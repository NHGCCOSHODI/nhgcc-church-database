# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

BASE_DIR = Path.cwd()

added_files = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
    ('logo.ico', '.'),
    ('nhgcc_church.db', '.'),
]

if (BASE_DIR / 'NHGCC database .pdf').exists():
    added_files.append(('NHGCC database .pdf', '.'))

if (BASE_DIR / 'NHGCC_Oshodi_Church_App_Setup_and_User_Manual.pdf').exists():
    added_files.append(('NHGCC_Oshodi_Church_App_Setup_and_User_Manual.pdf', '.'))

a = Analysis(
    ['run_desktop.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'engineio.async_drivers.threading',
        'jinja2',
        'sqlalchemy.ext.baked',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.postgresql',
        'psycopg2',
        'psycopg',
        'psycopg_binary',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'apscheduler',
        'apscheduler.schedulers.background',
        'apscheduler.triggers.cron',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pandas', 'scipy', 'numpy', 'pygame', 'tcl8'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NHGCC_Church_Database',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico' if (BASE_DIR / 'logo.ico').exists() else None,
)
