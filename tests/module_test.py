print("모듈 테스트 시작")

try:
    print("Config 모듈 로드 중...")
    from src.config import Config
    print("Config 모듈 로드 성공")
    
    print("Logger 모듈 로드 중...")
    from src.logger import setup_logger
    print("Logger 모듈 로드 성공")
    
    print("File Manager 모듈 로드 중...")
    from src.file_manager import FileManager
    print("File Manager 모듈 로드 성공")
    
    print("Cache DB 모듈 로드 중...")
    from src.cache_db import CacheDB
    print("Cache DB 모듈 로드 성공")
    
    print("TMDB Provider 모듈 로드 중...")
    from src.plugin.tmdb.provider import TMDBProvider
    print("TMDB Provider 모듈 로드 성공")
    
except Exception as e:
    print(f"모듈 로드 오류 발생: {e}")
    
print("테스트 완료") 