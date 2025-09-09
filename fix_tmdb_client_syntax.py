#!/usr/bin/env python3
"""
tmdb_client.py의 문법 오류를 수정하는 스크립트
"""

import re

def fix_tmdb_client_syntax():
    """tmdb_client.py의 문법 오류를 수정"""
    file_path = "src/core/tmdb_client.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 패턴 1: wait_if_needed -> wait_if_needed()
        content = re.sub(r'\.wait_if_needed\b', '.wait_if_needed()', content)
        
        # 패턴 2: get_cache -> get_cache()
        content = re.sub(r'\.get_cache\b', '.get_cache()', content)
        
        # 패턴 3: set_cache -> set_cache()
        content = re.sub(r'\.set_cache\b', '.set_cache()', content)
        
        # 패턴 4: exists -> exists()
        content = re.sub(r'\.exists\b', '.exists()', content)
        
        # 패턴 5: is_file -> is_file()
        content = re.sub(r'\.is_file\b', '.is_file()', content)
        
        # 패턴 6: is_dir -> is_dir()
        content = re.sub(r'\.is_dir\b', '.is_dir()', content)
        
        # 패턴 7: items -> items()
        content = re.sub(r'\.items\b', '.items()', content)
        
        # 패턴 8: values -> values()
        content = re.sub(r'\.values\b', '.values()', content)
        
        # 패턴 9: keys -> keys()
        content = re.sub(r'\.keys\b', '.keys()', content)
        
        # 패턴 10: emit -> emit()
        content = re.sub(r'\.emit\b', '.emit()', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {file_path} 문법 오류 수정 완료")
        return True
        
    except Exception as e:
        print(f"❌ {file_path} 수정 실패: {e}")
        return False

if __name__ == "__main__":
    fix_tmdb_client_syntax()
