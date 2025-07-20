#!/usr/bin/env python3
"""
AnimeSorter - 애니메이션 파일 정리 도구 (스트리밍 파이프라인 지원)
"""

import sys
import asyncio
import argparse
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
        from src.core.cache_db import CacheDB
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

async def run_streaming_pipeline(source_dir: Path, target_dir: Path, config: dict):
    """
    스트리밍 파이프라인 실행
    
    Args:
        source_dir: 소스 디렉토리
        target_dir: 대상 디렉토리
        config: 설정 딕셔너리
    """
    try:
        print(f"스트리밍 파이프라인 시작: {source_dir} -> {target_dir}")
        
        # 스트리밍 파이프라인 컴포넌트 초기화
        from src.core.streaming_pipeline import StreamingPipeline
        from src.core.file_cleaner import StreamingFileCleaner
        from src.core.metadata_provider import StreamingMetadataProvider
        from src.core.path_planner import PathPlanner
        from src.core.file_manager import FileManager
        from src.core.event_queue import AsyncEventQueue
        
        # 이벤트 큐 초기화
        event_queue = AsyncEventQueue()
        
        # 파일 정제기 초기화
        file_cleaner = StreamingFileCleaner()
        
        # 메타데이터 제공자 초기화
        from src.plugin.tmdb.provider import TMDBProvider
        tmdb_provider = TMDBProvider(
            api_key=config.get('tmdb_api_key'),
            cache_db=config.get('cache_db')
        )
        metadata_provider = StreamingMetadataProvider(
            tmdb_provider=tmdb_provider,
            cache_db=config.get('cache_db')
        )
        await metadata_provider.initialize()
        
        # 경로 계획자 초기화
        path_planner = PathPlanner(
            folder_template=config.get('folder_template', '{title} ({year})'),
            keep_original_name=config.get('keep_original_name', True),
            overwrite_existing=config.get('overwrite_existing', False)
        )
        
        # 파일 관리자 초기화
        file_manager = FileManager(
            source_dir=source_dir,
            target_dir=target_dir,
            overwrite_existing=config.get('overwrite_existing', False)
        )
        
        # 스트리밍 파이프라인 초기화
        pipeline = StreamingPipeline(
            file_cleaner=file_cleaner,
            metadata_provider=metadata_provider,
            path_planner=path_planner,
            file_manager=file_manager,
            event_queue=event_queue,
            max_concurrent_files=config.get('max_concurrent_files', 3)
        )
        
        # 파이프라인 실행
        await pipeline.run(source_dir)
        
        print("스트리밍 파이프라인 완료")
        
    except Exception as e:
        print(f"스트리밍 파이프라인 오류: {e}")
        import traceback
        traceback.print_exc()
        raise

def run_cli_mode(args):
    """CLI 모드 실행"""
    try:
        # 설정 준비
        config = {
            'tmdb_api_key': args.api_key,
            'folder_template': args.folder_template,
            'keep_original_name': not args.rename,
            'overwrite_existing': args.overwrite,
            'max_concurrent_files': args.max_concurrent
        }
        
        # 애플리케이션 초기화
        logger_manager, exception_handler, cache_db, key_manager = initialize_application()
        config['cache_db'] = cache_db
        
        # 스트리밍 파이프라인 실행
        asyncio.run(run_streaming_pipeline(
            source_dir=Path(args.source),
            target_dir=Path(args.target),
            config=config
        ))
        
    except Exception as e:
        print(f"CLI 모드 오류: {e}")
        sys.exit(1)

def run_gui_mode():
    """GUI 모드 실행"""
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

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="AnimeSorter - 애니메이션 파일 정리 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # GUI 모드 실행
  python main.py
  
  # CLI 모드 실행
  python main.py --source /path/to/source --target /path/to/target --api-key YOUR_TMDB_API_KEY
  
  # CLI 모드 (고급 옵션)
  python main.py --source /path/to/source --target /path/to/target \\
    --api-key YOUR_TMDB_API_KEY \\
    --folder-template "{title} ({year})" \\
    --rename \\
    --overwrite \\
    --max-concurrent 5
        """
    )
    
    # CLI 모드 옵션
    parser.add_argument('--source', type=str, help='소스 디렉토리 경로')
    parser.add_argument('--target', type=str, help='대상 디렉토리 경로')
    parser.add_argument('--api-key', type=str, help='TMDB API 키')
    parser.add_argument('--folder-template', type=str, 
                       default='{title} ({year})',
                       help='폴더 이름 템플릿 (기본값: {title} ({year}))')
    parser.add_argument('--rename', action='store_true',
                       help='파일명을 메타데이터 기반으로 변경')
    parser.add_argument('--overwrite', action='store_true',
                       help='기존 파일 덮어쓰기')
    parser.add_argument('--max-concurrent', type=int, default=3,
                       help='동시 처리할 파일 수 (기본값: 3)')
    
    args = parser.parse_args()
    
    # CLI 모드인지 확인
    if args.source and args.target:
        if not args.api_key:
            print("오류: CLI 모드에서는 --api-key가 필요합니다.")
            sys.exit(1)
        run_cli_mode(args)
    else:
        # GUI 모드 실행
        run_gui_mode()

if __name__ == "__main__":
    main() 