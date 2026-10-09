# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys


ROOT = Path(SPECPATH)
ICON = ROOT / "long_core_gui" / "ui" / "assets" / ("LongCoreControl.icns" if sys.platform == "darwin" else "long-core-control.ico")

a = Analysis(
    [str(ROOT / "long_core_gui" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (
            str(ROOT / "long_core_gui" / "ui" / "assets"),
            "long_core_gui/ui/assets",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick"],
    noarchive=False,
    optimize=1,
)

# Qt on Windows uses the OS ICU ABI. A Poppler/Conda ICU found on PATH
# has versioned exports and breaks QtCore at startup. Keep Qt-owned ICU
# libraries, but let Windows resolve the system ICU instead of bundling an
# unrelated library with the same filename.
if sys.platform == "win32":
    import PySide6
    qt_directory = Path(PySide6.__file__).resolve().parent
    a.binaries = [entry for entry in a.binaries
                  if Path(entry[0]).name.lower() != "icuuc.dll"
                  or Path(entry[1]).resolve().is_relative_to(qt_directory)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Long Core Control",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Long Core Control",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Long Core Control.app",
        icon=str(ICON),
        bundle_identifier="org.longcore.control",
        info_plist={
            "CFBundleDisplayName": "Long Core Control",
            "CFBundleName": "Long Core Control",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "Long Core paleomagnetic control software",
        },
    )
