"""Prepare the rendered Long Core Control artwork as PNG and macOS ICNS."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "long_core_gui" / "ui" / "assets"
SOURCE_PATH = ASSETS / "long-core-control-source.png"
PNG_PATH = ASSETS / "long-core-control.png"
ICNS_PATH = ASSETS / "LongCoreControl.icns"
ICON_SIZES = [(16, 16), (32, 32), (128, 128), (256, 256), (512, 512), (1024, 1024)]


def main() -> None:
    if not SOURCE_PATH.is_file():
        raise RuntimeError(f"missing source artwork: {SOURCE_PATH}")

    with Image.open(SOURCE_PATH) as source:
        artwork = source.convert("RGBA")
        if artwork.width != artwork.height:
            raise RuntimeError("icon source artwork must be square")
        runtime_icon = artwork.resize((1024, 1024), Image.Resampling.LANCZOS)
        runtime_icon.save(PNG_PATH, format="PNG", optimize=True)
        runtime_icon.save(ICNS_PATH, format="ICNS", sizes=ICON_SIZES)

    print(f"Prepared {PNG_PATH.relative_to(ROOT)}")
    print(f"Prepared {ICNS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
