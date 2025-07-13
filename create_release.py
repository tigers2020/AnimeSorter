#!/usr/bin/env python3
"""
AnimeSorter 배포 패키지 생성 스크립트
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_release_package():
    """배포 패키지 생성"""
    
    # 버전 정보
    version = datetime.now().strftime("%Y%m%d")
    package_name = f"AnimeSorter_v{version}"
    
    print(f"🚀 AnimeSorter 배포 패키지 생성: {package_name}")
    
    # 임시 폴더 생성
    temp_dir = Path("temp_release")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    package_dir = temp_dir / package_name
    package_dir.mkdir()
    
    # 필요한 파일들 복사
    files_to_copy = [
        ("dist/AnimeSorter.exe", "AnimeSorter.exe"),
        ("dist/config_template.yaml", "config_template.yaml"),
        ("dist/config.yaml", "config.yaml"),
        ("dist/README.txt", "README.txt"),
        ("dist/설치_및_사용법.txt", "설치_및_사용법.txt"),
    ]
    
    print("📁 파일 복사 중...")
    for src, dst in files_to_copy:
        src_path = Path(src)
        dst_path = package_dir / dst
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"  ✅ {src} → {dst}")
        else:
            print(f"  ⚠️  {src} 파일을 찾을 수 없습니다")
    
    # 추가 폴더 생성
    (package_dir / "logs").mkdir(exist_ok=True)
    
    # 로그 폴더에 설명 파일 생성
    with open(package_dir / "logs" / "여기에_로그가_저장됩니다.txt", "w", encoding="utf-8") as f:
        f.write("이 폴더에 AnimeSorter 실행 로그가 저장됩니다.\n")
        f.write("문제 발생 시 이 폴더의 로그 파일을 확인하세요.\n")
    
    # ZIP 파일 생성
    zip_path = Path(f"{package_name}.zip")
    print(f"\n📦 ZIP 파일 생성: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(temp_dir)
                zipf.write(file_path, arcname)
                print(f"  📄 {arcname}")
    
    # 임시 폴더 정리
    shutil.rmtree(temp_dir)
    
    # 결과 출력
    zip_size = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n🎉 배포 패키지 생성 완료!")
    print(f"📁 파일: {zip_path}")
    print(f"📏 크기: {zip_size:.1f} MB")
    
    print(f"\n📋 패키지 내용:")
    print(f"  - AnimeSorter.exe (메인 실행 파일)")
    print(f"  - config.yaml (API 키 설정 파일)")
    print(f"  - config_template.yaml (설정 템플릿)")
    print(f"  - README.txt (영문 설명서)")
    print(f"  - 설치_및_사용법.txt (한글 상세 가이드)")
    print(f"  - logs/ (로그 폴더)")
    
    print(f"\n💡 사용자에게 전달할 내용:")
    print(f"  1. ZIP 파일 압축 해제")
    print(f"  2. config.yaml에서 TMDB API 키 설정")
    print(f"  3. AnimeSorter.exe 실행")

if __name__ == "__main__":
    create_release_package() 