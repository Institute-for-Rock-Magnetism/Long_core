"""Generate isolated, offscreen previews of every application page.

Run: python tools/preview_ui.py --output .shots
This never opens a serial port or writes to the user's runtime workspace.
"""
from pathlib import Path
import argparse
import logging
import os
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from long_core_gui.infrastructure import ApplicationConfig
from long_core_gui.services import WorkspaceRepository
from long_core_gui.ui.main_window import MainWindow
from long_core_gui.ui.theme import APP_STYLE
from long_core_gui.domain import MeasurementMode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".shots"))
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # Qt's Windows offscreen plugin does not enumerate installed fonts.
    if sys.platform == "win32":
        font_dir = Path(os.environ.get("WINDIR", "C:/Windows"))/"Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
            QFontDatabase.addApplicationFont(str(font_dir/name))
    app.setStyleSheet(APP_STYLE)
    with tempfile.TemporaryDirectory() as directory:
        window = MainWindow(ApplicationConfig(), WorkspaceRepository(directory), logging.getLogger("preview"))
        window.show()
        queue = window.pages["Queue"]
        for sample in ("UC-001", "UC-002", "UC-003"):
            queue.sample_id.setText(sample)
            queue.mode.setCurrentText(MeasurementMode.DISCRETE.value)
            queue.positions.setText("0, 10, 20, 30, 40, 50")
            queue.add_step()
        window.start_run()
        deadline = time.monotonic()+15
        while window.engine.active and time.monotonic() < deadline:
            app.processEvents(); time.sleep(.01)
        if window.engine.active:
            window.engine.abort()
            while window.engine.active:
                app.processEvents(); time.sleep(.01)
            raise RuntimeError("preview simulation timed out")
        for size in ((1440, 900), (1080, 700)):
            window.resize(*size)
            for name in window.pages:
                window.show_page(name); app.processEvents()
                target = args.output/f"{name.lower().replace(' ', '-')}-{size[0]}.png"
                if not window.grab().save(str(target)):
                    raise RuntimeError(f"could not save {target}")
        window.close()
    print(f"Saved previews to {args.output.resolve()}")


if __name__ == "__main__":
    main()
