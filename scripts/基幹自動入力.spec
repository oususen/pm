# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['kikan_input_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Program Files/WindowsApps/PythonSoftwareFoundation.Python.3.13_3.13.3312.0_x64__qbz5n2kfra8p0/tcl/tcl8.6', 'tcl8.6'), ('C:/Program Files/WindowsApps/PythonSoftwareFoundation.Python.3.13_3.13.3312.0_x64__qbz5n2kfra8p0/tcl/tk8.6', 'tk8.6')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='基幹自動入力',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='基幹自動入力',
)
