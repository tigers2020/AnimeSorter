#!/usr/bin/env python3
"""
tmdb_client.py의 모든 문법 오류를 수정하는 종합 스크립트
"""

import re

def comprehensive_fix_tmdb_client():
    """tmdb_client.py의 모든 문법 오류를 수정"""
    file_path = "src/core/tmdb_client.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 패턴 1: 불필요한 괄호 제거
        content = re.sub(r'return \[TMDBAnimeInfo\(\*\*item\) for item in cached_result\]\)', 
                        'return [TMDBAnimeInfo(**item) for item in cached_result]', content)
        
        # 패턴 2: Search -> Search()
        content = re.sub(r'search = tmdb\.Search\b', 'search = tmdb.Search()', content)
        
        # 패턴 3: TV -> TV()
        content = re.sub(r'tmdb\.TV\b', 'tmdb.TV()', content)
        
        # 패턴 4: Configuration -> Configuration()
        content = re.sub(r'tmdb\.Configuration\b', 'tmdb.Configuration()', content)
        
        # 패턴 5: 불필요한 괄호 제거 (다른 패턴들)
        content = re.sub(r'\)\)$', ')', content, flags=re.MULTILINE)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {file_path} 종합 문법 오류 수정 완료")
        return True
        
    except Exception as e:
        print(f"❌ {file_path} 수정 실패: {e}")
        return False

if __name__ == "__main__":
    comprehensive_fix_tmdb_client()
