# -*- coding: utf-8 -*-
"""
Contiene la l\u00f3gica para generar reportes en PDF de los resultados de una ejecuci\u00f3n.
"""
import os
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QPainter, QFont, QPen
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtPrintSupport import QPrinter

class ReportGenerator:
    def __init__(self, parent, model, run_result, acor_config):
        self.parent = parent
        self.model = model
        self.result = run_result
        self.config = acor_config
        self.printer = QPrinter(QPrinter.HighResolution)
        self.painter = QPainter()

    def generate_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self.parent, "Guardar Reporte PDF", f"Reporte_Ejecucion_{self.result.run_id}.pdf", "PDF Files (*.pdf)")
        if not file_path: return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_path)
        self.printer.setPageSize(QPrinter.A4)
        self.printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)

        if not self.painter.begin(self.printer):
            QMessageBox.warning(self.parent, "Error", "No se pudo iniciar la creaci\u00f3n del PDF.")
            return

        try:
            self._draw_content()
        finally:
            self.painter.end()
            self.parent.log(f"Reporte PDF guardado en {os.path.basename(file_path)}", "green")

    def _draw_content(self):
        # Coordenadas y fuentes
        self.y_pos = 0
        self.page_rect = self.printer.pageRect()
        self.font_title = QFont("Arial", 16, QFont.Bold)
        self.font_subtitle = QFont("Arial", 12, QFont.Bold)
        self.font_normal = QFont("Arial", 10)
        self.pen_black = QPen(Qt.black, 1)

        # --- T\u00edtulo y Cabecera ---
        self._draw_header()

        # --- Secci\u00f3n de Resumen ---
        self._draw_summary_section()

        # --- Secci\u00f3n de Gr\u00e1ficos ---
        self._draw_plots_section()

        # --- Secci\u00f3n de Par\u00e1metros ---
        self._draw_parameters_section()

    def _draw_header(self):
        self.painter.setFont(self.font_title)
        self.painter.drawText(self.page_rect, Qt.AlignHCenter, f"Reporte de Optimizaci\u00f3n - Ejecuci\u00f3n #{self.result.run_id}")
        self.y_pos += 60

        self.painter.setFont(self.font_normal)
        self.painter.drawText(QRectF(0, self.y_pos, self.page_rect.width(), 30), Qt.AlignRight, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.y_pos += 80

    def _draw_summary_section(self):
        self.painter.setFont(self.font_subtitle)
        self.painter.drawText(0, self.y_pos, "Resumen de la Ejecuci\u00f3n")
        self.y_pos += 50

        summary_data = {
            "Costo Final (Loss)": f"{self.result.best_cost:.6e}",
            "AIC": f"{self.result.aic:.2f}" if not np.isnan(self.result.aic) else "N/A (requiere MSE)",
            "BIC": f"{self.result.bic:.2f}" if not np.isnan(self.result.bic) else "N/A (requiere MSE)",
            "Funci\u00f3n de Loss": self.model.loss_type,
            "Duraci\u00f3n Total": f"{self.result.duration:.2f} segundos",
            "Iteraciones Realizadas": str(len(self.result.cost_history)),
            "Poblaci\u00f3n (N)": str(self.model.N),
            "Hormigas / Archivo": f"{self.config.n_ants} / {self.config.archive_size}",
            "Colonias / Migraci\u00f3n": f"{self.config.colonies_count} / {self.config.migration_interval} iters"
        }
        self._draw_table(summary_data, col1_width=200)

    def _draw_plots_section(self):
        self.y_pos += 50
        self.painter.setFont(self.font_subtitle)
        self.painter.drawText(0, self.y_pos, "Gr\u00e1ficos de Resultados")
        self.y_pos += 50

        # Renderizar widgets de gráficos a imágenes
        main_plot_pixmap = self.parent.plot_widget.grab()
        rt_plot_pixmap = self.parent.dashboard_plots["rt"].grab()

        plot_height = self.page_rect.width() * 0.4
        # Gr\u00e1fico Principal
        self.painter.drawPixmap(QRectF(0, self.y_pos, self.page_rect.width(), plot_height), main_plot_pixmap, QRectF(main_plot_pixmap.rect()))
        self.y_pos += plot_height + 50

        # Gr\u00e1fico de Rt
        self.painter.drawPixmap(QRectF(0, self.y_pos, self.page_rect.width(), plot_height), rt_plot_pixmap, QRectF(rt_plot_pixmap.rect()))
        self.y_pos += plot_height + 50

    def _draw_parameters_section(self):
        # Nueva p\u00e1gina si no hay espacio
        if self.y_pos > self.page_rect.height() * 0.6:
            self.printer.newPage()
            self.y_pos = 0
            self._draw_header()

        self.painter.setFont(self.font_subtitle)
        self.painter.drawText(0, self.y_pos, "Par\u00e1metros Finales Encontrados")
        self.y_pos += 50

        params_data = {label: f"{val:.6f}" for label, val in zip(self.model.labels, self.result.best_params)}
        self._draw_table(params_data, col1_width=100, columns=2)

    def _draw_table(self, data, col1_width, columns=1):
        self.painter.setFont(self.font_normal)
        self.painter.setPen(self.pen_black)
        row_height = 40
        col_width = (self.page_rect.width() / columns) - 20
        items_per_col = (len(data) + columns - 1) // columns
        
        initial_y = self.y_pos
        max_y = initial_y

        items = list(data.items())
        for i, (key, value) in enumerate(items):
            col_index = i // items_per_col
            row_index = i % items_per_col
            
            current_x = col_index * col_width
            current_y = initial_y + row_index * row_height

            # Dibujar llave (par\u00e1metro)
            key_rect = QRectF(current_x, current_y, col1_width, row_height)
            self.painter.drawText(key_rect, Qt.AlignVCenter, key)
            # Dibujar valor
            val_rect = QRectF(current_x + col1_width, current_y, col_width - col1_width, row_height)
            self.painter.drawText(val_rect, Qt.AlignVCenter, value)

            if current_y > max_y: max_y = current_y

        self.y_pos = max_y + row_height
