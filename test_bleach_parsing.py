#!/usr/bin/env python3
"""
Bleach 파일명 파싱 문제 테스트 스크립트
"""

from guessit import guessit
from pathlib import Path
from src.utils.file_cleaner import FileCleaner

def test_bleach_parsing():
    """Bleach 파일명에서 연도가 시즌으로 잘못 인식되는 문제 확인"""
    
    # 실제 Bleach 파일명들 (연도가 포함된 경우)
    bleach_files = [
        "bleach 13th tv (2009).mkv",
        "bleach 11th tv (2009).mkv", 
        "bleach 3rd tv (2006).mkv",
        "bleach 2nd tv (2005).mkv",
        "bleach 12th tv (2009).mkv",
        "bleach 1st tv (2004).mkv",
        "Bleach 2004 Episode 01.mkv",
        "Bleach (2004) S01E01.mkv",
        "Bleach TV Series 2004-2012.mkv",
        "[SubsPlease] Bleach 2022 E01.mkv"
    ]
    
    print("=== Bleach 파일명 파싱 문제 테스트 ===\n")
    
    for filename in bleach_files:
        print(f"📁 파일명: {filename}")
        
        # 1. 원본 GuessIt 결과
        print("   🔍 GuessIt 원본 결과:")
        try:
            guessit_result = guessit(filename)
            print(f"      제목: {guessit_result.get('title')}")
            print(f"      시즌: {guessit_result.get('season')} (타입: {type(guessit_result.get('season')).__name__})")
            print(f"      에피소드: {guessit_result.get('episode')}")
            print(f"      연도: {guessit_result.get('year')}")
            print(f"      전체 결과: {dict(guessit_result)}")
        except Exception as e:
            print(f"      💥 GuessIt 오류: {e}")
        
        # 2. FileCleaner 처리 결과
        print("   🔧 FileCleaner 처리 결과:")
        try:
            clean_result = FileCleaner.clean_filename_static(Path(filename))
            print(f"      제목: {clean_result.title}")
            print(f"      시즌: {clean_result.season} (타입: {type(clean_result.season).__name__})")
            print(f"      에피소드: {clean_result.episode}")
            print(f"      연도: {clean_result.year}")
            print(f"      영화: {clean_result.is_movie}")
            
            # 문제 감지
            if clean_result.year and clean_result.season and clean_result.year == clean_result.season:
                print(f"      ⚠️  연도({clean_result.year})와 시즌({clean_result.season})이 동일함!")
            
            # 연도가 2000년대인데 시즌이 2000 이상이면 문제
            if clean_result.season and clean_result.season >= 2000:
                print(f"      ❌ 시즌이 연도처럼 보임: {clean_result.season}")
                
        except Exception as e:
            print(f"      💥 FileCleaner 오류: {e}")
        
        print()

def test_year_season_confusion():
    """연도와 시즌이 혼동되는 패턴 분석"""
    
    print("=== 연도-시즌 혼동 패턴 분석 ===\n")
    
    confusing_patterns = [
        "anime 2004 episode 01.mkv",  # 2004가 시즌으로 인식될 수 있음
        "anime (2004) S01E01.mkv",    # 괄호 있으면 연도로 인식
        "anime 2004 S01E01.mkv",      # 둘 다 있으면?
        "anime 04 episode 01.mkv",    # 04가 시즌인지 연도인지?
        "anime 2004-2005 complete.mkv", # 연도 범위
        "anime 2004 tv series.mkv"    # TV 키워드와 함께
    ]
    
    for pattern in confusing_patterns:
        print(f"📁 패턴: {pattern}")
        result = guessit(pattern)
        print(f"   시즌: {result.get('season')}")
        print(f"   연도: {result.get('year')}")
        print(f"   제목: {result.get('title')}")
        print()

if __name__ == "__main__":
    test_bleach_parsing()
    test_year_season_confusion() 