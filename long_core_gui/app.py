#!/usr/bin/env python3
"""Application bootstrap for Long Core Control."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

# Support both ``python -m long_core_gui`` and direct ``python app.py`` use.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from long_core_gui.infrastructure import (
    ApplicationConfig,
    ConfigCorruptionError,
    load_application_config,
    save_application_config,
    setup_structured_logging,
)
from long_core_gui.services.storage import WorkspaceRepository
from long_core_gui.ui.main_window import MainWindow
from long_core_gui.ui.theme import APP_STYLE


def _application_home() -> Path:
    override = os.environ.get("LONG_CORE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    return Path(location or (Path.home() / ".long-core-control"))


def create_application(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Long Core Control")
    app.setOrganizationName("Institute for Rock Magnetism")
    app.setApplicationVersion("0.2.0")
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, False)
    app.setFont(QFont("Avenir Next", 11))
    app.setStyleSheet(APP_STYLE)

    home = _application_home()
    config_path = home / "config" / "application.json"
    startup_warning: str | None = None
    try:
        config = load_application_config(config_path)
    except ConfigCorruptionError as exc:
        config = ApplicationConfig()
        startup_warning = str(exc)
    if not config_path.exists():
        save_application_config(config_path, config)

    logger = setup_structured_logging(
        home / config.log_directory / "long-core.jsonl",
        level=config.log_level,
        max_bytes=config.log_max_bytes,
        backup_count=config.log_backup_count,
    )
    repository = WorkspaceRepository(home / config.data_directory)
    window = MainWindow(config=config, repository=repository, logger=logger)
    if startup_warning:
        QMessageBox.warning(
            window,
            "Configuration recovery",
            startup_warning + "\n\nSafe simulation defaults were loaded.",
        )
    return app, window


def main() -> int:
    app, window = create_application()
    logger = logging.getLogger("long_core_gui")

    def report_uncaught(error_type, error, traceback) -> None:
        logger.critical("uncaught application error", exc_info=(error_type, error, traceback))
        QMessageBox.critical(window, "Unexpected error", str(error))

    sys.excepthook = report_uncaught
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
