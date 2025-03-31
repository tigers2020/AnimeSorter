#!/usr/bin/env python3

import asyncio
import os
import sys
from pathlib import Path

async def main():
    print("AnimeSorter 테스트", flush=True)
    
    # 현재 디렉토리 확인
    current_dir = Path.cwd()
    print(f"현재 디렉토리: {current_dir}", flush=True)
    
    # 테스트 디렉토리 확인
    test_source = current_dir / "test_source"
    test_target = current_dir / "test_target"
    
    print(f"소스 디렉토리 존재: {test_source.exists()}", flush=True)
    print(f"대상 디렉토리 존재: {test_target.exists()}", flush=True)
    
    # 소스 디렉토리 파일 목록
    print("소스 디렉토리 파일:", flush=True)
    for file in test_source.iterdir():
        print(f" - {file.name}", flush=True)

if __name__ == "__main__":
    asyncio.run(main()) 