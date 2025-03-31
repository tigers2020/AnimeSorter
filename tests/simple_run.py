import os
import yaml
from pathlib import Path

print("AnimeSorter 간단 테스트")

# 설정 파일 로드
try:
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    print("설정 로드 성공")
except Exception as e:
    print(f"설정 로드 오류: {e}")
    exit(1)

# 디렉토리 확인
source_dir = Path(config.get('source_dir'))
target_dir = Path(config.get('target_dir'))

print(f"소스 디렉토리: {source_dir} (존재: {source_dir.exists()})")
print(f"대상 디렉토리: {target_dir} (존재: {target_dir.exists()})")

# 소스 디렉토리 파일 확인
if source_dir.exists():
    print("소스 디렉토리 파일:")
    for file in source_dir.iterdir():
        if file.is_file():
            print(f" - {file.name}")
else:
    print("소스 디렉토리가 존재하지 않습니다.")

print("테스트 완료") 