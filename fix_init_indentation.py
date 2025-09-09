#!/usr/bin/env python3
"""
src/app/__init__.py 파일의 들여쓰기 문제를 수정하는 스크립트
"""

import re

def fix_init_file():
    """__init__.py 파일의 들여쓰기 문제를 수정"""
    file_path = "src/app/__init__.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 패턴: from .module import (Item1, Item2,)
    #                      Item3, Item4,
    # 이를 다음과 같이 수정:
    # from .module import (Item1, Item2,
    #                      Item3, Item4,
    
    # 여러 줄 import 문의 들여쓰기 문제를 수정
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # from .module import (Item1, Item2,) 패턴을 찾음
        if re.match(r'^from \.(\w+) import \([^)]+,\s*\)$', line):
            # 다음 줄이 들여쓰기된 import 항목인지 확인
            if i + 1 < len(lines) and lines[i + 1].startswith(' '):
                # 첫 번째 줄의 마지막 괄호를 제거
                fixed_line = line.rstrip(')')
                fixed_lines.append(fixed_line)
                i += 1
                
                # 들여쓰기된 줄들을 추가
                while i < len(lines) and lines[i].startswith(' '):
                    fixed_lines.append(lines[i])
                    i += 1
                
                # 마지막 줄에 닫는 괄호 추가
                if fixed_lines and not fixed_lines[-1].endswith(')'):
                    fixed_lines.append(')')
            else:
                fixed_lines.append(line)
                i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    # 수정된 내용을 파일에 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    
    print(f"✅ {file_path} 파일의 들여쓰기 문제를 수정했습니다.")

if __name__ == "__main__":
    fix_init_file()


