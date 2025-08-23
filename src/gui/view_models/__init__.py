"""
ViewModel 패키지 - Phase 3 뷰모델 분할 완료
각 기능별로 분리된 ViewModel들을 제공합니다.
"""

# 기존 단일 파일 ViewModel들 (적정 크기)
from .detail_view_model import DetailViewModel
from .file_list_view_model import FileListViewModel

# 새로운 분할된 ViewModel들 (테스트를 위해 문제가 있는 것들은 임시로 제외)
from .main_window import MainWindowViewModel

# TODO: import 문제 해결 후 활성화
# from .organize import OrganizeViewModel
# from .settings import SettingsViewModel
# from .metadata import MetadataViewModel
# from .scan import ScanViewModel

__all__ = [
    # 기존 ViewModel들 (적정 크기)
    "FileListViewModel",
    "DetailViewModel",
    # 새로운 분할된 ViewModel들
    "MainWindowViewModel",
    # TODO: import 문제 해결 후 활성화
    # "OrganizeViewModel",
    # "SettingsViewModel",
    # "MetadataViewModel",
    # "ScanViewModel",
]
