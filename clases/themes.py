# -*- coding: utf-8 -*-
"""
Contiene las hojas de estilo (QSS) para los temas claro y oscuro de la aplicación.
"""

DARK_THEME_QSS = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    border: 0px;
    font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 13px;
}
QLabel {
    color: #f0f0f0;
}
QTabWidget > QWidget {
    background-color: #2b2b2b;
}
QGroupBox {
    background-color: #3c3c3c;
    border: 1px solid #505050;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 6px;
    color: #a0a0a0;
}
QLineEdit {
    background-color: #3a3a3a;
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 4px 6px;
    color: #f0f0f0;
}
QLineEdit:focus {
    border: 1px solid #0078d7;
    background-color: #4a4a4a;
}
QPushButton {
    background-color: #555;
    border: 1px solid #666;
    padding: 5px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #666;
}
QPushButton:pressed {
    background-color: #4E4E4E;
}
QPushButton:disabled {
    background-color: #404040;
    color: #888;
}
QTextEdit {
    background-color: #222;
    border: 1px solid #505050;
    color: #ddd;
    border-radius: 4px;
    padding: 5px;
}
QProgressBar {
    border: 1px solid #505050;
    border-radius: 5px;
    text-align: center;
    color: #f0f0f0;
    background-color: #3a3a3a;
}
QProgressBar::chunk {
    background-color: #00aaff; /* Modern blue */
    border-radius: 4px;
    margin: 0.5px;
}
QComboBox {
    background-color: #444;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 3px;
}
QComboBox::drop-down {
    border: 0px;
}
QComboBox::down-arrow {
    image: url(no-such-file.png); /* Oculta la flecha por defecto */
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
}
QSplitter::handle {
    background: #555;
}
QSplitter::handle:horizontal {
    width: 4px;
}
QSplitter::handle:vertical {
    height: 4px;
}
QMenuBar {
    background-color: #3c3c3c;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 8px;
}
QMenuBar::item:selected {
    background: #555;
}
QMenu {
    background-color: #3c3c3c;
    border: 1px solid #555;
}
QMenu::item {
    padding: 4px 24px;
}
QMenu::item:selected {
    background-color: #555;
}
QTabWidget::pane {
    border-top: 1px solid #555;
}
QTabBar::tab {
    background: #3c3c3c;
    border: 1px solid #555;
    padding: 6px;
    border-bottom: none;
}
QTabBar::tab:selected {
    background: #2b2b2b;
    border-bottom: 1px solid #2b2b2b;
}
QTabBar::tab:!selected {
    background: #4a4a4a;
    margin-top: 2px;
}
"""

LIGHT_THEME_QSS = """
QWidget {
    background-color: #f0f0f0;
    color: #000000;
    border: 0px;
    font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 13px;
}
QLabel {
    color: #333333;
}
QTabWidget > QWidget {
    background-color: #f0f0f0;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin-top: 1ex;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 6px;
    color: #666666;
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px 6px;
    color: #333333;
}
QLineEdit:focus {
    border: 1px solid #0078d7;
    background-color: #f8f8f8;
}
QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #c0c0c0;
    padding: 5px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #e8e8e8;
}
QPushButton:pressed {
    background-color: #d0d0d0;
}
QPushButton:disabled {
    background-color: #d0d0d0;
    color: #a0a0a0;
}
QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    color: #333333;
    border-radius: 4px;
    padding: 5px;
}
QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 5px;
    text-align: center;
    color: #000000;
    background-color: #e0e0e0;
}
QProgressBar::chunk {
    background-color: #0078d7; /* Modern blue */
    border-radius: 4px;
    margin: 0.5px;
}
"""