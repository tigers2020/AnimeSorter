#!/usr/bin/env python3
"""
Bleach 6th TV 통합 테스트 스크립트
FileCleaner → TMDB 검색까지 전체 파이프라인 테스트
"""

import asyncio
import logging
from pathlib import Path
from src.utils.file_cleaner import FileCleaner
from src.plugin.tmdb.provider import TMDBProvider

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

async def test_bleach_integration():
    """Bleach 6th TV 전체 파이프라인 테스트"""
    
    print("=== Bleach 6th TV 통합 테스트 ===\n")
    
    # 실제 Bleach 6th TV 파일명들
    test_files = [
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP110-nezumi.mkv",
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP111-nezumi.mkv",
        "Bleach.6th.TV.2007.DVDRip-Hi.x264.AC3.1280.ReRip.EP112-nezumi.mkv",
    ]
    
    # TMDB API 키 (실제 키로 교체 필요)
    api_key = "your_tmdb_api_key_here"
    
    # 제공자 초기화
    tmdb_provider = TMDBProvider(api_key)
    
    try:
        await tmdb_provider.initialize()
        
        for filename in test_files:
            print(f"📁 파일명: {filename}")
            
            # 1단계: FileCleaner로 파일명 정제
            print("   🔧 1단계: 파일명 정제")
            clean_result = FileCleaner.clean_filename_static(Path(filename))
            
            print(f"      제목: '{clean_result.title}'")
            print(f"      시즌: {clean_result.season}")
            print(f"      에피소드: {clean_result.episode}")
            print(f"      연도: {clean_result.year}")
            
            # 2단계: TMDB 검색 (실제 API 키가 있는 경우에만)
            if api_key != "your_tmdb_api_key_here":
                print("   🔍 2단계: TMDB 검색")
                try:
                    # 점진적 검색 전략 테스트
                    search_result = await tmdb_provider.search(clean_result.title, clean_result.year)
                    
                    if search_result:
                        print(f"      ✅ 검색 성공!")
                        print(f"      TMDB ID: {search_result.get('id')}")
                        print(f"      제목: {search_result.get('name', search_result.get('title'))}")
                        print(f"      첫 방영일: {search_result.get('first_air_date', search_result.get('release_date'))}")
                        print(f"      장르: {[g.get('name') for g in search_result.get('genres', [])]}")
                    else:
                        print(f"      ❌ 검색 실패")
                        
                except Exception as e:
                    print(f"      💥 검색 오류: {e}")
            else:
                print("   ⏭️  2단계: TMDB 검색 스킵 (API 키 필요)")
                
            print()
            
    finally:
        await tmdb_provider.close()

def test_title_season_extraction():
    """제목에서 시즌 추출 함수 단독 테스트"""
    
    print("=== 제목 시즌 추출 함수 테스트 ===\n")
    
    from src.utils.file_cleaner import _extract_season_from_title
    
    test_titles = [
        "Bleach 6th TV",
        "Attack on Titan 3rd Season", 
        "Demon Slayer 2nd Season",
        "One Piece 20th Anniversary",
        "Naruto Shippuden 1st Season",
        "Dragon Ball Z 5th Series",
        "Bleach Season 6",
        "Anime 시즌 4",
        "Test 7기",
        "Show 3번째",
        "Normal Title",  # 시즌 정보 없음
        "Bleach 2004",   # 연도는 시즌이 아님
    ]
    
    for title in test_titles:
        season = _extract_season_from_title(title)
        print(f"'{title}' → 시즌: {season}")
    
    print()

if __name__ == "__main__":
    test_title_season_extraction()
    asyncio.run(test_bleach_integration()) 