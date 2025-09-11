"""
애플리케이션 파사드 - AnimeSorter

복잡한 Manager 클래스들의 상호작용을 단순화하는 파사드 패턴을 구현합니다.
모든 서비스들을 통합하여 단일 진입점을 제공합니다.
"""

import logging
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMainWindow

from src.app.services.command_service import CommandService
from src.app.services.configuration_service import ConfigurationService
from src.app.services.data_service import DataService
from src.app.services.safety_service import SafetyConfiguration, SafetyService
from src.app.services.ui_service import UIService

logger = logging.getLogger(__name__)


class ApplicationFacade(QObject):
    """애플리케이션 파사드 - 모든 서비스들의 통합 인터페이스"""

    # 시그널 정의
    application_initialized = pyqtSignal()
    application_shutdown = pyqtSignal()
    service_error = pyqtSignal(str, str)  # service_name, error_message

    def __init__(self, main_window: QMainWindow, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 서비스들
        self._safety_service: Optional[SafetyService] = None
        self._ui_service: Optional[UIService] = None
        self._command_service: Optional[CommandService] = None
        self._data_service: Optional[DataService] = None
        self._configuration_service: Optional[ConfigurationService] = None

        # 초기화 상태
        self._initialized = False
        self._initialization_errors = []

        self.logger.info("애플리케이션 파사드 초기화 시작")

    def initialize_application(self) -> bool:
        """애플리케이션 초기화"""
        try:
            self.logger.info("애플리케이션 초기화 시작")

            # 서비스들 초기화
            self._initialize_services()

            # 서비스들 간 연결 설정
            self._setup_service_connections()

            # 설정 적용
            self._apply_initial_configuration()

            self._initialized = True
            self.application_initialized.emit()
            self.logger.info("✅ 애플리케이션 초기화 완료")
            return True

        except Exception as e:
            self.logger.error(f"❌ 애플리케이션 초기화 실패: {e}")
            self._initialization_errors.append(str(e))
            return False

    def _initialize_services(self):
        """서비스들 초기화"""
        try:
            # 설정 서비스 초기화 (다른 서비스들보다 먼저)
            self._configuration_service = ConfigurationService(self)
            self.logger.info("✅ 설정 서비스 초기화 완료")

            # UI 서비스 초기화
            self._ui_service = UIService(self.main_window, self)
            self.logger.info("✅ UI 서비스 초기화 완료")

            # 데이터 서비스 초기화
            self._data_service = DataService(self)
            self.logger.info("✅ 데이터 서비스 초기화 완료")

            # 안전 서비스 초기화
            safety_config = SafetyConfiguration()
            self._safety_service = SafetyService(safety_config, self)
            self.logger.info("✅ 안전 서비스 초기화 완료")

            # 명령 서비스 초기화
            self._command_service = CommandService(self.main_window, self)
            self.logger.info("✅ 명령 서비스 초기화 완료")

        except Exception as e:
            self.logger.error(f"❌ 서비스 초기화 실패: {e}")
            raise

    def _setup_service_connections(self):
        """서비스들 간 연결 설정"""
        try:
            # UI 서비스와 안전 서비스 연결
            if self._ui_service and self._safety_service:
                self._ui_service.safety_mode_changed.connect(
                    lambda mode: self._safety_service.change_safety_mode(mode)
                )

            # 명령 서비스와 안전 서비스 연결
            if self._command_service and self._safety_service:
                # 안전한 명령 실행을 위해 연결
                pass

            # 데이터 서비스와 UI 서비스 연결
            if self._data_service and self._ui_service:
                self._data_service.data_updated.connect(
                    lambda data_type: self._ui_service.update_status_bar(
                        f"데이터 업데이트: {data_type}"
                    )
                )

            self.logger.info("✅ 서비스 간 연결 설정 완료")
        except Exception as e:
            self.logger.error(f"❌ 서비스 간 연결 설정 실패: {e}")

    def _apply_initial_configuration(self):
        """초기 설정 적용"""
        try:
            if self._configuration_service:
                # 설정 검증
                errors = self._configuration_service.validate_configuration()
                if errors:
                    self.logger.warning(f"설정 검증 오류 발견: {errors}")
                    self._configuration_service.fix_configuration_errors(errors)

                # UI에 설정 적용
                if self._ui_service:
                    self._ui_service.apply_settings_to_ui()

            self.logger.info("✅ 초기 설정 적용 완료")
        except Exception as e:
            self.logger.error(f"❌ 초기 설정 적용 실패: {e}")

    # 안전 서비스 인터페이스
    def get_safety_status(self) -> dict[str, Any]:
        """안전 상태 조회"""
        if self._safety_service:
            return self._safety_service.get_safety_status().__dict__
        return {}

    def change_safety_mode(self, mode: str) -> bool:
        """안전 모드 변경"""
        if self._safety_service:
            return self._safety_service.change_safety_mode(mode)
        return False

    def create_backup(self, source_paths: list[str]) -> Optional[Any]:
        """백업 생성"""
        if self._safety_service:
            from pathlib import Path

            paths = [Path(p) for p in source_paths]
            return self._safety_service.create_backup(paths)
        return None

    def restore_backup(self, backup_id: str, target_path: str) -> bool:
        """백업 복원"""
        if self._safety_service:
            from pathlib import Path

            return self._safety_service.restore_backup(backup_id, Path(target_path))
        return False

    # UI 서비스 인터페이스
    def apply_theme(self, theme: str) -> bool:
        """테마 적용"""
        if self._ui_service:
            return self._ui_service.apply_theme(theme)
        return False

    def set_language(self, language: str) -> bool:
        """언어 설정"""
        if self._ui_service:
            return self._ui_service.set_language(language)
        return False

    def update_status_bar(self, message: str, progress: int = None):
        """상태바 업데이트"""
        if self._ui_service:
            self._ui_service.update_status_bar(message, progress)

    def show_error_message(self, message: str, details: str = ""):
        """오류 메시지 표시"""
        if self._ui_service:
            self._ui_service.show_error_message(message, details)

    def show_success_message(self, message: str, details: str = ""):
        """성공 메시지 표시"""
        if self._ui_service:
            self._ui_service.show_success_message(message, details)

    # 명령 서비스 인터페이스
    def execute_command(self, command, show_progress: bool = True) -> bool:
        """명령 실행"""
        if self._command_service:
            return self._command_service.execute_command(command, show_progress)
        return False

    def undo_last_operation(self) -> bool:
        """마지막 작업 실행 취소"""
        if self._command_service:
            return self._command_service.undo_last_operation()
        return False

    def redo_last_operation(self) -> bool:
        """마지막 작업 재실행"""
        if self._command_service:
            return self._command_service.redo_last_operation()
        return False

    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        if self._command_service:
            return self._command_service.can_undo()
        return False

    def can_redo(self) -> bool:
        """재실행 가능 여부"""
        if self._command_service:
            return self._command_service.can_redo()
        return False

    # 데이터 서비스 인터페이스
    def search_anime(self, query: str) -> list[dict[str, Any]]:
        """애니메이션 검색"""
        if self._data_service:
            return self._data_service.search_anime(query)
        return []

    def get_anime_details(self, tmdb_id: int) -> dict[str, Any]:
        """애니메이션 상세 정보"""
        if self._data_service:
            return self._data_service.get_anime_details(tmdb_id)
        return {}

    def organize_files(self, source_paths: list[str], destination_path: str) -> bool:
        """파일 정리"""
        if self._data_service:
            from pathlib import Path

            source_paths_obj = [Path(p) for p in source_paths]
            destination_path_obj = Path(destination_path)
            return self._data_service.organize_files(source_paths_obj, destination_path_obj)
        return False

    def preview_organization(
        self, source_paths: list[str], destination_path: str
    ) -> list[dict[str, Any]]:
        """정리 미리보기"""
        if self._data_service:
            from pathlib import Path

            source_paths_obj = [Path(p) for p in source_paths]
            destination_path_obj = Path(destination_path)
            return self._data_service.preview_organization(source_paths_obj, destination_path_obj)
        return []

    # 설정 서비스 인터페이스
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """설정 값 조회"""
        if self._configuration_service:
            return self._configuration_service.get_config(section, key, default)
        return default

    def set_config(self, section: str, key: str, value: Any) -> bool:
        """설정 값 저장"""
        if self._configuration_service:
            return self._configuration_service.set_config(section, key, value)
        return False

    def save_configuration(self) -> bool:
        """설정 저장"""
        if self._configuration_service:
            return self._configuration_service.save_configuration()
        return False

    def load_configuration(self) -> bool:
        """설정 로드"""
        if self._configuration_service:
            return self._configuration_service.load_configuration()
        return False

    # 통합 기능
    def safe_organize_files(self, source_paths: list[str], destination_path: str) -> bool:
        """안전한 파일 정리 (안전 서비스와 데이터 서비스 통합)"""
        try:
            from pathlib import Path

            source_paths_obj = [Path(p) for p in source_paths]
            destination_path_obj = Path(destination_path)

            # 안전 서비스를 통한 안전한 작업 실행
            if self._safety_service:

                def organize_operation():
                    if self._data_service:
                        return self._data_service.organize_files(
                            source_paths_obj, destination_path_obj
                        )
                    return False

                return self._safety_service.request_safe_operation(
                    "file_organization", source_paths_obj, organize_operation
                )
            else:
                # 안전 서비스가 없으면 직접 실행
                if self._data_service:
                    return self._data_service.organize_files(source_paths_obj, destination_path_obj)
                return False
        except Exception as e:
            self.logger.error(f"❌ 안전한 파일 정리 실패: {e}")
            return False

    def refresh_application(self):
        """애플리케이션 새로고침"""
        try:
            self.logger.info("애플리케이션 새로고침 시작")

            # UI 새로고침
            if self._ui_service:
                self._ui_service.refresh_ui()

            # 데이터 새로고침
            if self._data_service:
                self._data_service.refresh_data()

            # 설정 다시 로드
            if self._configuration_service:
                self._configuration_service.load_configuration()

            self.logger.info("✅ 애플리케이션 새로고침 완료")
        except Exception as e:
            self.logger.error(f"❌ 애플리케이션 새로고침 실패: {e}")

    def reset_application_to_defaults(self):
        """애플리케이션을 기본값으로 초기화"""
        try:
            self.logger.info("애플리케이션 기본값 초기화 시작")

            # 설정 초기화
            if self._configuration_service:
                self._configuration_service.reset_to_defaults()

            # UI 초기화
            if self._ui_service:
                self._ui_service.reset_ui_to_defaults()

            # 안전 서비스 초기화
            if self._safety_service:
                self._safety_service.reset_safety_score()

            self.logger.info("✅ 애플리케이션 기본값 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 애플리케이션 기본값 초기화 실패: {e}")

    # 서비스 상태 관리
    def get_application_health_status(self) -> dict[str, Any]:
        """애플리케이션 건강 상태 반환"""
        health_status = {
            "initialized": self._initialized,
            "initialization_errors": self._initialization_errors,
            "services": {},
        }

        if self._safety_service:
            health_status["services"]["safety"] = self._safety_service.get_service_health_status()

        if self._ui_service:
            health_status["services"]["ui"] = self._ui_service.get_ui_health_status()

        if self._command_service:
            health_status["services"]["command"] = self._command_service.get_service_health_status()

        if self._data_service:
            health_status["services"]["data"] = self._data_service.get_service_health_status()

        if self._configuration_service:
            health_status["services"][
                "configuration"
            ] = self._configuration_service.get_service_health_status()

        return health_status

    def get_service_statistics(self) -> dict[str, Any]:
        """서비스 통계 반환"""
        stats = {"total_services": 5, "initialized_services": 0, "service_details": {}}

        services = [
            ("safety", self._safety_service),
            ("ui", self._ui_service),
            ("command", self._command_service),
            ("data", self._data_service),
            ("configuration", self._configuration_service),
        ]

        for service_name, service in services:
            if service:
                stats["initialized_services"] += 1
                if hasattr(service, "get_service_health_status"):
                    stats["service_details"][service_name] = service.get_service_health_status()
                elif hasattr(service, "get_ui_health_status"):
                    stats["service_details"][service_name] = service.get_ui_health_status()

        return stats

    def shutdown_application(self):
        """애플리케이션 종료"""
        try:
            self.logger.info("애플리케이션 종료 시작")

            # 서비스들 종료
            if self._command_service:
                self._command_service.shutdown()

            if self._data_service:
                self._data_service.shutdown()

            if self._ui_service:
                self._ui_service.shutdown_ui()

            if self._configuration_service:
                self._configuration_service.shutdown()

            if self._safety_service:
                # SafetyService는 QObject이므로 자동으로 정리됨
                pass

            self._initialized = False
            self.application_shutdown.emit()
            self.logger.info("✅ 애플리케이션 종료 완료")
        except Exception as e:
            self.logger.error(f"❌ 애플리케이션 종료 실패: {e}")

    # 서비스 직접 접근 (고급 사용자용)
    @property
    def safety_service(self) -> Optional[SafetyService]:
        """안전 서비스 직접 접근"""
        return self._safety_service

    @property
    def ui_service(self) -> Optional[UIService]:
        """UI 서비스 직접 접근"""
        return self._ui_service

    @property
    def command_service(self) -> Optional[CommandService]:
        """명령 서비스 직접 접근"""
        return self._command_service

    @property
    def data_service(self) -> Optional[DataService]:
        """데이터 서비스 직접 접근"""
        return self._data_service

    @property
    def configuration_service(self) -> Optional[ConfigurationService]:
        """설정 서비스 직접 접근"""
        return self._configuration_service

    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._initialized

    def get_initialization_errors(self) -> list[str]:
        """초기화 오류 목록"""
        return self._initialization_errors.copy()
