#!/usr/bin/env python3
"""
GuessIt 시즌 파싱 테스트 스크립트
"""

from guessit import guessit

def test_guessit_season_parsing():
    """GuessIt이 시즌 정보를 어떻게 파싱하는지 테스트"""
    
    test_files = [
        # 일반적인 시즌 표기
        "Attack on Titan S01E01.mkv",
        "Bleach S02E05.mp4",
        "Naruto Season 1 Episode 01.mkv",
        
        # 복잡한 시즌 표기
        "Bleach - S01-S02 Complete.mkv",
        "Attack on Titan S1-S4 Complete Collection.mkv", 
        "Demon Slayer Season 1-2 Complete.mkv",
        
        # 다중 시즌 표기
        "Anime Collection S01S02S03.mkv",
        "Complete Series S1S2S3S4.mkv",
        
        # 모호한 표기
        "Bleach 13th tv.mkv",
        "One Piece 1000+ Episodes.mkv",
        
        # 실제 문제가 될 수 있는 파일명
        "[SubsPlease] Attack on Titan S04E01-E16 [1080p].mkv",
        "Bleach Complete Series (Season 1-16) [1080p].mkv"
    ]
    
    print("=== GuessIt 시즌 파싱 테스트 ===\n")
    
    for filename in test_files:
        print(f"📁 파일명: {filename}")
        
        try:
            result = guessit(filename)
            
            # 시즌 정보 확인
            season = result.get('season')
            if season is not None:
                season_type = type(season).__name__
                print(f"   시즌: {season} (타입: {season_type})")
                
                if isinstance(season, list):
                    print(f"   ⚠️  리스트 발견! 길이: {len(season)}, 내용: {season}")
            else:
                print(f"   시즌: None")
            
            # 에피소드 정보 확인
            episode = result.get('episode')
            if episode is not None:
                episode_type = type(episode).__name__
                print(f"   에피소드: {episode} (타입: {episode_type})")
                
                if isinstance(episode, list):
                    print(f"   ⚠️  에피소드도 리스트! 길이: {len(episode)}, 내용: {episode}")
            else:
                print(f"   에피소드: None")
                
            # 제목 확인
            title = result.get('title')
            print(f"   제목: {title}")
            
        except Exception as e:
            print(f"   💥 파싱 오류: {e}")
        
        print()

if __name__ == "__main__":
    test_guessit_season_parsing() 