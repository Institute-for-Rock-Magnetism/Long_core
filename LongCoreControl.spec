# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH)
ICON = ROOT / "long_core_gui" / "ui" / "assets" / "LongCoreControl.icns"

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
