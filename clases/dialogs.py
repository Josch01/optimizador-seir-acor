# -*- coding: utf-8 -*-
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QLabel, QTableWidget, QTableWidgetItem,
    QGridLayout, QComboBox, QCheckBox, QTabWidget, QSpinBox, QDoubleSpinBox,
    QDialogButtonBox, QWidget, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from scipy.integrate import odeint
from multiprocessing import Pool
import psutil

from .helpers import ACORConfig, parse_numeric
from .seir_model import SEIRModel
from .acor_optimizer import ACOROptimizer

class AdvancedACORConfigDialog(QDialog):
    """Di\u00e1logo para configurar par\u00e1metros avanzados de ACOR."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuraci\u00f3n Avanzada ACOR")
        self.setGeometry(400, 400, 700, 600)
        layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        # Pesta\u00f1a Multi-Colonia
        colony_tab = QWidget()
        colony_layout = QVBoxLayout(colony_tab)
        colony_group = QGroupBox("Modelo de Islas (Multi-Colonia)")
        col_layout = QGridLayout(colony_group)
        col_layout.addWidget(QLabel("N\u00famero de colonias (islas):"), 0, 0)
        self.spin_colonies_count = QSpinBox()
        self.spin_colonies_count.setRange(1, 16)
        self.spin_colonies_count.setValue(4)
        col_layout.addWidget(self.spin_colonies_count, 0, 1)
        col_layout.addWidget(QLabel("Intervalo de migraci\u00f3n (iters):"), 1, 0)
        self.spin_mig_interval = QSpinBox()
        self.spin_mig_interval.setRange(5, 100)
        self.spin_mig_interval.setValue(25)
        col_layout.addWidget(self.spin_mig_interval, 1, 1)
        col_layout.addWidget(QLabel("Tama\u00f1o de migraci\u00f3n (individuos):"), 2, 0)
        self.spin_mig_size = QSpinBox()
        self.spin_mig_size.setRange(1, 10)
        self.spin_mig_size.setValue(2)
        col_layout.addWidget(self.spin_mig_size, 2, 1)
        colony_layout.addWidget(colony_group)
        colony_layout.addStretch()
        tab_widget.addTab(colony_tab, "Modelo de Colonias")

        # Pesta\u00f1a de Intensificaci\u00f3n
        intensification_tab = QWidget()
        intensification_layout = QVBoxLayout(intensification_tab)
        self.chk_obl = QCheckBox("Activar Aprendizaje Basado en Oposici\u00f3n (OBL)")
        self.chk_obl.setChecked(True)
        intensification_layout.addWidget(self.chk_obl)
        refine_group = QGroupBox("Pulido Codicioso de Mejor Soluci\u00f3n")
        refine_layout = QGridLayout(refine_group)
        self.chk_refine = QCheckBox("Activar Pulido")
        self.chk_refine.setChecked(True)
        refine_layout.addWidget(self.chk_refine, 0, 0, 1, 2)
        refine_layout.addWidget(QLabel("Frecuencia (iters):"), 1, 0)
        self.spin_refine_freq = QSpinBox()
        self.spin_refine_freq.setRange(10, 200)
        self.spin_refine_freq.setValue(50)
        refine_layout.addWidget(self.spin_refine_freq, 1, 1)
        refine_layout.addWidget(QLabel("Paso de pulido (%):"), 2, 0)
        self.spin_refine_step = QDoubleSpinBox()
        self.spin_refine_step.setRange(0.01, 0.2)
        self.spin_refine_step.setSingleStep(0.01)
        self.spin_refine_step.setValue(0.05)
        refine_layout.addWidget(self.spin_refine_step, 2, 1)
        intensification_layout.addWidget(refine_group)
        local_search_group = QGroupBox("B\u00fasqueda Local (por hormiga)")
        ls_layout = QGridLayout(local_search_group)
        self.chk_local_search = QCheckBox("Activar b\u00fasqueda local")
        self.chk_local_search.setChecked(True)
        ls_layout.addWidget(self.chk_local_search, 0, 0, 1, 2)
        ls_layout.addWidget(QLabel("Radio de b\u00fasqueda (%):"), 1, 0)
        self.spin_local_search_radius = QDoubleSpinBox()
        self.spin_local_search_radius.setRange(0.01, 0.5)
        self.spin_local_search_radius.setSingleStep(0.01)
        self.spin_local_search_radius.setValue(0.1)
        ls_layout.addWidget(self.spin_local_search_radius, 1, 1)
        ls_layout.addWidget(QLabel("Puntos de b\u00fasqueda:"), 2, 0)
        self.spin_local_search_points = QSpinBox()
        self.spin_local_search_points.setRange(5, 50)
        self.spin_local_search_points.setValue(10)
        ls_layout.addWidget(self.spin_local_search_points, 2, 1)
        ls_layout.addWidget(QLabel("Frecuencia (iters):"), 3, 0)
        self.spin_local_search_freq = QSpinBox()
        self.spin_local_search_freq.setRange(1, 20)
        self.spin_local_search_freq.setValue(5)
        ls_layout.addWidget(self.spin_local_search_freq, 3, 1)
        intensification_layout.addWidget(local_search_group)
        intensification_layout.addStretch()
        tab_widget.addTab(intensification_tab, "Estrategias de Intensificaci\u00f3n")

        layout.addWidget(tab_widget)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def get_config(self, base_config: ACORConfig) -> ACORConfig:
        base_config.colonies_count = self.spin_colonies_count.value()
        base_config.migration_interval = self.spin_mig_interval.value()
        base_config.migration_size = self.spin_mig_size.value()
        base_config.local_search_enabled = self.chk_local_search.isChecked()
        base_config.local_search_radius = self.spin_local_search_radius.value()
        base_config.local_search_points = self.spin_local_search_points.value()
        base_config.local_search_frequency = self.spin_local_search_freq.value()
        base_config.obl_enabled = self.chk_obl.isChecked()
        base_config.refinement_enabled = self.chk_refine.isChecked()
        base_config.refinement_frequency = self.spin_refine_freq.value()
        base_config.refinement_step = self.spin_refine_step.value()
        return base_config

class ResidualsDialog(QDialog):
    """Di\u00e1logo para visualizar los residuos del modelo y la distancia a los l\u00edmites."""
    def __init__(self, model: SEIRModel, optimizer: ACOROptimizer, parent=None):
        super().__init__(parent)
        self.model = model
        self.optimizer = optimizer
        self.setWindowTitle("Residuos y Extremos")
        self.setGeometry(350, 200, 1000, 820)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        box_res = QGroupBox("Residuos (I_obs - I_pred)")
        res_layout = QVBoxLayout()
        self.plot_res = pg.PlotWidget()
        self.plot_res.setLabel('left', 'Residuo')
        self.plot_res.setLabel('bottom', 'Tiempo')
        res_layout.addWidget(self.plot_res)
        box_res.setLayout(res_layout)
        box_dist = QGroupBox("Distancia al L\u00edmite Superior (0=pegado, 1=lejos)")
        dist_layout = QVBoxLayout()
        self.plot_dist = pg.PlotWidget()
        self.plot_dist.setLabel('left', 'Distancia a high (fracci\u00f3n)')
        self.plot_dist.setLabel('bottom', 'Par\u00e1metro')
        dist_layout.addWidget(self.plot_dist)
        box_dist.setLayout(dist_layout)
        layout.addWidget(box_res, stretch=1)
        layout.addWidget(box_dist, stretch=1)
        self.update_contents()

    def _bar_color_to_high(self, p, low, high):
        rng = max(high - low, 1e-12)
        dist_to_high = (high - p) / rng
        if dist_to_high <= 0.02: return pg.mkBrush(220, 20, 60, 220)
        elif dist_to_high <= 0.10: return pg.mkBrush(255, 165, 0, 220)
        else: return pg.mkBrush(70, 130, 180, 220)

    def update_contents(self, params: np.ndarray = None):
        if params is None: params = self.optimizer.best_params_global
        self.plot_res.clear()
        self.plot_dist.clear()
        if params is None or len(self.model.I_data) == 0: return
        t = self.model.t_data
        try:
            I_pred = odeint(self.model.seir_harmonic, self.model.y0, t, args=tuple(params[:21]), mxstep=200_000)[:, 2]
        except Exception: I_pred = np.full_like(self.model.I_data, np.nan)
        resid = self.model.I_data - I_pred
        self.plot_res.plot(t, resid, pen=None, symbol='o', symbolBrush='b', symbolPen='k')
        self.plot_res.addLine(y=0, pen=pg.mkPen('k', style=Qt.DashLine))
        low, high = self.model.LOW, self.model.HIGH
        rng = np.where((high - low) == 0, 1.0, (high - low))
        dist_high = (high - params) / rng
        bar_item = pg.BarGraphItem(x=range(len(params)), height=dist_high, width=0.8, brushes=[self._bar_color_to_high(p, l, h) for p, l, h in zip(params, low, high)])
        self.plot_dist.addItem(bar_item)
        self.plot_dist.addLine(y=0.10, pen=pg.mkPen('r', style=Qt.DashLine))
        self.plot_dist.addLine(y=0.02, pen=pg.mkPen('r', style=Qt.SolidLine))
        self.plot_dist.getAxis('bottom').setTicks([list(enumerate(self.model.labels))])
        self.plot_dist.setYRange(0, 1, padding=0.05)

class ConvergenceDialog(QDialog):
    """Di\u00e1logo para visualizar la convergencia del costo y los par\u00e1metros."""
    def __init__(self, model: SEIRModel, optimizer: ACOROptimizer, parent=None):
        super().__init__(parent)
        self.optimizer = optimizer
        self.model = model
        self.setWindowTitle("Convergencia")
        self.setGeometry(360, 220, 1000, 820)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        box_cost = QGroupBox("Mejor Costo por Iteraci\u00f3n")
        v1 = QVBoxLayout()
        self.plot_cost = pg.PlotWidget()
        self.plot_cost.setLabel('left', f'Costo ({self.model.loss_type})')
        self.plot_cost.setLabel('bottom', 'Iteraci\u00f3n')
        v1.addWidget(self.plot_cost)
        box_cost.setLayout(v1)
        box_par = QGroupBox("Evoluci\u00f3n de Par\u00e1metros")
        v2 = QVBoxLayout()
        self.plot_par = pg.PlotWidget()
        self.plot_par.setLabel('left', 'Valor')
        self.plot_par.setLabel('bottom', 'Iteraci\u00f3n')
        v2.addWidget(self.plot_par)
        box_par.setLayout(v2)
        layout.addWidget(box_cost, stretch=1)
        layout.addWidget(box_par, stretch=2)
        self.update_contents()

    def update_contents(self):
        self.plot_cost.clear()
        self.plot_par.clear()
        hc = self.optimizer.history_best_cost
        hp = self.optimizer.history_best_params
        if not hc or not hp: return
        it = np.arange(len(hc))
        hp_arr = np.vstack(hp)
        self.plot_cost.plot(it, hc, pen='b')
        for j in range(hp_arr.shape[1]):
            self.plot_par.plot(it, hp_arr[:, j], pen=pg.intColor(j, hp_arr.shape[1]))

class RtDialog(QDialog):
    """Di\u00e1logo para visualizar las tasas variables y el n\u00famero reproductivo efectivo Rt."""
    def __init__(self, model: SEIRModel, optimizer: ACOROptimizer, parent=None):
        super().__init__(parent)
        self.model = model
        self.optimizer = optimizer
        self.setWindowTitle("b2(t), b3(t), c3(t) y Rt(t)")
        self.setGeometry(370, 240, 1000, 900)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        self.plot_beta = pg.PlotWidget(title="b2(t)")
        layout.addWidget(self.plot_beta)
        self.plot_gamma = pg.PlotWidget(title="b3(t)")
        layout.addWidget(self.plot_gamma)
        self.plot_sigma = pg.PlotWidget(title="c3(t)")
        layout.addWidget(self.plot_sigma)
        self.plot_Rt = pg.PlotWidget(title="Rt(t) = b2(t)·S(t) / (b3(t)·N)")
        layout.addWidget(self.plot_Rt)
        self.plot_Rt.addItem(pg.InfiniteLine(angle=0, pos=1.0, pen=pg.mkPen('b', style=Qt.DashLine)))
        self.update_contents()

    def update_contents(self, params=None):
        if params is None: params = self.optimizer.best_params_global
        for plot in [self.plot_beta, self.plot_gamma, self.plot_sigma, self.plot_Rt]: plot.clear()
        self.plot_Rt.addItem(pg.InfiniteLine(angle=0, pos=1.0, pen=pg.mkPen('b', style=Qt.DashLine)))
        if params is None or len(self.model.t_data) == 0: return
        t_sim = np.linspace(self.model.t_data[0], self.model.t_data[-1], 300)
        p = params[:21]
        beta = np.exp(p[0] + p[1]*np.cos(p[2]*t_sim + p[3]) + p[4]*np.cos(p[5]*t_sim + p[6]))
        gamma = np.exp(p[7] + p[8]*np.cos(p[9]*t_sim + p[10]) + p[11]*np.cos(p[12]*t_sim + p[13]))
        sigma = np.exp(p[14] + p[15]*np.cos(p[16]*t_sim + p[17]) + p[18]*np.cos(p[19]*t_sim + p[20]))
        k = params[21]
        self.model.set_initial_conditions(k)
        sol = odeint(self.model.seir_harmonic, self.model.y0, t_sim, args=tuple(p), mxstep=200_000)
        S = sol[:, 0]
        Rt = beta * S / (gamma * self.model.N)
        self.plot_beta.plot(t_sim, beta, pen=pg.mkPen('b', width=2))
        self.plot_gamma.plot(t_sim, gamma, pen=pg.mkPen('r', width=2))
        self.plot_sigma.plot(t_sim, sigma, pen=pg.mkPen('g', width=2))
        self.plot_Rt.plot(t_sim, Rt, pen=pg.mkPen('m', width=2))

class ArchiveDistributionDialog(QDialog):
    """Di\u00e1logo para analizar la distribuci\u00f3n de par\u00e1metros en las colonias."""
    def __init__(self, model: SEIRModel, optimizer: ACOROptimizer, parent=None):
        super().__init__(parent)
        self.model = model
        self.optimizer = optimizer
        self.setWindowTitle("An\u00e1lisis de Distribuci\u00f3n de Colonias")
        self.setGeometry(400, 250, 1200, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Valor Normalizado')
        self.plot_widget.setLabel('bottom', 'Par\u00e1metro')
        layout.addWidget(self.plot_widget)
        self.update_contents()

    def update_contents(self):
        self.plot_widget.clear()
        if not self.optimizer.archives:
            self.plot_widget.addItem(pg.TextItem(text="No hay archivos de colonias.", color='k'))
            return
        low, high = self.model.LOW, self.model.HIGH
        x_ticks = [list(enumerate(self.model.labels))]
        self.plot_widget.getAxis('bottom').setTicks(x_ticks)
        self.plot_widget.setTitle("Distribuci\u00f3n de Par\u00e1metros por Colonia (Media y Desv. Est.)")
        for i, archive in enumerate(self.optimizer.archives):
            normalized_archive = (archive - low) / (high - low)
            means = np.mean(normalized_archive, axis=0)
            stds = np.std(normalized_archive, axis=0)
            color = pg.intColor(i, self.optimizer.config.colonies_count, alpha=150)
            bar_item = pg.BarGraphItem(x=np.arange(self.model.DIM) + i*0.2, height=means, width=0.2, brush=color)
            self.plot_widget.addItem(bar_item)
        self.plot_widget.setYRange(0, 1)

class SensitivityAnalysisDialog(QDialog):
    """Di\u00e1logo para realizar un an\u00e1lisis de sensibilidad de los par\u00e1metros."""
    def __init__(self, model: SEIRModel, optimizer: ACOROptimizer, parent=None):
        super().__init__(parent)
        self.model = model
        self.optimizer = optimizer
        self.setWindowTitle("An\u00e1lisis de Sensibilidad de Par\u00e1metros")
        self.setGeometry(420, 270, 1200, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Cambio en MSE (%)')
        self.plot_widget.setLabel('bottom', 'Par\u00e1metro')
        layout.addWidget(self.plot_widget)
        self.status_label = QLabel("Calculando sensibilidad... Por favor, espere.")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        QApplication.processEvents()
        self.calculate_and_update()

    def calculate_and_update(self):
        base_params = self.optimizer.best_params_global
        base_cost = self.optimizer.best_cost_global
        if base_params is None:
            self.status_label.setText("No hay una soluci\u00f3n base para analizar.")
            return
        perturbation_factor = 0.05
        candidates = []
        for i in range(self.model.DIM):
            delta = (self.model.HIGH[i] - self.model.LOW[i]) * perturbation_factor
            p_plus = base_params.copy()
            p_plus[i] = min(p_plus[i] + delta, self.model.HIGH[i])
            candidates.append(p_plus)
            p_minus = base_params.copy()
            p_minus[i] = max(p_minus[i] - delta, self.model.LOW[i])
            candidates.append(p_minus)
        
        with Pool(max(1, int(psutil.cpu_count(logical=True) * 0.8))) as pool:
            costs = np.array(pool.map(self.model.fitness, candidates))
        
        sensitivities = []
        for i in range(self.model.DIM):
            max_change = max(abs(costs[2*i] - base_cost), abs(costs[2*i+1] - base_cost))
            sensitivity = (max_change / base_cost) * 100 if base_cost > 1e-9 else max_change
            sensitivities.append(sensitivity)
        
        self.plot_widget.clear()
        bar_item = pg.BarGraphItem(x=range(self.model.DIM), height=sensitivities, width=0.6, brush='r')
        self.plot_widget.addItem(bar_item)
        self.plot_widget.getAxis('bottom').setTicks([list(enumerate(self.model.labels))])
        self.plot_widget.setTitle(f"Sensibilidad Local (Impacto de perturbar +/-{perturbation_factor*100}%)")
        self.status_label.hide()

class ParametersDialog(QDialog):
    """Di\u00e1logo para ajustar los l\u00edmites de los par\u00e1metros del modelo."""
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Ajuste de L\u00edmites de Par\u00e1metros")
        self.setGeometry(300, 300, 560, 700)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tip: usa 'pi' para constantes. Ej: 2*pi, -pi/2"))
        self.table = QTableWidget(len(model.labels), 3)
        self.table.setHorizontalHeaderLabels(["Par\u00e1metro", "M\u00ednimo", "M\u00e1ximo"])
        for i, label in enumerate(model.labels):
            self.table.setItem(i, 0, QTableWidgetItem(label))
            self.table.item(i, 0).setFlags(Qt.ItemIsEnabled)
            self.table.setItem(i, 1, QTableWidgetItem(str(model.bounds[i, 0])))
            self.table.setItem(i, 2, QTableWidgetItem(str(model.bounds[i, 1])))
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.save_parameters)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def save_parameters(self):
        try:
            new_bounds = self.model.bounds.copy()
            for i in range(len(self.model.labels)):
                vmin = parse_numeric(self.table.item(i, 1).text())
                vmax = parse_numeric(self.table.item(i, 2).text())
                if vmax < vmin:
                    raise ValueError(f"En '{self.model.labels[i]}', el m\u00e1ximo es menor que el m\u00ednimo.")
                new_bounds[i, 0] = vmin
                new_bounds[i, 1] = vmax
            self.model.bounds = new_bounds
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Error de Valor", str(e))
