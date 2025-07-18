#!/usr/bin/env python3
"""
AnimeSorter - 애니메이션 파일 정리 도구
"""

import sys
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

# --- src 경로를 sys.path에 추가 (import 오류 방지) ---
sys.path.insert(0, str(Path(__file__).parent / "src"))

def initialize_application():
    """애플리케이션 초기화"""
    try:
        print("로깅 시스템 초기화 중...")
        # 로깅 시스템 초기화
        from src.utils.logger import initialize_logging
        logger_manager = initialize_logging(
            log_dir="logs",
            log_level="INFO"
        )
        print("로깅 시스템 초기화 완료")
        
        print("전역 예외 핸들러 설정 중...")
        # 전역 예외 핸들러 설정
        from src.utils.exception_handler import GlobalExceptionHandler
        exception_handler = GlobalExceptionHandler()
        exception_handler.install()
        print("전역 예외 핸들러 설정 완료")
        
        print("캐시 시스템 초기화 중...")
        # 캐시 시스템 초기화
        from src.cache.cache_db import CacheDB
        cache_db = CacheDB("cache/animesorter_cache.db")
        print("캐시 시스템 초기화 완료")
        
        print("API 키 관리자 초기화 중...")
        # API 키 관리자 초기화
        from src.security.key_manager import KeyManager
        key_manager = KeyManager("config")
        print("API 키 관리자 초기화 완료")
        
        return logger_manager, exception_handler, cache_db, key_manager
        
    except Exception as e:
        print(f"초기화 오류: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(
            None, 
            "초기화 오류", 
            f"애플리케이션 초기화 중 오류가 발생했습니다:\n{str(e)}"
        )
        sys.exit(1)

def main():
    """메인 함수"""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("AnimeSorter")
        app.setApplicationVersion("1.0.0")
        
        # 애플리케이션 초기화
        logger_manager, exception_handler, cache_db, key_manager = initialize_application()
        
        # 메인 윈도우 생성
        from src.ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        
        # 애플리케이션 실행
        exit_code = app.exec()
        
        # 정리 작업
        try:
            asyncio.run(cache_db.close())
        except:
            pass
            
        sys.exit(exit_code)
        
    except Exception as e:
        QMessageBox.critical(
            None, 
            "치명적 오류", 
            f"애플리케이션 실행 중 치명적 오류가 발생했습니다:\n{str(e)}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main() 