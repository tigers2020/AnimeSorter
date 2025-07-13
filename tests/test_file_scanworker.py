import pytest
from src.ui.main_window import FileScanWorker
from src.utils.file_cleaner import FileCleaner
from types import SimpleNamespace
import threading

class DummySignals:
    def __init__(self):
        self.progress = lambda *a, **k: None
        self.log = lambda *a, **k: None
        self.result = lambda *a, **k: None
        self.finished = lambda *a, **k: None

@pytest.mark.timeout(30)
def test_file_scanworker_large(monkeypatch):
    # 1000개 더미 파일명 생성
    file_paths = [f"/dummy/path/file_{i}.mkv" for i in range(1000)]
    export_dir = "."
    file_cleaner = FileCleaner(None)
    config = None
    worker = FileScanWorker(file_paths, export_dir, file_cleaner, config)
    worker.signals = DummySignals()
    # 실제 run() 호출 (스레드 안전성, IndexError 등 검증)
    # monkeypatch FileCleaner.clean_filename_static to avoid real parsing
    monkeypatch.setattr(FileCleaner, "clean_filename_static", lambda x: SimpleNamespace(title="dummy", original_filename=x, season=1, episode=1, year=2020, is_movie=False, extra_info={}))
    # run in main thread for test
    worker.run()
    # 내부 리스트 길이 불일치/IndexError 발생 시 pytest가 실패 처리 