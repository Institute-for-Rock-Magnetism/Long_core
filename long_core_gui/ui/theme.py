"""Visual system for the desktop application.

Modern macOS-style light theme: soft warm neutrals, rounded controls,
custom chevron indicators for combo/spin boxes, and WCAG AA contrast
(>= 4.5:1) for body text. Asset URLs are resolved from this file so the
stylesheet works regardless of the working directory.
"""

from __future__ import annotations

from pathlib import Path

_ASSETS = (Path(__file__).resolve().parent / "assets").as_posix()

APP_STYLE = r"""
/* ---------- palette ----------
   window bg        #f5f4f1
   surface          #ffffff
   border           #e2e0da / strong #d3d0c8
   ink              #1b2a2e
   ink-secondary    #4e5f63   (7.6:1 on white)
   sidebar          #0e3a41
   sidebar ink      #b9d5d0   (7.1:1 on sidebar)
   accent           #c0521e
   teal             #2d6970
   danger           #b3422f
   selection        #d7e8e6
*/

QWidget { color: #1b2a2e; background: #f5f4f1; }
QMainWindow, QStackedWidget { background: #f5f4f1; }
QWidget:disabled { color: #79817f; }

/* ---------- sidebar ---------- */
QFrame#sidebar { background: #0e3a41; border: none; }
QFrame#topbar { background: #ffffff; border-bottom: 1px solid #e2e0da; }
QLabel#brand { color: #ffffff; font: 700 21px "Avenir Next"; }
QLabel#brandCaption { color: #b9d5d0; font-size: 11px; }
QLabel#pageTitle { color: #1b2a2e; font: 700 30px "Avenir Next"; }
QLabel#pageSubtitle { color: #4e5f63; font-size: 13px; }
QLabel#eyebrow { color: #4e5f63; font: 700 10px "Avenir Next"; letter-spacing: 1px; }
QLabel#metricValue { color: #143940; font: 700 27px "Avenir Next"; }

/* ---------- badges ---------- */
QLabel#modeBadge { color: #5c4100; background: #f6d98a; border-radius: 12px; padding: 4px 12px; font-weight: 700; font-size: 11px; }
QLabel#statusGood { color: #174d40; background: #d9efe6; border-radius: 10px; padding: 3px 10px; font-weight: 700; }
QLabel#statusOff { color: #525d5c; background: #e9e8e3; border-radius: 10px; padding: 3px 10px; font-weight: 700; }

/* ---------- buttons ---------- */
QPushButton {
    min-height: 34px; border: 1px solid #d3d0c8; border-radius: 9px;
    padding: 0 16px; background: #ffffff; font-weight: 600;
}
QPushButton:hover { background: #faf9f6; border-color: #bfbbb1; }
QPushButton:pressed { background: #f0eee8; }
QPushButton:focus { border: 2px solid #8fb5b3; }
QPushButton[kind="primary"] { color: #ffffff; background: #c0521e; border-color: #c0521e; }
QPushButton[kind="primary"]:hover { background: #a94716; border-color: #a94716; }
QPushButton[kind="primary"]:pressed { background: #963c10; }
QPushButton[kind="primary"]:focus { border: 2px solid #f2b596; }
QPushButton[kind="danger"] { color: #ffffff; background: #b3422f; border-color: #b3422f; }
QPushButton[kind="danger"]:hover { background: #a03727; }
QPushButton[kind="danger"]:pressed { background: #8d2d1f; }
QPushButton[kind="nav"] {
    color: #cfe0dc; background: transparent; border: none; text-align: left;
    padding: 0 14px; min-height: 38px; border-radius: 9px; font-weight: 600;
}
QPushButton[kind="nav"]:hover { background: #17454c; }
QPushButton[kind="nav"]:checked { color: #ffffff; background: #1f535a; }
QPushButton:disabled { color: #79817f; background: #ecebe6; border-color: #dedcd5; }
QPushButton[kind="primary"]:disabled, QPushButton[kind="danger"]:disabled {
    color: #f3e9e4; background: #dfb3a3; border-color: #dfb3a3;
}

/* ---------- input fields ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background: #ffffff; border: 1px solid #d3d0c8; border-radius: 9px;
    padding: 6px 10px; selection-background-color: #2d6970;
    selection-color: #ffffff;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover { border-color: #b9b5ab; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus { border: 2px solid #2d6970; padding: 5px 9px; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QPlainTextEdit:disabled {
    background: #f1f0ec; color: #8d9492; border-color: #e2e0da;
}

/* ---------- combo box (custom chevron, rounded popup) ---------- */
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow { image: url(__ASSETS_DIR__/chevron-down.png); width: 12px; height: 8px; }
QComboBox::down-arrow:disabled { image: url(__ASSETS_DIR__/chevron-down-disabled.png); }
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid #d3d0c8; border-radius: 9px;
    padding: 5px; selection-background-color: #d7e8e6; selection-color: #143940;
    outline: 0;
}
QComboBox QAbstractItemView::item { min-height: 26px; padding: 0 8px; border-radius: 6px; }

/* ---------- spin boxes (macOS-style stepper) ---------- */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 22px; border: none; border-left: 1px solid #e2e0da;
    border-top-right-radius: 8px; background: #f7f6f2;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 22px; border: none; border-left: 1px solid #e2e0da;
    border-bottom-right-radius: 8px; background: #f7f6f2;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: #ecebe6; }
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed { background: #e0dfd9; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url(__ASSETS_DIR__/chevron-up.png); width: 12px; height: 8px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url(__ASSETS_DIR__/chevron-down.png); width: 12px; height: 8px; }
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled { image: none; }

/* ---------- cards and groups ---------- */
QFrame#metricCard {
    background: #ffffff; border: 1px solid #e2e0da; border-radius: 13px; padding: 14px 16px;
}
QGroupBox {
    background: #ffffff; border: 1px solid #e2e0da; border-radius: 13px;
    margin-top: 12px; padding: 18px 14px 14px 14px; font-weight: 700; font-size: 13px;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #3a4c50; }

/* ---------- tables ---------- */
QTableWidget {
    background: #ffffff; border: 1px solid #e2e0da; border-radius: 11px;
    gridline-color: #edeae4; alternate-background-color: #faf9f6;
    selection-background-color: #d7e8e6; selection-color: #143940;
}
QTableWidget::item { padding: 4px 8px; }
QHeaderView::section {
    background: #f2f0eb; color: #3f5659; border: none;
    border-right: 1px solid #e5e2db; border-bottom: 1px solid #e2e0da;
    padding: 9px 8px; font-weight: 700; font-size: 12px;
}
QTableCornerButton::section { background: #f2f0eb; border: none; border-right: 1px solid #e5e2db; }
QTableWidget QTableCornerButton::section { border-top-left-radius: 10px; }

/* ---------- progress ---------- */
QProgressBar {
    background: #e8e6e0; border: none; border-radius: 6px; height: 12px;
    text-align: center; color: #1b2a2e; font-size: 10px; font-weight: 700;
}
QProgressBar::chunk { background: #c0521e; border-radius: 6px; }

/* ---------- scrollbars ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c6c3bb; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #a9a69d; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c6c3bb; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #a9a69d; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

/* ---------- menus and tooltips ---------- */
QMenu {
    background: #ffffff; border: 1px solid #e2e0da; border-radius: 10px;
    padding: 6px; color: #1b2a2e;
}
QMenu::item { padding: 7px 28px 7px 14px; border-radius: 7px; }
QMenu::item:selected { background: #eef4f2; color: #143940; }
QMenu::separator { height: 1px; background: #e8e6e0; margin: 5px 8px; }
QToolTip {
    background: #1f2d30; color: #f4f2ec; border: none; border-radius: 6px;
    padding: 6px 10px; font-size: 12px;
}

/* ---------- misc ---------- */
QMessageBox { background: #f5f4f1; }
QStatusBar { background: #f5f4f1; color: #4e5f63; }
QListWidget, QListView { background: #ffffff; border: 1px solid #e2e0da; border-radius: 11px; }
"""

APP_STYLE = APP_STYLE.replace("__ASSETS_DIR__", _ASSETS)
