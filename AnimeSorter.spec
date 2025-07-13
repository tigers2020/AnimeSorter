# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 프로젝트 루트 경로
project_root = Path.cwd()

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 설정 파일들
        ('config.yaml', '.'),
        ('config_template.yaml', '.'),
        
        # 아이콘 파일 (있는 경우)
        # ('icon.ico', '.'),
    ],
    hiddenimports=[
        # PyQt5 관련 모듈들
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
        
        # aiohttp 관련 모듈들
        'aiohttp',
        'aiohttp.client',
        'aiohttp.connector',
        
        # 기타 필요한 모듈들
        'guessit',
        'yaml',
        'configparser',
        'asyncio',
        'concurrent.futures',
        'threading',
        'multiprocessing',
        
        # src 패키지 모듈들
        'src.config.config_manager',
        'src.utils.file_cleaner',
        'src.plugin.tmdb.provider',
        'src.plugin.tmdb.api.client',
        'src.plugin.tmdb.api.endpoints',
        'src.ui.main_window',
        'src.ui.widgets.control_panel',
        'src.ui.widgets.directory_selector',
        'src.ui.widgets.file_list_table',
        'src.ui.widgets.settings_dialog',
        'src.ui.widgets.status_panel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 불필요한 모듈들 제외
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AnimeSorter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 애플리케이션이므로 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일 경로 (있는 경우 설정)
)
