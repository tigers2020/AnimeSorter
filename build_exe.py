#!/usr/bin/env python3
"""
AnimeSorter EXE 빌드 스크립트
PyInstaller를 사용하여 실행 파일 생성
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_pyinstaller():
    """PyInstaller 설치"""
    print("📦 PyInstaller 설치 중...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✅ PyInstaller 설치 완료")
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller 설치 실패: {e}")
        return False
    return True

def create_config_template():
    """API 키 설정을 위한 config 템플릿 생성"""
    config_content = """# AnimeSorter 설정 파일
# 이 파일을 수정하여 API 키를 설정하세요

tmdb:
  api_key: "your_tmdb_api_key_here"  # TMDB API 키를 여기에 입력하세요
  language: "ko-KR"
  cache_enabled: true

# 지원하는 파일 확장자
video_extensions:
  - ".mp4"
  - ".mkv" 
  - ".avi"
  - ".mov"
  - ".wmv"
  - ".m4v"
  - ".flv"

subtitle_extensions:
  - ".srt"
  - ".ass"
  - ".ssa"
  - ".sub"
  - ".idx"
  - ".smi"
  - ".vtt"

# 폴더 구조 템플릿
folder_template: "{title} ({year})"

# 기타 설정
keep_original_name: true
overwrite_existing: false
"""
    
    with open("config_template.yaml", "w", encoding="utf-8") as f:
        f.write(config_content)
    
    print("✅ config_template.yaml 생성 완료")

def create_spec_file():
    """PyInstaller spec 파일 생성"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

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
"""
    
    with open("AnimeSorter.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print("✅ AnimeSorter.spec 생성 완료")

def setup_api_key():
    """API 키 설정"""
    print("\n🔑 TMDB API 키 설정")
    print("TMDB API 키를 입력하세요 (Enter로 스킵 가능):")
    api_key = input("API 키: ").strip()
    
    if api_key and api_key != "your_tmdb_api_key_here":
        # config.yaml 파일 업데이트
        try:
            import yaml
            
            # 기존 config.yaml 읽기
            config_path = Path("config.yaml")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
            else:
                config = {}
            
            # API 키 설정
            if "tmdb" not in config:
                config["tmdb"] = {}
            config["tmdb"]["api_key"] = api_key
            
            # config.yaml 저장
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ API 키가 config.yaml에 저장되었습니다")
            return True
            
        except Exception as e:
            print(f"❌ API 키 저장 실패: {e}")
            return False
    else:
        print("⏭️  API 키 설정을 스킵했습니다. 나중에 config.yaml에서 수정할 수 있습니다.")
        return True

def build_exe():
    """EXE 파일 빌드"""
    print("\n🔨 EXE 파일 빌드 시작...")
    
    try:
        # PyInstaller 실행
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",  # 이전 빌드 파일 정리
            "--noconfirm",  # 덮어쓰기 확인 없이 진행
            "AnimeSorter.spec"
        ]
        
        print(f"실행 명령: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ EXE 파일 빌드 완료!")
            
            # 빌드 결과 확인
            exe_path = Path("dist/AnimeSorter.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📁 생성된 파일: {exe_path}")
                print(f"📏 파일 크기: {size_mb:.1f} MB")
                
                # config_template.yaml을 dist 폴더에 복사
                template_src = Path("config_template.yaml")
                template_dst = Path("dist/config_template.yaml")
                if template_src.exists():
                    shutil.copy2(template_src, template_dst)
                    print("✅ config_template.yaml을 dist 폴더에 복사")
                
                return True
            else:
                print("❌ EXE 파일이 생성되지 않았습니다")
                return False
        else:
            print("❌ EXE 파일 빌드 실패:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 빌드 중 오류 발생: {e}")
        return False

def create_readme():
    """README 파일 생성"""
    readme_content = """# AnimeSorter - 실행 파일

## 사용 방법

1. **API 키 설정**
   - `config_template.yaml` 파일을 `config.yaml`로 복사
   - `config.yaml` 파일에서 `your_tmdb_api_key_here`를 실제 TMDB API 키로 교체

2. **실행**
   - `AnimeSorter.exe` 파일을 더블클릭하여 실행

## TMDB API 키 발급

1. https://www.themoviedb.org/ 에서 계정 생성
2. 설정 → API → API 키 요청
3. 개인 사용 목적으로 신청
4. 발급받은 API 키를 config.yaml에 입력

## 설정 파일 (config.yaml)

```yaml
tmdb:
  api_key: "여기에_실제_API_키_입력"
  language: "ko-KR"
  cache_enabled: true

# 기타 설정들...
```

## 문제 해결

- **실행 안됨**: Windows Defender나 백신 프로그램에서 차단될 수 있습니다
- **API 오류**: config.yaml의 API 키가 올바른지 확인하세요
- **파일 권한 오류**: 관리자 권한으로 실행해보세요

## 지원

문제가 있으면 GitHub 이슈로 문의하세요.
"""
    
    with open("dist/README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ README.txt 생성 완료")

def main():
    """메인 빌드 프로세스"""
    print("🚀 AnimeSorter EXE 빌드 시작\n")
    
    # 1. PyInstaller 설치
    if not install_pyinstaller():
        return
    
    # 2. 설정 파일들 생성
    create_config_template()
    create_spec_file()
    
    # 3. API 키 설정
    if not setup_api_key():
        return
    
    # 4. EXE 빌드
    if not build_exe():
        return
    
    # 5. README 생성
    create_readme()
    
    print("\n🎉 AnimeSorter EXE 빌드 완료!")
    print("\n📁 dist 폴더에서 다음 파일들을 확인하세요:")
    print("   - AnimeSorter.exe (메인 실행 파일)")
    print("   - config_template.yaml (설정 템플릿)")
    print("   - README.txt (사용 설명서)")
    print("\n💡 사용하기 전에 config_template.yaml을 config.yaml로 복사하고")
    print("   TMDB API 키를 설정하세요!")

if __name__ == "__main__":
    main() 