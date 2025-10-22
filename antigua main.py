# -*- coding: utf-8 -*-
"""
SEIR + ACOR GUI (v4.4.2 - Corrección Final de Carga)
---------------------------------------------------
Versión con la corrección definitiva para el error TypeError en QSettings.
"""

import sys, os, json, time
from functools import partial
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy.integrate import odeint

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QPushButton, QLabel, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QGridLayout, QComboBox, QCheckBox, QAction,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QListWidget, QDialogButtonBox, QListWidgetItem, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, QSettings, QByteArray
import pyqtgraph as pg
import qdarktheme
# Importaciones de clases refactorizadas
from clases.helpers import ACORConfig
from clases.seir_model import SEIRModel
from clases.acor_optimizer import ACOROptimizer, ACORWorker
from clases.dialogs import (
    AdvancedACORConfigDialog, ResidualsDialog, ConvergenceDialog, RtDialog,
    ArchiveDistributionDialog, SensitivityAnalysisDialog, ParametersDialog
)
from clases.themes import DARK_THEME_QSS, LIGHT_THEME_QSS
from clases.report_generator import ReportGenerator

@dataclass
class RunResult:
    run_id: int
    best_cost: float
    best_params: np.ndarray
    cost_history: list = field(default_factory=list)
    duration: float = 0.0

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("AcorSeirOptimizer", "AppConfig")
        self.model = SEIRModel()
        self.optimizer = None
        self.worker = None
        self.dialog_windows = []
        self.best_params_overall = None
        self.best_cost_overall = float('inf')
        self.acor_config = ACORConfig()
        self.recent_files = self.settings.value("recent_files", [], type=list)
        self.run_history = []
        self.run_counter = 0
        
        self.dashboard_plots = {}
        self.next_plot_row = 1
        self.next_plot_col = 0

        self.init_ui()
        self.setAcceptDrops(True)
        self._load_settings()

    def init_ui(self):
        self.setWindowTitle("Interfaz de Optimización SEIR (v4.5)")
        self.setGeometry(100, 100, 1400, 850)
        self._create_menu_bar()

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Horizontal)

        # Panel izquierdo para gráficos
        self.plot_panel_content = QWidget()
        self.plot_grid_layout = QGridLayout(self.plot_panel_content)
        self.plot_grid_layout.setSpacing(10)

        self.plot_scroll_area = QScrollArea()
        self.plot_scroll_area.setWidgetResizable(True)
        self.plot_scroll_area.setWidget(self.plot_panel_content)
        self.plot_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.plot_widget = pg.PlotWidget(title="Modelo SEIR vs Datos")
        self.plot_widget.addLegend()
        self.plot_widget.setLabel('left', 'Infectados')
        self.plot_widget.setLabel('bottom', 'Semanas')
        self.scatter_item = self.plot_widget.plot(pen=None, symbol='o', symbolBrush='r', symbolPen='k', name="Datos Observados")
        self.curve_item = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name="Mejor Ajuste Global")
        self.comparison_curve_item = self.plot_widget.plot(pen=pg.mkPen('#888888', width=2, style=Qt.DashLine), name="Ajuste de Comparación")
        
        # El gráfico principal se gestiona por _rearrange_dashboard_plots

        self.tabs = QTabWidget()
        config_tab = QWidget()
        dashboard_tab = QWidget()
        self.tabs.addTab(config_tab, "Configuración")
        self.tabs.addTab(dashboard_tab, "Dashboard")
        self.tabs.setTabEnabled(1, False)

        self._setup_config_tab(config_tab)
        self._setup_dashboard_tab(dashboard_tab)

        splitter.addWidget(self.plot_scroll_area)
        splitter.addWidget(self.tabs)
        splitter.setSizes([950, 450])
        main_layout.addWidget(splitter)
        self.setCentralWidget(main_widget)
        self.log("Sistema listo. Importe datos para comenzar o arrastre un archivo a la ventana.", "blue")
        self.update_plot()
        self._rearrange_dashboard_plots() # Initial arrangement of plots

    def _setup_config_tab(self, tab):
        right_layout = QVBoxLayout(tab)
        # Los botones de importación/exportación fueron eliminados ya que están en el menú.

        group_cfg = QGroupBox("Configuración Principal")
        cfg_layout = QGridLayout(group_cfg)
        default_config = ACORConfig()
        self.pop_input = self._add_validated_input(cfg_layout, 0, "Población (N):", str(self.model.N), "Población total.", is_int=True)
        self.in_n_ants = self._add_validated_input(cfg_layout, 1, "Hormigas:", str(default_config.n_ants), "Soluciones por iteración.", is_int=True)
        self.in_archive = self._add_validated_input(cfg_layout, 2, "Archivo:", str(default_config.archive_size), "Tamaño de la élite.", is_int=True)
        self.in_max_iter = self._add_validated_input(cfg_layout, 3, "Iteraciones:", str(default_config.max_iter), "Número máximo de iteraciones.", is_int=True)
        self.in_q = self._add_validated_input(cfg_layout, 4, "q:", str(default_config.q), "Factor de exploración.", is_float=True)
        cfg_layout.addWidget(QLabel("Loss:"), 5, 0); self.cb_loss = QComboBox(); self.cb_loss.addItems(["MSE", "MAE", "Huber"]); cfg_layout.addWidget(self.cb_loss, 5, 1)
        self.in_plateau = self._add_validated_input(cfg_layout, 6, "Plateau K:", "200", "Iteraciones sin mejora para detener.", is_int=True, allow_empty=True)
        self.in_tmax = self._add_validated_input(cfg_layout, 7, "T máx (min):", "", "Tiempo máximo de ejecución.", is_float=True, allow_empty=True)
        self.chk_warm = QCheckBox("Warm-start"); self.chk_warm.setToolTip("Comenzar usando los últimos mejores parámetros."); cfg_layout.addWidget(self.chk_warm, 8, 0, 1, 2)
        btn_advanced = QPushButton("Configuración Avanzada"); btn_advanced.clicked.connect(self.open_advanced_config); cfg_layout.addWidget(btn_advanced, 9, 0, 1, 2)
        right_layout.addWidget(group_cfg)

        group_params = QGroupBox("Parámetros del Modelo"); p_layout = QVBoxLayout(group_params)
        btn_params = QPushButton("Ajustar Límites"); btn_params.clicked.connect(self.open_params_dialog); p_layout.addWidget(btn_params)
        right_layout.addWidget(group_params)

        group_run = QGroupBox("Ejecución y Log"); run_layout = QVBoxLayout(group_run)
        run_buttons_layout = QHBoxLayout()
        self.btn_run = QPushButton("Correr"); self.btn_run.clicked.connect(self.run_optimization); run_buttons_layout.addWidget(self.btn_run)
        self.btn_stop = QPushButton("Detener"); self.btn_stop.clicked.connect(self.stop_optimization); self.btn_stop.setEnabled(False); run_buttons_layout.addWidget(self.btn_stop)
        run_layout.addLayout(run_buttons_layout)
        log_layout = QHBoxLayout(); log_layout.addWidget(QLabel("Log:"))
        self.log_text = QTextEdit(readOnly=True)
        btn_clear_log = QPushButton("Limpiar"); btn_clear_log.clicked.connect(self.log_text.clear); log_layout.addWidget(btn_clear_log)
        run_layout.addLayout(log_layout); run_layout.addWidget(self.log_text)
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Mejor Costo: -")
        self.progress_label.setFixedWidth(200)
        progress_layout.addWidget(QLabel("Progreso:"))
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        run_layout.addLayout(progress_layout)
        right_layout.addWidget(group_run)
        right_layout.addStretch()

    def _setup_dashboard_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        history_group = QGroupBox("Historial de Ejecuciones")
        history_layout = QVBoxLayout(history_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["ID", "Costo Final", "Iteraciones", "Tiempo (s)"])
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.cellClicked.connect(self._display_comparison_run)
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_group, 2)

        dashboard_plots_group = QGroupBox("Análisis de la Ejecución Seleccionada")
        plots_layout = QGridLayout(dashboard_plots_group)
        plots_layout.setSpacing(10)
        
        btn_rt = QPushButton("R(t)"); btn_rt.clicked.connect(self.show_rt_plot)
        btn_residuals = QPushButton("Residuos"); btn_residuals.clicked.connect(self.show_residuals_plot)
        btn_convergence = QPushButton("Convergencia"); btn_convergence.clicked.connect(self.show_convergence_plot)
        btn_distribution = QPushButton("Distribución"); btn_distribution.clicked.connect(self.show_distribution_plot)
        btn_parallel = QPushButton("Análisis de Parámetros"); btn_parallel.clicked.connect(self.show_parallel_plot)
        btn_bounds = QPushButton("Análisis de Límites"); btn_bounds.clicked.connect(self.show_bounds_analysis_plot)

        plots_layout.addWidget(btn_rt, 0, 0)
        plots_layout.addWidget(btn_residuals, 0, 1)
        plots_layout.addWidget(btn_convergence, 1, 0)
        plots_layout.addWidget(btn_distribution, 1, 1)
        plots_layout.addWidget(btn_parallel, 2, 0)
        plots_layout.addWidget(btn_bounds, 2, 1)
        
        layout.addWidget(dashboard_plots_group, 1)
        layout.addStretch(1)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&Archivo")
        file_menu.addAction("Importar &XLSX...", lambda: self.import_xlsx())
        file_menu.addAction("Importar &JSON...", lambda: self.import_json())
        file_menu.addAction("&Exportar Sesión JSON...", self.export_json)
        self.export_pdf_action = QAction("Exportar Reporte PDF...", self, triggered=self._show_report_selection_dialog, enabled=False)
        file_menu.addAction(self.export_pdf_action)
        file_menu.addSeparator()
        self.recent_files_menu = file_menu.addMenu("Archivos Recientes")
        self.recent_files_menu.aboutToShow.connect(self._update_recent_files_menu)
        file_menu.addSeparator()
        file_menu.addAction("&Salir", self.close)

        view_menu = menu_bar.addMenu("&Ver")
        self.theme_action = QAction("Tema Oscuro", self, checkable=True, triggered=self._toggle_theme)
        view_menu.addAction(self.theme_action)
        view_menu.addAction("Limpiar Comparación", lambda: self.comparison_curve_item.clear())
        view_menu.addAction("Limpiar Gráficos del Dashboard", self._clear_dashboard_plots)

        help_menu = menu_bar.addMenu("A&yuda")
        help_menu.addAction("Acerca de...", self._show_about_dialog)

    def _load_settings(self):
        geometry = self.settings.value("geometry")
        if geometry and isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state and isinstance(state, QByteArray):
            self.restoreState(state)

        is_dark = self.settings.value("is_dark_theme", False, type=bool)
        self.theme_action.setChecked(is_dark)
        self._set_theme(is_dark)

    def _save_settings(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("is_dark_theme", self.theme_action.isChecked())
        self.settings.setValue("recent_files", self.recent_files)

    def _toggle_theme(self, checked):
        self._set_theme(checked)

    def _set_theme(self, is_dark):
            # 1. Determina el nombre del tema
            theme_name = "dark" if is_dark else "light"
            
            # 2. Carga la hoja de estilos correcta usando qdarktheme.load_stylesheet()
            stylesheet = qdarktheme.load_stylesheet(theme_name)
            
            # 3. Aplica la hoja de estilos a la instancia de la aplicación
            # Esto asegura que TODOS los widgets (diálogos, ventanas) reciban el tema
            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)
    
            # 4. Configura los colores de pyqtgraph manualmente (como lo hacías al principio)
            pg.setConfigOption('background', '#2b2b2b' if is_dark else 'w')
            pg.setConfigOption('foreground', '#f0f0f0' if is_dark else 'k')
    
            # 5. Actualiza el estado del menú
            self.theme_action.setChecked(is_dark)
            
            # 6. Actualiza tu gráfico principal
            self.update_plot()

    def _update_recent_files_menu(self):
        self.recent_files_menu.clear()
        if not self.recent_files:
            self.recent_files_menu.addAction(QAction("(No hay archivos recientes)", self, enabled=False))
        else:
            for file_path in self.recent_files:
                action = QAction(os.path.basename(file_path), self, triggered=partial(self._open_recent_file, file_path))
                self.recent_files_menu.addAction(action)

    def _add_recent_file(self, file_path):
        if file_path in self.recent_files: self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]

    def _open_recent_file(self, file_path):
        if not os.path.exists(file_path):
            self.log(f"El archivo reciente '{os.path.basename(file_path)}' no se encuentra.", "red"); self.recent_files.remove(file_path); return
        if file_path.lower().endswith(('.xlsx', '.xls')): self.import_xlsx(file_path)
        elif file_path.lower().endswith('.json'): self.import_json(file_path)

    def _show_about_dialog(self):
        QMessageBox.about(self, "Acerca de SEIR ACOR Optimizer",
                            "<p><b>SEIR ACOR Optimizer v4.4</b></p>"
                            "<p>arturo.josch@gmail.com</p>")

    def _show_report_selection_dialog(self):
        if not self.run_history: return
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleccionar Ejecución para Reporte")
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for r in self.run_history:
            item = QListWidgetItem(f"Ejecución #{r.run_id} (Costo: {r.best_cost:.4e})")
            item.setData(Qt.UserRole, r)
            list_widget.addItem(item)
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_() == QDialog.Accepted and list_widget.currentItem():
            selected_result = list_widget.currentItem().data(Qt.UserRole)
            self._display_comparison_run(self.run_history.index(selected_result), 0)
            
            # Ensure Rt plot is generated for the selected run before PDF generation
            rt_plot_widget = pg.PlotWidget(title=f"Rt(t) - Ejecución #{selected_result.run_id}")
            self._plot_rt_on_widget(rt_plot_widget, selected_result.best_params)
            self._add_dashboard_plot("rt", rt_plot_widget) # Add to dashboard_plots for ReportGenerator
            
            QApplication.processEvents()
            report_gen = ReportGenerator(self, self.model, selected_result, self.acor_config)
            report_gen.generate_pdf()

    def _add_validated_input(self, layout, row, label_text, value, tooltip, is_int=False, is_float=False, allow_empty=False):
        layout.addWidget(QLabel(label_text), row, 0)
        line_edit = QLineEdit(value)
        line_edit.setToolTip(tooltip)
        validation_func = partial(self._validate_line_edit, line_edit, is_int, is_float, allow_empty)
        line_edit.textChanged.connect(validation_func)
        validation_func()
        layout.addWidget(line_edit, row, 1)
        return line_edit

    def _validate_line_edit(self, line_edit, is_int, is_float, allow_empty):
        text = line_edit.text().strip()
        valid = False
        if allow_empty and not text: valid = True
        elif is_int: valid = text.isdigit() or (text.startswith('-') and text[1:].isdigit())
        elif is_float:
            try: float(text); valid = True
            except ValueError: valid = False
        line_edit.setStyleSheet("" if valid else "border: 1px solid red;")
        return valid

    def log(self, txt, color="black"):
        timestamp = time.strftime("%H:%M:%S")
        if self.theme_action.isChecked() and color == "black": color = "#f0f0f0"
        self.log_text.append(f'<font color="{color}">[{timestamp}] {txt}</font>')
        self.log_text.ensureCursorVisible()

    def update_plot(self, comparison_params=None):
        # 1. Dibuja siempre los puntos de datos observados si existen.
        if self.model.I_data is not None and len(self.model.I_data) > 0:
            self.scatter_item.setData(self.model.t_data, self.model.I_data)
        else:
            self.scatter_item.setData([], [])

        # 2. Dibuja la curva del mejor ajuste global si existe.
        if self.best_params_overall is not None and len(self.model.I_data) > 0:
            t_sim = np.linspace(float(self.model.t_data[0]), float(self.model.t_data[-1]), 300)
            try:
                k = self.best_params_overall[21]; self.model.set_initial_conditions(k)
                sol = odeint(self.model.seir_harmonic, self.model.y0, t_sim, args=tuple(self.best_params_overall[:21]), mxstep=200_000)
                self.curve_item.setData(t_sim, sol[:, 2])
            except Exception as e: self.log(f"Error al graficar mejor ajuste: {e}", "red")
        else:
            self.curve_item.setData([], [])

        # 3. Dibuja la curva de comparación (para actualizaciones en vivo) si se proporcionan los parámetros.
        if comparison_params is not None and len(self.model.I_data) > 0:
            t_sim = np.linspace(float(self.model.t_data[0]), float(self.model.t_data[-1]), 300)
            try:
                k = comparison_params[21]; self.model.set_initial_conditions(k)
                sol = odeint(self.model.seir_harmonic, self.model.y0, t_sim, args=tuple(comparison_params[:21]), mxstep=200_000)
                self.comparison_curve_item.setData(t_sim, sol[:, 2])
            except Exception as e: self.log(f"Error al graficar comparación: {e}", "red")
        else:
            self.comparison_curve_item.setData([], [])

    def run_optimization(self):
        if len(self.model.I_data) == 0: QMessageBox.warning(self, "Datos faltantes", "Importe datos."); return
        try:
            self.model.N = int(self.pop_input.text())
            self.model.loss_type = self.cb_loss.currentText()
            self.acor_config.n_ants = int(self.in_n_ants.text())
            self.acor_config.archive_size = int(self.in_archive.text())
            self.acor_config.max_iter = int(self.in_max_iter.text())
            self.acor_config.q = float(self.in_q.text())
            plateau_K = int(self.in_plateau.text()) if self.in_plateau.text().strip() else None
            tmax_m = self.in_tmax.text().strip()
            tmax_seconds = float(tmax_m) * 60.0 if tmax_m else None
            warm_start_params = self.best_params_overall if self.chk_warm.isChecked() else None

            self.start_time = time.time()
            self.optimizer = ACOROptimizer(self.model.fitness, self.model.bounds, self.acor_config, warm_start_params)
            self.worker = ACORWorker(self.optimizer, tmax_seconds, plateau_K)
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.optimization_finished)
            config_summary = f"<b>Iniciando Optimización #{self.run_counter + 1} con la siguiente configuración:</b>\n"
            config_summary += f"  - <b>Parámetros Base:</b> {self.acor_config.n_ants} hormigas, {self.acor_config.archive_size} en archivo, {self.acor_config.max_iter} iteraciones.\n"
            config_summary += f"  - <b>Modelo de Islas:</b> {self.acor_config.colonies_count} colonias, migración de {self.acor_config.migration_size} individuos cada {self.acor_config.migration_interval} iteraciones.\n"
            config_summary += "  - <b>Estrategias de Intensificación:</b>\n"
            config_summary += f"    - OBL: {'Activado' if self.acor_config.obl_enabled else 'Desactivado'}\n"
            config_summary += f"    - Búsqueda Local: {'Activado (cada ' + str(self.acor_config.local_search_frequency) + ' iters)' if self.acor_config.local_search_enabled else 'Desactivado'}\n"
            config_summary += f"    - Pulido Codicioso: {'Activado (cada ' + str(self.acor_config.refinement_frequency) + ' iters)' if self.acor_config.refinement_enabled else 'Desactivado'}\n"
            config_summary += f"  - <b>Condiciones de Parada:</b> Límite de tiempo: {tmax_m or 'N/A'} min, Plateau global: {plateau_K or 'N/A'} iters.\n"
            config_summary += f"  - <b>Función de Loss:</b> {self.model.loss_type}"
            self.log(config_summary, "blue")

            self.btn_run.setEnabled(False); self.btn_stop.setEnabled(True)
            self.tabs.setCurrentIndex(0)
            self.progress_label.setText("Mejor Costo: -")
            self.worker.start()
        except (ValueError, TypeError) as e:
            self.log(f"Error de Entrada: {e}", "red"); QMessageBox.critical(self, "Error de Entrada", f"Parámetros inválidos: {e}")

    def stop_optimization(self):
        if self.worker: self.worker.stop(); self.log("Solicitud de detención enviada...", "orange")

    def update_progress(self, progress, message, params):
        self.progress_bar.setValue(progress)
        
        cost_str = "-"
        if "Best Cost:" in message:
            try:
                cost_str = message.split("Best Cost:")[1].split("(")[0].strip()
            except IndexError:
                pass
        self.progress_label.setText(f"Mejor Costo: {cost_str}")

        important_keywords = ["encontró mejora", "Detenido", "Límite de tiempo", "Plateau", "Error"]
        if any(keyword in message for keyword in important_keywords):
            color = "green" if "mejora" in message else "orange" if "Detenido" in message or "Plateau" in message else "red"
            self.log(message, color)

        if params is not None:
            self.update_plot(comparison_params=params)

    def optimization_finished(self, optimizer):
        self.run_counter += 1
        duration = time.time() - self.start_time
        result = RunResult(run_id=self.run_counter, best_cost=optimizer.best_cost_global, best_params=optimizer.best_params_global, cost_history=optimizer.history_best_cost,
        duration=duration)
        self.run_history.append(result)

        self.log(f"<b>Optimización #{self.run_counter} finalizada. Costo final: {result.best_cost:.4e}</b>", "blue")
        
        params_header = "<b>Mejores Parámetros Encontrados:</b>"
        params_list = "\n".join([f"  - {label}: {val:.6f}" for label, val in zip(self.model.labels, result.best_params)])
        self.log(f"{params_header}\n<pre>{params_list}</pre>")

        self.btn_run.setEnabled(True); self.btn_stop.setEnabled(False)
        self.export_pdf_action.setEnabled(True)

        if result.best_cost < self.best_cost_overall:
            self.best_cost_overall = result.best_cost
            self.best_params_overall = result.best_params
            self.log("<b>¡Nuevo mejor resultado global encontrado!</b>", "green")

        self.worker = None; self.optimizer = optimizer
        self._update_dashboard()
        self.update_plot()
        for dlg in self.dialog_windows:
            if hasattr(dlg, 'update_contents'): dlg.update_contents()

    def _update_dashboard(self):
        self.tabs.setTabEnabled(1, True)
        self.history_table.setRowCount(0)
        for result in reversed(self.run_history):
            row_pos = self.history_table.rowCount()
            self.history_table.insertRow(row_pos)
            self.history_table.setItem(row_pos, 0, QTableWidgetItem(str(result.run_id)))
            self.history_table.setItem(row_pos, 1, QTableWidgetItem(f"{result.best_cost:.4e}"))
            self.history_table.setItem(row_pos, 2, QTableWidgetItem(str(len(result.cost_history))))
            self.history_table.setItem(row_pos, 3, QTableWidgetItem(f"{result.duration:.2f}"))
        
        if self.history_table.rowCount() > 0:
            self.history_table.selectRow(0)
            self._display_comparison_run(0, 0)

    def _display_comparison_run(self, row, column):
        result = self._get_selected_run_result()
        if result:
            self.log(f"Seleccionada Ejecución #{result.run_id} para comparación y análisis.", "purple")
            self.update_plot(comparison_params=result.best_params)
            self._clear_dashboard_plots()

    def _plot_rt_on_widget(self, plot_widget, params):
        if params is None or len(self.model.I_data) == 0: return
        plot_widget.clear()
        plot_widget.addItem(pg.InfiniteLine(angle=0, pos=1.0, pen=pg.mkPen('b', style=Qt.DashLine)))
        t_sim = np.linspace(self.model.t_data[0], self.model.t_data[-1], 300)
        p = params[:21]
        beta = np.exp(p[0] + p[1]*np.cos(p[2]*t_sim + p[3]) + p[4]*np.cos(p[5]*t_sim + p[6]))
        gamma = np.exp(p[7] + p[8]*np.cos(p[9]*t_sim + p[10]) + p[11]*np.cos(p[12]*t_sim + p[13]))
        k = params[21]; self.model.set_initial_conditions(k)
        sol = odeint(self.model.seir_harmonic, self.model.y0, t_sim, args=tuple(p), mxstep=200_000)
        S = sol[:, 0]
        Rt = beta * S / (gamma * self.model.N)
        plot_widget.plot(t_sim, Rt, pen=pg.mkPen('m', width=2))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.xlsx', '.xls', '.json')):
                    event.acceptProposedAction()

    def dropEvent(self, event):
        file_path = event.mimeData().urls()[0].toLocalFile()
        if os.path.exists(file_path): self._add_recent_file(file_path)
        self.log(f"Archivo arrastrado: {os.path.basename(file_path)}", "blue")
        if file_path.lower().endswith(('.xlsx', '.xls')): self.import_xlsx(file_path)
        elif file_path.lower().endswith('.json'): self.import_json(file_path)

    def import_xlsx(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Importar Excel", "", "Excel Files (*.xlsx *.xls)")
        if not file_path: return
        self._reset_session_state()
        try:
            df = pd.read_excel(file_path, dtype=float).dropna(how="all")
            self.model.t_data = df.iloc[:, 0].to_numpy(float)
            self.model.I_data = df.iloc[:, 1].to_numpy(float)
            self.log(f"Datos importados de {os.path.basename(file_path)} ({len(self.model.I_data)} registros)", "green")
            self.update_plot(); self._add_recent_file(file_path)
        except Exception as e:
            self.log(f"Error importando XLSX: {e}", "red"); QMessageBox.critical(self, "Error", f"{e}")

    def import_json(self, file_path=None):
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(self, "Importar JSON", "", "JSON Files (*.json)")
        if not file_path: return
        self._reset_session_state()
        try:
            with open(file_path, "r") as f: data = json.load(f)
            self.model.t_data = np.array(data["t"], dtype=float)
            self.model.I_data = np.array(data["I"], dtype=float)
            self.model.N = int(data["N"])
            if "bounds" in data and len(data["bounds"]) == self.model.DIM: self.model.bounds = np.array(data["bounds"], dtype=float)
            if "best_params" in data and len(data["best_params"]) == self.model.DIM:
                self.best_params_overall = np.array(data["best_params"], dtype=float)
                self.best_cost_overall = float(data.get("best_cost", float('inf')))
            self.pop_input.setText(str(self.model.N))
            self.log(f"Sesión importada desde {os.path.basename(file_path)}", "green")
            self.update_plot(); self._add_recent_file(file_path)
        except Exception as e:
            self.log(f"Error importando JSON: {e}", "red"); QMessageBox.critical(self, "Error", f"{e}")

    def export_json(self):
        file, _ = QFileDialog.getSaveFileName(self, "Exportar JSON", "", "JSON Files (*.json)")
        if not file: return
        if not file.endswith(".json"): file += ".json"
        try:
            data = {
                "t": self.model.t_data.tolist(), "I": self.model.I_data.tolist(),
                "N": int(self.pop_input.text()), "bounds": self.model.bounds.tolist(),
                "model": "SEIR-harmonic-v4-multi-colony"
            }
            if self.best_params_overall is not None:
                data["best_params"] = self.best_params_overall.tolist()
                data["best_cost"] = float(self.best_cost_overall)
            with open(file, "w") as f: json.dump(data, f, indent=4)
            self.log(f"Sesión exportada a {os.path.basename(file)}", "green")
        except Exception as e:
            self.log(f"Error exportando JSON: {e}", "red"); QMessageBox.critical(self, "Error", f"{e}")

    def open_advanced_config(self):
        dlg = AdvancedACORConfigDialog(self)
        if dlg.exec_(): self.acor_config = dlg.get_config(self.acor_config); self.log("Configuración avanzada actualizada.", "blue")

    def open_params_dialog(self):
        dlg = ParametersDialog(self.model, self)
        if dlg.exec_(): self.log("Límites de parámetros actualizados.", "blue")

    def _reset_session_state(self):
        """Limpia el estado de la sesión actual, incluyendo historial y gráficos."""
        self.log("Limpiando estado de la sesión anterior...", "orange")
        self.run_history.clear()
        self.history_table.setRowCount(0)
        self.tabs.setTabEnabled(1, False)
        self._clear_dashboard_plots()
        self.best_params_overall = None
        self.best_cost_overall = float('inf')
        self.comparison_curve_item.clear()
        self.update_plot()

    def _clear_dashboard_plots(self):
        for plot_widget in self.dashboard_plots.values():
            self.plot_grid_layout.removeWidget(plot_widget)
            plot_widget.deleteLater()
        self.dashboard_plots.clear()
        self.next_plot_row = 1 # These are no longer directly used for layout, but keep for consistency if needed elsewhere
        self.next_plot_col = 0 # These are no longer directly used for layout, but keep for consistency if needed elsewhere
        self.log("Gráficos del dashboard limpiados.", "blue")
        self._rearrange_dashboard_plots() # Re-arrange to ensure main plot spans 2 columns

    def _get_selected_run_result(self):
        if self.history_table.rowCount() == 0 or self.history_table.currentRow() < 0:
            QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione una ejecución de la tabla de historial.")
            return None
        selected_row = self.history_table.currentRow()
        run_id_to_find = int(self.history_table.item(selected_row, 0).text())
        return next((r for r in self.run_history if r.run_id == run_id_to_find), None)

    def _add_dashboard_plot(self, name, plot_widget):
        plot_widget.setMinimumSize(450, 350) # Set a consistent minimum size
        plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow it to expand but respect min size

        # Store the plot widget, replacing if it already exists
        self.dashboard_plots[name] = plot_widget
        self._rearrange_dashboard_plots()

    def _rearrange_dashboard_plots(self):
        # Clear all widgets from the layout first
        for i in reversed(range(self.plot_grid_layout.count())):
            widget = self.plot_grid_layout.itemAt(i).widget()
            if widget is not None: # Ensure it's a widget, not just a spacer
                self.plot_grid_layout.removeWidget(widget)
                widget.setParent(None) # Remove from layout and delete

        num_dashboard_plots = len(self.dashboard_plots)

        # Position the main SEIR plot
        if num_dashboard_plots == 0:
            self.plot_grid_layout.addWidget(self.plot_widget, 0, 0, 1, 2) # Span 2 columns
        else:
            self.plot_grid_layout.addWidget(self.plot_widget, 0, 0, 1, 1) # Occupy 1 column

        # Position dashboard plots
        current_row = 0
        current_col = 1

        # If there are dashboard plots, the main plot takes one column, so dashboard plots start at (0,1)
        # If there are 2 or more dashboard plots, they start from row 1, column 0
        if num_dashboard_plots > 0:
            dashboard_plot_index = 0
            for name, plot_widget in self.dashboard_plots.items():
                if dashboard_plot_index == 0 and num_dashboard_plots == 1:
                    # Only one dashboard plot, it goes to (0,1)
                    self.plot_grid_layout.addWidget(plot_widget, 0, 1, 1, 1)
                elif dashboard_plot_index == 0 and num_dashboard_plots > 1:
                    # First dashboard plot when there are multiple, it goes to (0,1)
                    self.plot_grid_layout.addWidget(plot_widget, 0, 1, 1, 1)
                else:
                    # Subsequent dashboard plots start from row 1
                    if (dashboard_plot_index - 1) % 2 == 0: # Even index (0, 2, 4...) after the first one
                        current_row = 1 + (dashboard_plot_index - 1) // 2
                        current_col = 0
                    else: # Odd index (1, 3, 5...) after the first one
                        current_row = 1 + (dashboard_plot_index - 1) // 2
                        current_col = 1
                    self.plot_grid_layout.addWidget(plot_widget, current_row, current_col, 1, 1)
                dashboard_plot_index += 1



    def show_rt_plot(self):
        result = self._get_selected_run_result()
        if not result: return
        
        plot_widget = pg.PlotWidget(title=f"Rt(t) - Ejecución #{result.run_id}")
        self._plot_rt_on_widget(plot_widget, result.best_params)
        self._add_dashboard_plot("rt", plot_widget)

    def show_residuals_plot(self):
        result = self._get_selected_run_result()
        if not result: return

        plot_widget = pg.PlotWidget(title=f"Residuos - Ejecución #{result.run_id}")
        plot_widget.setLabel('left', 'Residuo (I_obs - I_pred)')
        plot_widget.setLabel('bottom', 'Tiempo')
        
        params = result.best_params
        if params is not None and len(self.model.I_data) > 0:
            t = self.model.t_data
            try:
                k = params[21]; self.model.set_initial_conditions(k)
                I_pred = odeint(self.model.seir_harmonic, self.model.y0, t, args=tuple(params[:21]), mxstep=200_000)[:, 2]
                resid = self.model.I_data - I_pred
                plot_widget.plot(t, resid, pen=None, symbol='o', symbolBrush='b', symbolPen='k')
                plot_widget.addLine(y=0, pen=pg.mkPen('k', style=Qt.DashLine))
            except Exception as e:
                self.log(f"Error al calcular residuos: {e}", "red")

        self._add_dashboard_plot("residuals", plot_widget)

    def show_convergence_plot(self):
        result = self._get_selected_run_result()
        if not result: return

        plot_widget = pg.PlotWidget(title=f"Convergencia de Costo - Ejecución #{result.run_id}")
        plot_widget.setLabel('left', f'Costo ({self.model.loss_type})')
        plot_widget.setLabel('bottom', 'Iteración')
        plot_widget.plot(result.cost_history, pen='b')
        self._add_dashboard_plot("convergence", plot_widget)

    def show_distribution_plot(self):
        result = self._get_selected_run_result()
        if not result: return
        
        if not self.optimizer or not self.optimizer.archives:
            QMessageBox.warning(self, "Sin Datos", "No hay datos de colonias. La distribución de parámetros se genera al final de una nueva ejecución de optimización.")
            return
        
        plot_widget = pg.PlotWidget(title="Distribución de Parámetros por Colonia (Última Iter.)")
        plot_widget.setLabel('left', 'Valor Normalizado')
        plot_widget.setLabel('bottom', 'Parámetro')

        low, high = self.model.LOW, self.model.HIGH
        x_ticks = [list(enumerate(self.model.labels))]
        plot_widget.getAxis('bottom').setTicks(x_ticks)

        for i, archive in enumerate(self.optimizer.archives):
            normalized_archive = (archive - low) / (high - low)
            means = np.mean(normalized_archive, axis=0)
            color = pg.intColor(i, self.optimizer.config.colonies_count, alpha=150)
            bar_item = pg.BarGraphItem(x=np.arange(self.model.DIM) + i * 0.2, height=means, width=0.2, brush=color)
            plot_widget.addItem(bar_item)
        
        plot_widget.setYRange(0, 1)
        self._add_dashboard_plot("distribution", plot_widget)

    def show_parallel_plot(self):
        if not self.optimizer or not self.optimizer.archives:
            QMessageBox.warning(self, "Sin Datos", "No hay datos de archivo para mostrar. Ejecute una optimización primero.")
            return

        plot_widget = pg.PlotWidget(title="Análisis de Coordenadas Paralelas (Archivo de la Mejor Colonia)")
        plot_widget.setLabel('left', 'Valor Normalizado (0=min, 1=max)')
        
        ticks = [list(enumerate(self.model.labels))]
        ax = plot_widget.getAxis('bottom')
        ax.setTicks(ticks)
        ax.setPen(pg.mkPen(None))
        ax.setTextPen(pg.mkPen('k' if not self.theme_action.isChecked() else '#f0f0f0'))

        plot_widget.setYRange(0, 1)

        archive = self.optimizer.archives[0]
        low = self.model.LOW
        high = self.model.HIGH
        
        rng = high - low
        rng[rng == 0] = 1
        normalized_archive = (archive - low) / rng

        for i in range(1, normalized_archive.shape[0]):
            plot_widget.plot(y=normalized_archive[i], pen=pg.mkPen((0, 100, 255, 30), width=1))

        plot_widget.plot(y=normalized_archive[0], pen=pg.mkPen('r', width=1.5, style=Qt.DashLine), name="Mejor Solución")

        self._add_dashboard_plot("parallel", plot_widget)

    def show_bounds_analysis_plot(self):
        result = self._get_selected_run_result()
        if not result:
            return

        plot_widget = pg.PlotWidget(title=f"Análisis de Límites - Ejecución #{result.run_id}")
        plot_widget.setLabel('left', 'Distancia Normalizada al Límite Más Cercano')
        plot_widget.setLabel('bottom', 'Parámetro')
        
        params = result.best_params
        bounds = self.model.bounds
        
        lows = bounds[:, 0]
        highs = bounds[:, 1]
        ranges = highs - lows
        ranges[ranges == 0] = 1 # Evitar división por cero

        normalized_params = (params - lows) / ranges
        
        distances = np.minimum(normalized_params, 1 - normalized_params)
        
        colors = []
        for d in distances:
            if d < 0.05:
                colors.append((220, 20, 60, 200)) # Rojo
            elif d < 0.15:
                colors.append((255, 165, 0, 200)) # Amarillo
            else:
                colors.append((34, 139, 34, 200)) # Verde

        bar_item = pg.BarGraphItem(x=range(len(params)), height=distances, width=0.6, brushes=colors)
        plot_widget.addItem(bar_item)

        ticks = [list(enumerate(self.model.labels))]
        ax = plot_widget.getAxis('bottom')
        ax.setTicks(ticks)
        
        plot_widget.setYRange(0, 0.5) # La distancia máxima posible es 0.5 (justo al centro)

        # Añadir líneas para los umbrales de color
        plot_widget.addLine(y=0.05, pen=pg.mkPen('r', style=Qt.DashLine))
        plot_widget.addLine(y=0.15, pen=pg.mkPen('y', style=Qt.DashLine))

        self._add_dashboard_plot("bounds", plot_widget)


    def closeEvent(self, event):
        self._save_settings()
        for win in self.dialog_windows[:]: win.close()
        super().closeEvent(event)

if __name__ == '__main__':
    if sys.platform.startswith('win'):
        from multiprocessing import freeze_support
        freeze_support()
        if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        import ctypes
        myappid = 'acor.seir.optimizer.v4.4'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())