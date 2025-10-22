# -*- coding: utf-8 -*-
import numpy as np
import emcee
import corner
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QSpinBox,
    QDialogButtonBox, QTextEdit, QProgressBar, QPushButton, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    """Widget para incrustar un gráfico de Matplotlib en PyQt."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)

class MCMCWorker(QThread):
    """Ejecuta el muestreador MCMC en un hilo separado."""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(object)

    def __init__(self, model, start_params, n_walkers, n_steps, n_burn, n_thin):
        super().__init__()
        self.model = model
        self.start_params = start_params
        self.n_walkers = n_walkers
        self.n_steps = n_steps
        self.n_burn = n_burn
        self.n_thin = n_thin
        self._is_running = True

    def stop(self):
        self._is_running = False

    def log_prob(self, theta):
        # Penalización si los parámetros están fuera de los límites
        if not np.all((self.model.LOW <= theta) & (theta <= self.model.HIGH)):
            return -np.inf
        
        # La función de verosimilitud es proporcional a la inversa del error (MSE)
        # log(prob) es proporcional a -MSE
        fitness = self.model.fitness(theta)
        return -fitness

    def run(self):
        try:
            ndim = self.model.DIM
            # Inicializar caminantes en una pequeña bola alrededor de la mejor solución de ACOR
            pos = self.start_params + 1e-4 * np.random.randn(self.n_walkers, ndim)
            
            sampler = emcee.EnsembleSampler(self.n_walkers, ndim, self.log_prob)
            
            self.progress_signal.emit(0, f"Ejecutando MCMC con {self.n_walkers} caminantes...")
            
            # Iterar y actualizar el progreso
            for i, result in enumerate(sampler.sample(pos, iterations=self.n_steps, progress=False)):
                if not self._is_running:
                    self.progress_signal.emit(100, "Detenido por el usuario.")
                    self.finished_signal.emit(None)
                    return
                
                progress_pct = int((i + 1) * 100 / self.n_steps)
                if i % 20 == 0: # Actualizar no tan frecuentemente para no ralentizar
                    self.progress_signal.emit(progress_pct, f"Paso {i+1}/{self.n_steps} completado.")
            
            self.progress_signal.emit(100, "Muestreo completado. Procesando resultados...")
            
            # Descartar el período de quemado y adelgazar la cadena
            flat_samples = sampler.get_chain(discard=self.n_burn, thin=self.n_thin, flat=True)
            
            self.progress_signal.emit(100, "Análisis finalizado.")
            self.finished_signal.emit(flat_samples)

        except Exception as e:
            self.progress_signal.emit(0, f"Error en el worker MCMC: {e}")
            self.finished_signal.emit(None)

class MCMCDialog(QDialog):
    def __init__(self, model, result, parent=None):
        super().__init__(parent)
        self.model = model
        self.result = result
        self.worker = None
        
        self.setWindowTitle("Análisis de Incertidumbre de Parámetros (MCMC)")
        self.setGeometry(450, 300, 900, 700)
        self.setAttribute(11) # WA_DeleteOnClose

        # --- Layout Principal y Pestañas ---
        main_layout = QVBoxLayout(self)
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # --- Pestaña de Configuración ---
        config_tab = QWidget()
        form_layout = QFormLayout(config_tab)
        self.spin_walkers = QSpinBox(); self.spin_walkers.setRange(2 * self.model.DIM, 500); self.spin_walkers.setValue(50)
        self.spin_steps = QSpinBox(); self.spin_steps.setRange(100, 10000); self.spin_steps.setValue(1000)
        self.spin_burn = QSpinBox(); self.spin_burn.setRange(50, 5000); self.spin_burn.setValue(200)
        self.spin_thin = QSpinBox(); self.spin_thin.setRange(1, 100); self.spin_thin.setValue(15)
        form_layout.addRow("Número de Caminantes:", self.spin_walkers)
        form_layout.addRow("Número de Pasos:", self.spin_steps)
        form_layout.addRow("Pasos de Quemado (Burn-in):", self.spin_burn)
        form_layout.addRow("Adelgazamiento (Thinning):", self.spin_thin)
        tabs.addTab(config_tab, "Configuración")

        # --- Pestaña de Progreso y Resultados ---
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        self.progress_bar = QProgressBar()
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        results_layout.addWidget(self.log_text, 1)
        results_layout.addWidget(self.progress_bar, 0)
        results_layout.addWidget(self.canvas, 5)
        tabs.addTab(results_tab, "Progreso y Resultados")

        # --- Botones ---
        self.btn_run = QPushButton("Ejecutar Análisis")
        self.btn_run.clicked.connect(self.run_mcmc)
        self.btn_stop = QPushButton("Detener"); self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_mcmc)
        
        button_box = QDialogButtonBox()
        button_box.addButton(self.btn_run, QDialogButtonBox.ActionRole)
        button_box.addButton(self.btn_stop, QDialogButtonBox.ActionRole)
        main_layout.addWidget(button_box)

    def log(self, message):
        self.log_text.append(message)

    def run_mcmc(self):
        n_walkers = self.spin_walkers.value()
        n_steps = self.spin_steps.value()
        n_burn = self.spin_burn.value()
        
        if n_burn >= n_steps:
            QMessageBox.warning(self, "Configuración Inválida", "El período de quemado debe ser menor que el número total de pasos.")
            return

        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log("Iniciando análisis MCMC...")

        self.worker = MCMCWorker(
            model=self.model,
            start_params=self.result.best_params,
            n_walkers=n_walkers,
            n_steps=n_steps,
            n_burn=n_burn,
            n_thin=self.spin_thin.value()
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_mcmc_finished)
        self.worker.start()

    def stop_mcmc(self):
        if self.worker:
            self.worker.stop()
            self.log("Enviando señal de detención...")
            self.btn_stop.setEnabled(False)

    def update_progress(self, pct, msg):
        self.progress_bar.setValue(pct)
        self.log(msg)

    def on_mcmc_finished(self, samples):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.worker = None

        if samples is None:
            self.log("El análisis no produjo resultados.")
            return
        
        self.log("Generando gráfico de esquina (corner plot)...")
        
        # Limpiar el canvas anterior
        self.canvas.fig.clear()
        
        # Generar el gráfico
        try:
            corner.corner(
                samples, 
                labels=self.model.labels, 
                truths=self.result.best_params,
                fig=self.canvas.fig
            )
            self.canvas.fig.tight_layout()
            self.canvas.draw()
            self.log("Gráfico generado.")
        except Exception as e:
            self.log(f"Error al generar el gráfico: {e}")

    def closeEvent(self, event):
        self.stop_mcmc()
        super().closeEvent(event)