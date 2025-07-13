#!/usr/bin/env python3
"""
Bleach 6th TV 시즌 추출 로직 로깅 테스트
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

def test_bleach_6th_with_logging():
    """로깅과 함께 Bleach 6th TV 시즌 추출 테스트"""
    
    print("=== Bleach 6th TV 시즌 추출 로깅 테스트 ===\n")
    
    # 실제 문제 파일명들
    problem_files = [
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP110-nezumi.mkv",
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP111-nezumi.mkv", 
        "Bleach 6th Season Episode 110.mkv",
        "Bleach.6.TV.2007.EP110.mkv",
        "Attack on Titan 3rd Season.mkv",
        "Demon Slayer 2nd Season.mkv",
        "One Piece 20th Anniversary.mkv",
    ]
    
    for filename in problem_files:
        print(f"📁 테스트: {filename}")
        
        # FileCleaner 실행 (로깅 포함)
        result = FileCleaner.clean_filename_static(Path(filename))
        
        print(f"   ✅ 결과: 제목='{result.title}', 시즌={result.season}, 에피소드={result.episode}, 연도={result.year}")
        print()

if __name__ == "__main__":
    test_bleach_6th_with_logging() 