#!/usr/bin/env python3
"""
수정된 FileCleaner 시즌 리스트 처리 테스트 스크립트
"""

from pathlib import Path
from src.utils.file_cleaner import FileCleaner

def test_fixed_cleaner():
    """수정된 FileCleaner가 시즌 리스트를 올바르게 처리하는지 테스트"""
    
    # 시즌이 리스트로 반환될 수 있는 파일명들
    test_files = [
        # 다중 시즌 표기 (리스트로 반환될 것)
        "Attack on Titan S1-S4 Complete Collection.mkv",
        "Demon Slayer Season 1-2 Complete.mkv", 
        "Anime Collection S01S02S03.mkv",
        "Bleach Complete Series (Season 1-16) [1080p].mkv",
        
        # 다중 에피소드 표기 (에피소드가 리스트로 반환될 것)
        "[SubsPlease] Attack on Titan S04E01-E16 [1080p].mkv",
        
        # 일반적인 표기 (정상적으로 int로 반환될 것)
        "Attack on Titan S01E01.mkv",
        "Bleach S02E05.mp4",
        "Naruto Season 1 Episode 01.mkv",
        
        # 시즌 정보 없음
        "Bleach 13th tv.mkv",
        "One Piece Movie.mkv"
    ]
    
    print("=== 수정된 FileCleaner 시즌 리스트 처리 테스트 ===\n")
    
    for filename in test_files:
        print(f"📁 파일명: {filename}")
        
        try:
            # FileCleaner의 static 메서드 사용
            result = FileCleaner.clean_filename_static(Path(filename))
            
            print(f"   제목: {result.title}")
            print(f"   시즌: {result.season} (타입: {type(result.season).__name__})")
            print(f"   에피소드: {result.episode} (타입: {type(result.episode).__name__ if result.episode is not None else 'NoneType'})")
            print(f"   연도: {result.year}")
            print(f"   영화: {result.is_movie}")
            
            # 시즌이 정수인지 확인
            if isinstance(result.season, int):
                print(f"   ✅ 시즌이 올바르게 정수로 처리됨")
            else:
                print(f"   ❌ 시즌이 여전히 {type(result.season).__name__}임!")
                
            # 에피소드가 있으면 정수인지 확인
            if result.episode is not None:
                if isinstance(result.episode, int):
                    print(f"   ✅ 에피소드가 올바르게 정수로 처리됨")
                else:
                    print(f"   ❌ 에피소드가 여전히 {type(result.episode).__name__}임!")
            
            # 원본 GuessIt 결과도 확인 (extra_info에 저장됨)
            original_season = result.extra_info.get('season')
            if isinstance(original_season, list):
                print(f"   📋 원본 GuessIt 시즌: {original_season} (리스트) → 첫 번째 값 {result.season} 사용")
            
            original_episode = result.extra_info.get('episode')
            if isinstance(original_episode, list):
                print(f"   📋 원본 GuessIt 에피소드: {original_episode[:3]}{'...' if len(original_episode) > 3 else ''} (리스트) → 첫 번째 값 {result.episode} 사용")
                
        except Exception as e:
            print(f"   💥 처리 오류: {e}")
        
        print()

if __name__ == "__main__":
    test_fixed_cleaner() 