import yaml

print("Config 테스트 시작")

try:
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    print("설정 로드 성공")
    print(f"API 키: {config.get('api_key')}")
    print(f"소스 디렉토리: {config.get('source_dir')}")
    print(f"대상 디렉토리: {config.get('target_dir')}")
except Exception as e:
    print(f"오류 발생: {e}")
    
print("테스트 완료") 