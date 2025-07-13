#!/usr/bin/env python3
"""
TMDB 점진적 제목 단순화 전략 및 애니메이션 우선 선택 테스트 스크립트
"""

import asyncio
import logging
from src.plugin.tmdb.provider import TMDBProvider

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

async def test_progressive_search():
    """점진적 검색 전략 테스트"""
    
    # TMDB API 키 (실제 키로 교체 필요)
    api_key = "your_tmdb_api_key_here"
    
    # 테스트할 제목들 (검색 실패가 예상되는 복잡한 제목들)
    test_titles = [
        "bleach 13th tv",
        "bleach 11th tv",
        "소드 아트 오프라인",
        "블리치 극장판 4기 지옥편",
        "은하철도 999 tv",
        "Attack on Titan Season 4 Part 2",
        "Demon Slayer Kimetsu no Yaiba Entertainment District Arc"
    ]
    
    provider = TMDBProvider(api_key)
    
    try:
        await provider.initialize()
        
        print("=== TMDB 점진적 검색 전략 테스트 ===\n")
        
        for title in test_titles:
            print(f"🔍 테스트 제목: '{title}'")
            
            # 점진적 제목 생성 확인
            progressive_titles = provider._generate_progressive_titles(title)
            print(f"   점진적 제목들: {progressive_titles}")
            
            # 실제 검색 시도
            try:
                result = await provider.search(title)
                if result:
                    media_type = result.get('media_type', 'unknown')
                    name_field = 'name' if media_type == 'tv' else 'title'
                    found_title = result.get(name_field, 'Unknown')
                    genres = [g.get('name', '') for g in result.get('genres', [])]
                    is_animation = '애니메이션' in genres or 'Animation' in genres
                    print(f"   ✅ 검색 성공: {found_title} ({media_type})")
                    print(f"      장르: {', '.join(genres)}")
                    print(f"      애니메이션: {'✅' if is_animation else '❌'}")
                else:
                    print(f"   ❌ 검색 실패: 모든 시도 실패")
            except Exception as e:
                print(f"   💥 오류 발생: {e}")
            
            print()
        
    finally:
        await provider.close()

def test_progressive_titles_generation():
    """점진적 제목 생성 로직만 테스트 (API 호출 없음)"""
    
    provider = TMDBProvider("dummy_key")
    
    test_cases = [
        "bleach 13th tv",
        "Attack on Titan Season 4 Part 2",
        "Demon Slayer Kimetsu no Yaiba Entertainment District Arc",
        "single",
        "two words",
        "one two three four five"
    ]
    
    print("=== 점진적 제목 생성 테스트 ===\n")
    
    for title in test_cases:
        progressive = provider._generate_progressive_titles(title)
        print(f"'{title}' → {progressive}")
    
    print()

def test_animation_filtering():
    """애니메이션 우선 선택 로직 테스트 (모의 데이터)"""
    
    provider = TMDBProvider("dummy_key")
    
    # 모의 검색 결과 (애니메이션과 실사 혼재)
    mock_results = [
        {
            "id": 1,
            "media_type": "tv",
            "name": "Bleach (Live Action)",
            "genre_ids": [18, 10759],  # Drama, Action & Adventure
            "popularity": 50.0
        },
        {
            "id": 2,
            "media_type": "tv", 
            "name": "Bleach",
            "genre_ids": [16, 10759, 10765],  # Animation, Action & Adventure, Sci-Fi & Fantasy
            "popularity": 80.0
        },
        {
            "id": 3,
            "media_type": "movie",
            "title": "Bleach Movie",
            "genre_ids": [28, 878],  # Action, Science Fiction
            "popularity": 30.0
        }
    ]
    
    print("=== 애니메이션 우선 선택 테스트 ===\n")
    print("모의 검색 결과:")
    for result in mock_results:
        name_field = "name" if result["media_type"] == "tv" else "title"
        is_animation = 16 in result["genre_ids"]
        print(f"  - {result[name_field]} ({result['media_type']}) - 애니: {'✅' if is_animation else '❌'}")
    
    filtered = provider._filter_and_sort_results(mock_results, "bleach")
    
    print(f"\n필터링 결과 (총 {len(filtered)}개):")
    for i, result in enumerate(filtered):
        name_field = "name" if result["media_type"] == "tv" else "title"
        is_animation = 16 in result["genre_ids"]
        print(f"  {i+1}. {result[name_field]} ({result['media_type']}) - 애니: {'✅' if is_animation else '❌'}")
    
    print()

if __name__ == "__main__":
    print("1. 점진적 제목 생성 로직 테스트")
    test_progressive_titles_generation()
    
    print("2. 애니메이션 우선 선택 로직 테스트")
    test_animation_filtering()
    
    print("3. 실제 TMDB API 테스트 (API 키 필요)")
    print("   config.yaml에서 TMDB API 키를 설정한 후 실행하세요.")
    
    # 실제 API 테스트를 원하면 아래 주석 해제
    # asyncio.run(test_progressive_search()) 