# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src\\plex_nfs_watchdog\\plex_nfs_watchdog.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'plex_nfs_watchdog.modules.config',
        'plex_nfs_watchdog.modules.plex',
        'plex_nfs_watchdog.modules.watchdog',
        # Include any other modules here
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='plex-nfs-watchdog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='plex-nfs-watchdog',
)
