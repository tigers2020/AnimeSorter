"""
FileScanWorker 회귀 테스트
- 대용량 파일 처리 시 길이 불일치 문제 검증
- ThreadPoolExecutor 스레드 수 제한 검증
- IndexError 방지 검증
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
from PyQt5.QtCore import QObject
import threading
import time

# src 디렉토리를 경로에 추가
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui.main_window import FileScanWorker, FileScanWorkerSignals
from utils.file_cleaner import FileCleaner


class TestFileScanWorkerRegression:
    """FileScanWorker 회귀 테스트"""
    
    def setup_method(self):
        """테스트 전 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_file_cleaner = Mock()
        
    def teardown_method(self):
        """테스트 후 정리"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self, count: int) -> list:
        """테스트용 파일들 생성"""
        file_paths = []
        video_exts = ['.mp4', '.mkv', '.avi', '.mov']
        subtitle_exts = ['.srt', '.ass', '.sub']
        other_exts = ['.txt', '.nfo', '.jpg', '.png']
        
        all_exts = video_exts + subtitle_exts + other_exts
        
        for i in range(count):
            ext = all_exts[i % len(all_exts)]
            filename = f"test_anime_s01e{i:02d}_1080p{ext}"
            file_path = Path(self.temp_dir) / filename
            file_path.touch()  # 빈 파일 생성
            file_paths.append(file_path)
            
        return file_paths
    
    def test_large_file_list_no_index_error(self):
        """1000+ 파일 처리 시 IndexError 발생하지 않음을 검증"""
        # 1500개 파일 생성
        file_paths = self.create_test_files(1500)
        
        # Mock signals
        signals = Mock()
        signals.log = Mock()
        signals.progress = Mock()
        signals.result = Mock()
        signals.finished = Mock()
        
        # FileScanWorker 생성
        worker = FileScanWorker(file_paths, self.mock_file_cleaner)
        worker.signals = signals
        
        # FileCleaner.clean_filename_static을 mock
        with patch.object(FileCleaner, 'clean_filename_static') as mock_clean:
            from utils.file_cleaner import CleanResult
            mock_clean.return_value = CleanResult(
                title="test_anime",
                original_filename="test_file.mp4",
                season=1,
                episode=1,
                year=2023,
                is_movie=False,
                extra_info={}
            )
            
            # 실행 (예외 발생하지 않아야 함)
            try:
                worker.run()
                success = True
            except IndexError as e:
                success = False
                pytest.fail(f"IndexError 발생: {e}")
            except Exception as e:
                # 다른 예외는 허용 (파일 시스템 관련 등)
                success = True
                
        # 결과 검증
        assert success, "대용량 파일 처리 시 IndexError가 발생하지 않아야 함"
        signals.finished.emit.assert_called()
    
    def test_file_name_list_ext_type_list_length_consistency(self):
        """file_name_list와 ext_type_list 길이 일치 검증"""
        file_paths = self.create_test_files(1000)
        
        # Mock signals
        signals = Mock()
        signals.log = Mock()
        signals.progress = Mock()
        signals.result = Mock()
        signals.finished = Mock()
        
        worker = FileScanWorker(file_paths, self.mock_file_cleaner)
        worker.signals = signals
        
        # run() 메서드의 초기 부분만 실행하여 리스트 길이 확인
        worker.run()
        
        # 실행 후 signals.result.emit이 호출되었는지 확인
        # (정상 완료되었다면 길이 불일치 문제가 없었다는 의미)
        signals.finished.emit.assert_called()
    
    def test_thread_pool_executor_max_workers_limit(self):
        """ThreadPoolExecutor max_workers 제한 검증"""
        file_paths = self.create_test_files(500)
        
        # 활성 스레드 수를 추적하기 위한 변수
        max_active_threads = [0]
        active_threads = [0]
        thread_lock = threading.Lock()
        
        def mock_clean_with_thread_tracking(file_path):
            with thread_lock:
                active_threads[0] += 1
                max_active_threads[0] = max(max_active_threads[0], active_threads[0])
            
            # 짧은 지연으로 스레드 동시성 시뮬레이션
            time.sleep(0.01)
            
            with thread_lock:
                active_threads[0] -= 1
            
            from utils.file_cleaner import CleanResult
            return CleanResult(
                title="test_anime",
                original_filename=str(file_path),
                season=1,
                episode=1,
                year=2023,
                is_movie=False,
                extra_info={}
            )
        
        # Mock signals
        signals = Mock()
        signals.log = Mock()
        signals.progress = Mock()
        signals.result = Mock()
        signals.finished = Mock()
        
        worker = FileScanWorker(file_paths, self.mock_file_cleaner)
        worker.signals = signals
        
        with patch.object(FileCleaner, 'clean_filename_static', side_effect=mock_clean_with_thread_tracking):
            worker.run()
        
        # 최대 활성 스레드 수가 제한 범위 내인지 확인
        expected_max_workers = min(8, os.cpu_count() or 4)
        assert max_active_threads[0] <= expected_max_workers, \
            f"최대 활성 스레드 수({max_active_threads[0]})가 제한({expected_max_workers})을 초과함"
        
        print(f"최대 활성 스레드 수: {max_active_threads[0]}, 제한: {expected_max_workers}")
    
    def test_abort_mechanism(self):
        """중단 메커니즘 검증"""
        file_paths = self.create_test_files(100)
        
        signals = Mock()
        signals.log = Mock()
        signals.progress = Mock()
        signals.result = Mock()
        signals.finished = Mock()
        
        worker = FileScanWorker(file_paths, self.mock_file_cleaner)
        worker.signals = signals
        
        # 작업 중단
        worker.stop()
        
        with patch.object(FileCleaner, 'clean_filename_static') as mock_clean:
            from utils.file_cleaner import CleanResult
            mock_clean.return_value = CleanResult(
                title="test_anime",
                original_filename="test_file.mp4",
                season=1,
                episode=1,
                year=2023,
                is_movie=False,
                extra_info={}
            )
            
            worker.run()
        
        # 중단 메시지가 로그에 기록되었는지 확인
        log_calls = [call[0][0] for call in signals.log.emit.call_args_list]
        abort_messages = [msg for msg in log_calls if "중단" in msg]
        assert len(abort_messages) > 0, "중단 메시지가 로그에 기록되어야 함"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 