#!/usr/bin/env python3
"""
tmdb_client.py의 모든 문법 오류를 최종 수정하는 스크립트
"""

import re

def final_fix_tmdb_client():
    """tmdb_client.py의 모든 문법 오류를 최종 수정"""
    file_path = "src/core/tmdb_client.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 패턴 1: 불필요한 괄호 제거 (docstring)
        content = re.sub(r'""".*?""")', r'"""', content)
        
        # 패턴 2: get_cache()( -> get_cache(
        content = re.sub(r'\.get_cache\(\)\s*\(', '.get_cache(', content)
        
        # 패턴 3: set_cache()( -> set_cache(
        content = re.sub(r'\.set_cache\(\)\s*\(', '.set_cache(', content)
        
        # 패턴 4: TV_Seasons -> TV_Seasons()
        content = re.sub(r'tmdb\.TV_Seasons\b', 'tmdb.TV_Seasons()', content)
        
        # 패턴 5: TV_Episodes -> TV_Episodes()
        content = re.sub(r'tmdb\.TV_Episodes\b', 'tmdb.TV_Episodes()', content)
        
        # 패턴 6: 불필요한 괄호 제거 (다른 패턴들)
        content = re.sub(r'\)\)$', ')', content, flags=re.MULTILINE)
        
        # 패턴 7: emit()() -> emit()
        content = re.sub(r'\.emit\(\)\s*\(\)', '.emit()', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {file_path} 최종 문법 오류 수정 완료")
        return True
        
    except Exception as e:
        print(f"❌ {file_path} 수정 실패: {e}")
        return False

if __name__ == "__main__":
    final_fix_tmdb_client()


