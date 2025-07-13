#!/usr/bin/env python3
"""
Bleach 6th TV 파일명 파싱 테스트 스크립트
"""

from guessit import guessit
from pathlib import Path
from src.utils.file_cleaner import FileCleaner

def test_bleach_6th_parsing():
    """Bleach 6th TV 파일명이 어떻게 파싱되는지 확인"""
    
    # 실제 Bleach 6th TV 파일명들
    bleach_6th_files = [
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP110-nezumi.mkv",
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP111-nezumi.mkv",
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP112-nezumi.mkv",
        # 다른 시즌 표기 방식들도 테스트
        "Bleach 6th Season Episode 110.mkv",
        "Bleach Season 6 Episode 110.mkv", 
        "Bleach S06E110.mkv",
        "Bleach - 6th TV Series.mkv",
        "Bleach.6.TV.2007.EP110.mkv"
    ]
    
    print("=== Bleach 6th TV 파일명 파싱 테스트 ===\n")
    
    for filename in bleach_6th_files:
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
            
            # 시즌 6이어야 하는데 1이면 문제
            if clean_result.season == 1:
                print(f"      ❌ 시즌이 1로 잘못 인식됨 (6이어야 함)")
            elif clean_result.season == 6:
                print(f"      ✅ 시즌 6으로 올바르게 인식됨")
            else:
                print(f"      ⚠️  예상과 다른 시즌: {clean_result.season}")
                
        except Exception as e:
            print(f"      💥 FileCleaner 오류: {e}")
        
        print()

def analyze_6th_pattern():
    """6th 패턴이 어떻게 인식되는지 분석"""
    
    print("=== '6th' 패턴 분석 ===\n")
    
    patterns = [
        "anime 6th tv.mkv",
        "anime 6th season.mkv", 
        "anime 6.mkv",
        "anime 6th.mkv",
        "anime sixth.mkv",
        "anime season 6.mkv",
        "anime s06.mkv",
        "anime s6.mkv"
    ]
    
    for pattern in patterns:
        print(f"📁 패턴: {pattern}")
        result = guessit(pattern)
        print(f"   시즌: {result.get('season')}")
        print(f"   제목: {result.get('title')}")
        print(f"   전체: {dict(result)}")
        print()

if __name__ == "__main__":
    test_bleach_6th_parsing()
    analyze_6th_pattern() 