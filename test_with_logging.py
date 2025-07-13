#!/usr/bin/env python3
"""
연도-시즌 혼동 수정 로직 로깅 테스트
"""

import logging
from pathlib import Path
from src.utils.file_cleaner import FileCleaner

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

def test_with_logging():
    """로깅과 함께 연도-시즌 혼동 수정 테스트"""
    
    print("=== 연도-시즌 혼동 수정 로깅 테스트 ===\n")
    
    # 문제가 있는 파일명들
    problem_files = [
        "Bleach 2004 Episode 01.mkv",  # 2004가 시즌으로 잘못 인식
        "[SubsPlease] Bleach 2022 E01.mkv",  # 2022가 시즌으로 잘못 인식
        "Attack on Titan 2013 E01.mkv",  # 2013이 시즌으로 잘못 인식
        "Demon Slayer 2019 Episode 1.mkv",  # 2019가 시즌으로 잘못 인식
    ]
    
    for filename in problem_files:
        print(f"📁 테스트: {filename}")
        
        # FileCleaner 실행 (로깅 포함)
        result = FileCleaner.clean_filename_static(Path(filename))
        
        print(f"   ✅ 결과: 제목='{result.title}', 시즌={result.season}, 연도={result.year}")
        print()

if __name__ == "__main__":
    test_with_logging() 