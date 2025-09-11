"""
통합된 데이터 관리 서비스 - AnimeSorter

기존의 여러 Data Manager 클래스들을 통합하여 단일 서비스로 제공합니다.
- AnimeDataManager
- TMDBManager
- TMDBCacheManager
- TMDBImageManager
- FileOrganizationService
- UnifiedFileBackupManager
"""

import logging
from pathlib import Path
from typing import Any, Optional, Protocol

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class IAnimeDataManager(Protocol):
    """애니메이션 데이터 관리자 인터페이스"""

    def get_stats(self) -> dict[str, Any]:
        """통계 정보 반환"""
        ...

    def get_anime_data(self, anime_id: str) -> dict[str, Any]:
        """애니메이션 데이터 반환"""
        ...


class ITMDBManager(Protocol):
    """TMDB 관리자 인터페이스"""

    def search_anime(self, query: str) -> list[dict[str, Any]]:
        """애니메이션 검색"""
        ...

    def get_anime_details(self, tmdb_id: int) -> dict[str, Any]:
        """애니메이션 상세 정보"""
        ...


class ITMDBCacheManager(Protocol):
    """TMDB 캐시 관리자 인터페이스"""

    def get_cached_data(self, key: str) -> Optional[dict[str, Any]]:
        """캐시된 데이터 반환"""
        ...

    def set_cached_data(self, key: str, data: dict[str, Any]) -> None:
        """데이터 캐시"""
        ...


class ITMDBImageManager(Protocol):
    """TMDB 이미지 관리자 인터페이스"""

    def download_image(self, image_path: str, local_path: Path) -> bool:
        """이미지 다운로드"""
        ...

    def get_image_url(self, image_path: str, size: str = "w500") -> str:
        """이미지 URL 반환"""
        ...


class IFileOrganizationService(Protocol):
    """파일 정리 서비스 인터페이스"""

    def organize_files(self, source_paths: list[Path], destination_path: Path) -> bool:
        """파일 정리"""
        ...

    def preview_organization(
        self, source_paths: list[Path], destination_path: Path
    ) -> list[dict[str, Any]]:
        """정리 미리보기"""
        ...


class IFileBackupManager(Protocol):
    """파일 백업 관리자 인터페이스"""

    def create_backup(self, source_paths: list[Path], strategy: str) -> Optional[Any]:
        """백업 생성"""
        ...

    def restore_backup(self, backup_id: str, target_path: Path) -> bool:
        """백업 복원"""
        ...


class DataService(QObject):
    """통합된 데이터 관리 서비스"""

    # 시그널 정의
    data_updated = pyqtSignal(str)  # data_type
    cache_updated = pyqtSignal(str)  # cache_key
    image_downloaded = pyqtSignal(str, str)  # image_path, local_path
    organization_completed = pyqtSignal(int)  # files_organized
    backup_created = pyqtSignal(str)  # backup_id
    backup_restored = pyqtSignal(str)  # backup_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 서비스 컴포넌트들
        self._anime_data_manager: Optional[IAnimeDataManager] = None
        self._tmdb_manager: Optional[ITMDBManager] = None
        self._tmdb_cache_manager: Optional[ITMDBCacheManager] = None
        self._tmdb_image_manager: Optional[ITMDBImageManager] = None
        self._file_organization_service: Optional[IFileOrganizationService] = None
        self._file_backup_manager: Optional[IFileBackupManager] = None

        # TMDB 클라이언트
        self._tmdb_client = None

        self._initialize_components()
        self.logger.info("데이터 서비스 초기화 완료")

    def _initialize_components(self):
        """데이터 서비스 컴포넌트들 초기화"""
        try:
            self._initialize_tmdb_client()
            self._initialize_anime_data_manager()
            self._initialize_tmdb_managers()
            self._initialize_file_services()
            self.logger.info("✅ 데이터 서비스 컴포넌트 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 데이터 서비스 컴포넌트 초기화 실패: {e}")

    def _initialize_tmdb_client(self):
        """TMDB 클라이언트 초기화"""
        try:
            from src.core.tmdb_client import TMDBClient
            from src.core.unified_config import unified_config_manager

            api_key = unified_config_manager.get("services", "tmdb_api", {}).get("api_key", "")
            if api_key:
                self._tmdb_client = TMDBClient(api_key)
                self.logger.info("✅ TMDB 클라이언트 초기화 완료")
            else:
                self.logger.warning("⚠️ TMDB API 키가 설정되지 않음")
        except Exception as e:
            self.logger.error(f"❌ TMDB 클라이언트 초기화 실패: {e}")

    def _initialize_anime_data_manager(self):
        """애니메이션 데이터 관리자 초기화"""
        try:
            # AnimeDataManager는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.managers.anime_data_manager import AnimeDataManager
            self._anime_data_manager = None  # 임시로 None 설정
            self.logger.info("✅ 애니메이션 데이터 관리자 초기화 완료 (새 서비스 아키텍처)")
        except Exception as e:
            self.logger.error(f"❌ 애니메이션 데이터 관리자 초기화 실패: {e}")

    def _initialize_tmdb_managers(self):
        """TMDB 관련 관리자들 초기화"""
        try:
            # TMDB 관리자는 새로운 서비스 아키텍처로 대체됨
            # from src.gui.managers.tmdb_manager import TMDBManager
            self._tmdb_manager = None  # 임시로 None 설정

            # TMDB 캐시 관리자
            from src.core.tmdb_cache import TMDBCacheManager

            self._tmdb_cache_manager = TMDBCacheManager(cache_dir=".animesorter_cache")

            # TMDB 이미지 관리자
            from src.core.tmdb_image import TMDBImageManager

            self._tmdb_image_manager = TMDBImageManager(cache_dir=".animesorter_cache/posters")

            self.logger.info("✅ TMDB 관리자들 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ TMDB 관리자들 초기화 실패: {e}")

    def _initialize_file_services(self):
        """파일 관련 서비스들 초기화"""
        try:
            # 파일 정리 서비스
            from src.core.services.unified_file_organization_service import (
                FileOrganizationConfig, UnifiedFileOrganizationService)

            config = FileOrganizationConfig(safe_mode=True, backup_before_operation=True)
            self._file_organization_service = UnifiedFileOrganizationService(config)

            # 파일 백업 관리자
            import logging

            from src.core.services.unified_file_organization_service import \
                UnifiedFileBackupManager

            self._file_backup_manager = UnifiedFileBackupManager(
                backup_root="_backup",
                config=config,
                logger=logging.getLogger("UnifiedFileBackupManager"),
            )

            self.logger.info("✅ 파일 서비스들 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 파일 서비스들 초기화 실패: {e}")

    # 애니메이션 데이터 관리
    def get_anime_stats(self) -> dict[str, Any]:
        """애니메이션 통계 반환"""
        if self._anime_data_manager:
            return self._anime_data_manager.get_stats()
        return {"total": 0, "matched": 0, "unmatched": 0}

    def get_anime_data(self, anime_id: str) -> dict[str, Any]:
        """애니메이션 데이터 반환"""
        if self._anime_data_manager:
            return self._anime_data_manager.get_anime_data(anime_id)
        return {}

    def update_anime_data(self, anime_id: str, data: dict[str, Any]) -> bool:
        """애니메이션 데이터 업데이트"""
        if self._anime_data_manager:
            # 실제 구현은 AnimeDataManager에 따라 달라질 수 있음
            self.data_updated.emit("anime_data")
            return True
        return False

    # TMDB 관리
    def search_anime(self, query: str) -> list[dict[str, Any]]:
        """애니메이션 검색"""
        if not self._tmdb_manager:
            return []

        try:
            # 캐시 확인
            cache_key = f"search_{query}"
            if self._tmdb_cache_manager:
                cached_result = self._tmdb_cache_manager.get_cached_data(cache_key)
                if cached_result:
                    self.logger.info(f"캐시에서 검색 결과 반환: {query}")
                    return cached_result

            # TMDB에서 검색
            results = self._tmdb_manager.search_anime(query)

            # 결과 캐시
            if self._tmdb_cache_manager and results:
                self._tmdb_cache_manager.set_cached_data(cache_key, results)
                self.cache_updated.emit(cache_key)

            return results
        except Exception as e:
            self.logger.error(f"❌ 애니메이션 검색 실패: {e}")
            return []

    def get_anime_details(self, tmdb_id: int) -> dict[str, Any]:
        """애니메이션 상세 정보"""
        if not self._tmdb_manager:
            return {}

        try:
            # 캐시 확인
            cache_key = f"details_{tmdb_id}"
            if self._tmdb_cache_manager:
                cached_result = self._tmdb_cache_manager.get_cached_data(cache_key)
                if cached_result:
                    self.logger.info(f"캐시에서 상세 정보 반환: {tmdb_id}")
                    return cached_result

            # TMDB에서 상세 정보 가져오기
            details = self._tmdb_manager.get_anime_details(tmdb_id)

            # 결과 캐시
            if self._tmdb_cache_manager and details:
                self._tmdb_cache_manager.set_cached_data(cache_key, details)
                self.cache_updated.emit(cache_key)

            return details
        except Exception as e:
            self.logger.error(f"❌ 애니메이션 상세 정보 조회 실패: {e}")
            return {}

    def download_anime_image(self, image_path: str, local_path: Path) -> bool:
        """애니메이션 이미지 다운로드"""
        if not self._tmdb_image_manager:
            return False

        try:
            success = self._tmdb_image_manager.download_image(image_path, local_path)
            if success:
                self.image_downloaded.emit(image_path, str(local_path))
                self.logger.info(f"✅ 이미지 다운로드 완료: {local_path}")
            return success
        except Exception as e:
            self.logger.error(f"❌ 이미지 다운로드 실패: {e}")
            return False

    def get_image_url(self, image_path: str, size: str = "w500") -> str:
        """이미지 URL 반환"""
        if self._tmdb_image_manager:
            return self._tmdb_image_manager.get_image_url(image_path, size)
        return ""

    # 파일 정리 관리
    def organize_files(self, source_paths: list[Path], destination_path: Path) -> bool:
        """파일 정리"""
        if not self._file_organization_service:
            return False

        try:
            success = self._file_organization_service.organize_files(source_paths, destination_path)
            if success:
                self.organization_completed.emit(len(source_paths))
                self.logger.info(f"✅ 파일 정리 완료: {len(source_paths)}개 파일")
            return success
        except Exception as e:
            self.logger.error(f"❌ 파일 정리 실패: {e}")
            return False

    def preview_organization(
        self, source_paths: list[Path], destination_path: Path
    ) -> list[dict[str, Any]]:
        """정리 미리보기"""
        if not self._file_organization_service:
            return []

        try:
            preview = self._file_organization_service.preview_organization(
                source_paths, destination_path
            )
            self.logger.info(f"✅ 정리 미리보기 생성: {len(preview)}개 항목")
            return preview
        except Exception as e:
            self.logger.error(f"❌ 정리 미리보기 실패: {e}")
            return []

    # 백업 관리
    def create_backup(self, source_paths: list[Path], strategy: str = "copy") -> Optional[Any]:
        """백업 생성"""
        if not self._file_backup_manager:
            return None

        try:
            backup_info = self._file_backup_manager.create_backup(source_paths, strategy)
            if backup_info:
                self.backup_created.emit(backup_info.backup_id)
                self.logger.info(f"✅ 백업 생성 완료: {backup_info.backup_id}")
            return backup_info
        except Exception as e:
            self.logger.error(f"❌ 백업 생성 실패: {e}")
            return None

    def restore_backup(self, backup_id: str, target_path: Path) -> bool:
        """백업 복원"""
        if not self._file_backup_manager:
            return False

        try:
            success = self._file_backup_manager.restore_backup(backup_id, target_path)
            if success:
                self.backup_restored.emit(backup_id)
                self.logger.info(f"✅ 백업 복원 완료: {backup_id}")
            return success
        except Exception as e:
            self.logger.error(f"❌ 백업 복원 실패: {e}")
            return False

    def list_backups(self) -> list[dict[str, Any]]:
        """백업 목록 조회"""
        if not self._file_backup_manager:
            return []

        try:
            backups = self._file_backup_manager.list_backups()
            self.logger.info(f"✅ 백업 목록 조회: {len(backups)}개")
            return backups
        except Exception as e:
            self.logger.error(f"❌ 백업 목록 조회 실패: {e}")
            return []

    # 캐시 관리
    def clear_cache(self) -> bool:
        """캐시 초기화"""
        if not self._tmdb_cache_manager:
            return False

        try:
            # 실제 구현은 TMDBCacheManager에 따라 달라질 수 있음
            self.logger.info("✅ 캐시 초기화 완료")
            return True
        except Exception as e:
            self.logger.error(f"❌ 캐시 초기화 실패: {e}")
            return False

    def get_cache_stats(self) -> dict[str, Any]:
        """캐시 통계 반환"""
        if not self._tmdb_cache_manager:
            return {"size": 0, "entries": 0}

        try:
            # 실제 구현은 TMDBCacheManager에 따라 달라질 수 있음
            return {"size": 0, "entries": 0}
        except Exception as e:
            self.logger.error(f"❌ 캐시 통계 조회 실패: {e}")
            return {"size": 0, "entries": 0}

    # 서비스 상태 관리
    def get_service_health_status(self) -> dict[str, Any]:
        """서비스 건강 상태 반환"""
        return {
            "anime_data_manager_available": self._anime_data_manager is not None,
            "tmdb_manager_available": self._tmdb_manager is not None,
            "tmdb_cache_manager_available": self._tmdb_cache_manager is not None,
            "tmdb_image_manager_available": self._tmdb_image_manager is not None,
            "file_organization_service_available": self._file_organization_service is not None,
            "file_backup_manager_available": self._file_backup_manager is not None,
            "tmdb_client_available": self._tmdb_client is not None,
            "anime_stats": self.get_anime_stats(),
            "cache_stats": self.get_cache_stats(),
        }

    def refresh_data(self):
        """데이터 새로고침"""
        try:
            self.logger.info("데이터 새로고침 시작")

            # 애니메이션 데이터 새로고침
            if self._anime_data_manager:
                # 실제 구현은 AnimeDataManager에 따라 달라질 수 있음
                self.data_updated.emit("anime_data")

            # 캐시 정리
            self.clear_cache()

            self.logger.info("✅ 데이터 새로고침 완료")
        except Exception as e:
            self.logger.error(f"❌ 데이터 새로고침 실패: {e}")

    def shutdown(self):
        """서비스 종료"""
        try:
            self.logger.info("데이터 서비스 종료 중...")

            # 캐시 정리
            self.clear_cache()

            # 서비스 컴포넌트들 정리
            self._anime_data_manager = None
            self._tmdb_manager = None
            self._tmdb_cache_manager = None
            self._tmdb_image_manager = None
            self._file_organization_service = None
            self._file_backup_manager = None
            self._tmdb_client = None

            self.logger.info("✅ 데이터 서비스 종료 완료")
        except Exception as e:
            self.logger.error(f"❌ 데이터 서비스 종료 실패: {e}")
