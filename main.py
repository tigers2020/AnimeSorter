#!/usr/bin/env python3
"""
AnimeSorter - 애니메이션 파일 정리 도구
"""

import os
import sys
from pathlib import Path

def main():
    """애플리케이션 메인 함수"""
    print("AnimeSorter 시작")
    
    # 테스트 디렉토리 확인
    source_dir = Path("test_source")
    target_dir = Path("test_target")
    
    print(f"소스 디렉토리 존재: {source_dir.exists()}")
    print(f"대상 디렉토리 존재: {target_dir.exists()}")
    
    # 소스 디렉토리 파일 목록
    if source_dir.exists():
        print("소스 디렉토리 파일:")
        for file in source_dir.iterdir():
            if file.is_file():
                print(f" - {file.name}")
    else:
        print("소스 디렉토리가 존재하지 않습니다.")
    
    print("AnimeSorter 종료")

if __name__ == "__main__":
    main() 