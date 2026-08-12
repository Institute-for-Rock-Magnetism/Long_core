#!/usr/bin/env python3
"""Batch-extract LabVIEW reconstruction evidence for a module.

For every VI in a source folder this script:

1. Runs the pylabview ``readRSRC`` extractor to produce an XML dataset with
   enum labels, type descriptors, connector info, and default data.
2. OCRs every exported block-diagram page (``vi_prints/dependencies``) plus
   the front panel, producing per-page text.
3. Writes everything under ``reconstructions/<module>/<VI basename>/`` so
   each module report can cite exact artifacts.

Usage:
    python tools/extract_vi.py Labview_source/Serial reconstructions/serial
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
DEPENDENCIES = ROOT / "vi_prints" / "dependencies"
PYTHON = sys.executable

if not DEPENDENCIES.is_dir():
    # The printed block-diagram export was removed from the repo during the
    # slim-down; the evidence in reconstructions/ is already committed, and
    # regeneration requires re-exporting the module's diagrams from LabVIEW.
    raise SystemExit(
        f"missing printed diagram export: {DEPENDENCIES}\n"
        "re-export the block diagrams from LabVIEW (or restore vi_prints/) "
        "before regenerating artifacts."
    )

# Diagram pages are exported as <name>d.png, <name>d1.png, ... and the front
# panel as <name>c.png. LabVIEW names with spaces are printed with
# underscores; ampersands and other punctuation are preserved.
_VI_REF = re.compile(r"([^\\/]+?)(?:\.vi|\.ctl)$", re.IGNORECASE)


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def find_images(vi_name: str) -> tuple[list[Path], Path | None]:
    """Return (diagram pages in numeric order, front panel) for a VI."""
    target = normalize(Path(vi_name).stem)
    diagrams: list[tuple[int, Path]] = []
    panel: Path | None = None
    for image in DEPENDENCIES.iterdir():
        if not image.name.endswith(".png"):
            continue
        stem = image.name[:-4]
        match = re.match(r"^(.*?)(d)(\d*)$", stem)
        if match:
            if normalize(match.group(1)) == target:
                page = int(match.group(3) or 0)
                diagrams.append((page, image))
        else:
            match = re.match(r"^(.*?)c$", stem)
            if match and normalize(match.group(1)) == target:
                panel = image
    diagrams.sort()
    return [image for _, image in diagrams], panel


def ocr(image: Path, output: Path) -> None:
    """OCR one image with the preprocessing that matches diagram text."""
    import PIL.Image
    import PIL.ImageOps

    scaled = image.with_suffix(".scaled.png")
    with PIL.Image.open(image) as im:
        gray = im.convert("L")
        gray = gray.resize(
            (gray.width * 3, gray.height * 3), PIL.Image.LANCZOS
        )
        gray = PIL.ImageOps.autocontrast(gray)
        gray = gray.point(lambda value: 0 if value < 180 else 255)
        gray.save(scaled)
    try:
        subprocess.run(
            ["tesseract", str(scaled), str(output.with_suffix("")), "--psm", "11"],
            check=True,
            capture_output=True,
        )
    finally:
        scaled.unlink(missing_ok=True)


def extract_vi(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    xml = destination / (source.stem.replace(" ", "_") + ".xml")
    if not xml.exists():
        subprocess.run(
            [PYTHON, "-m", "pylabview.readRSRC", "-x",
             "-i", str(source), "-m", str(xml)],
            check=False,
            capture_output=True,
        )
    diagrams, panel = find_images(source.name)
    for page, image in enumerate(diagrams):
        text = destination / f"diagram_page{page}.txt"
        if not text.exists():
            ocr(image, text)
    if panel is not None:
        text = destination / "front_panel.txt"
        if not text.exists():
            ocr(panel, text)
    if not diagrams and panel is None and not xml.exists():
        print(f"  !! no evidence found for {source.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="VI file or folder of VIs")
    parser.add_argument(
        "destination", help="output folder (e.g. reconstructions/serial)"
    )
    args = parser.parse_args()

    if shutil.which("tesseract") is None:
        print("tesseract is required but not on PATH", file=sys.stderr)
        return 1

    source = Path(args.source)
    destination = Path(args.destination)
    if source.is_file():
        files = [source]
    else:
        files = sorted(
            path for path in source.iterdir()
            if path.suffix.lower() in {".vi", ".ctl"} and path.is_file()
        )
    for vi in files:
        print(f"extracting {vi.name} ...")
        extract_vi(vi, destination / vi.stem.replace(" ", "_"))
    print(f"done: {len(files)} files -> {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
