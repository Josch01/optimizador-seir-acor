# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDialogButtonBox, QLabel
)

class ModelConfigDialog(QDialog):
    """Diálogo para configurar la estructura del modelo SEIR (número de armónicos)."""
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Estructura del Modelo")
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        info_label = QLabel("Define el número de términos armónicos (cosenos) para cada tasa.\n0 = tasa constante, 1 o 2 = tasa variable.")
        layout.addWidget(info_label)

        self.spin_beta = QSpinBox()
        self.spin_beta.setRange(0, 2)
        self.spin_beta.setValue(current_config.get('beta', 2))
        
        self.spin_gamma = QSpinBox()
        self.spin_gamma.setRange(0, 2)
        self.spin_gamma.setValue(current_config.get('gamma', 2))

        self.spin_sigma = QSpinBox()
        self.spin_sigma.setRange(0, 2)
        self.spin_sigma.setValue(current_config.get('sigma', 2))

        form_layout.addRow("Armónicos para Beta (tasa de transmisión):", self.spin_beta)
        form_layout.addRow("Armónicos para Gamma (tasa de recuperación):", self.spin_gamma)
        form_layout.addRow("Armónicos para Sigma (tasa de incubación):", self.spin_sigma)
        
        layout.addLayout(form_layout)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_config(self):
        """Devuelve la nueva configuración seleccionada."""
        return {
            'beta': self.spin_beta.value(),
            'gamma': self.spin_gamma.value(),
            'sigma': self.spin_sigma.value()
        }
