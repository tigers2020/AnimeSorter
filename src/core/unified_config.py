"""
통합 설정 관리 시스템 - AnimeSorter

기존의 여러 설정 파일들을 통합하여 관리하는 시스템입니다.
- opencode.json: MCP 서버 설정
- animesorter_config.json: 애플리케이션 설정
"""

import json
import logging
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal


def get_config_directory() -> Path:
    """설정 디렉토리 경로를 반환합니다 (PyInstaller 환경 고려)"""
    if getattr(sys, "frozen", False):
        # PyInstaller로 빌드된 실행 파일인 경우
        base_path = Path(sys.executable).parent
        return base_path / "config"
    else:
        # 개발 환경인 경우
        return Path(__file__).parent.parent.parent / "data" / "config"


logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """외부 서비스 설정"""

    mcp_server: dict[str, Any] = field(default_factory=dict)
    tmdb_api: dict[str, Any] = field(default_factory=dict)
    api_keys: dict[str, str] = field(default_factory=dict)


@dataclass
class ApplicationSettings:
    """애플리케이션 핵심 설정"""

    file_organization: dict[str, Any] = field(default_factory=dict)
    backup_settings: dict[str, Any] = field(default_factory=dict)
    logging_config: dict[str, Any] = field(default_factory=dict)
    performance_settings: dict[str, Any] = field(default_factory=dict)

    @property
    def destination_root(self) -> str:
        return self.file_organization.get("destination_root", "")

    @destination_root.setter
    def destination_root(self, value: str):
        self.file_organization["destination_root"] = value

    @property
    def organize_mode(self) -> str:
        return self.file_organization.get("organize_mode", "복사")

    @organize_mode.setter
    def organize_mode(self, value: str):
        self.file_organization["organize_mode"] = value

    @property
    def naming_scheme(self) -> str:
        return self.file_organization.get("naming_scheme", "standard")

    @naming_scheme.setter
    def naming_scheme(self, value: str):
        self.file_organization["naming_scheme"] = value

    @property
    def safe_mode(self) -> bool:
        return self.file_organization.get("safe_mode", True)

    @safe_mode.setter
    def safe_mode(self, value: bool):
        self.file_organization["safe_mode"] = value

    @property
    def backup_before_organize(self) -> bool:
        return self.file_organization.get("backup_before_organize", False)

    @backup_before_organize.setter
    def backup_before_organize(self, value: bool):
        self.file_organization["backup_before_organize"] = value

    @property
    def prefer_anitopy(self) -> bool:
        return self.file_organization.get("prefer_anitopy", False)

    @prefer_anitopy.setter
    def prefer_anitopy(self, value: bool):
        self.file_organization["prefer_anitopy"] = value

    @property
    def fallback_parser(self) -> str:
        return self.file_organization.get("fallback_parser", "FileParser")

    @fallback_parser.setter
    def fallback_parser(self, value: str):
        self.file_organization["fallback_parser"] = value

    @property
    def log_level(self) -> str:
        return self.logging_config.get("log_level", "INFO")

    @log_level.setter
    def log_level(self, value: str):
        self.logging_config["log_level"] = value

    @property
    def log_to_file(self) -> bool:
        return self.logging_config.get("log_to_file", False)

    @log_to_file.setter
    def log_to_file(self, value: bool):
        self.logging_config["log_to_file"] = value

    @property
    def backup_location(self) -> str:
        return self.backup_settings.get("backup_location", "")

    @backup_location.setter
    def backup_location(self, value: str):
        self.backup_settings["backup_location"] = value

    @property
    def max_backup_count(self) -> int:
        return self.backup_settings.get("max_backup_count", 10)

    @max_backup_count.setter
    def max_backup_count(self, value: int):
        self.backup_settings["max_backup_count"] = value


@dataclass
class UserPreferences:
    """사용자 개인 설정"""

    gui_state: dict[str, Any] = field(default_factory=dict)
    accessibility: dict[str, Any] = field(default_factory=dict)
    theme_preferences: dict[str, Any] = field(default_factory=dict)
    language_settings: dict[str, Any] = field(default_factory=dict)

    @property
    def theme(self) -> str:
        return self.theme_preferences.get("theme", "light")

    @theme.setter
    def theme(self, value: str):
        self.theme_preferences["theme"] = value

    @property
    def language(self) -> str:
        return self.theme_preferences.get("language", "ko")

    @language.setter
    def language(self, value: str):
        self.theme_preferences["language"] = value

    @property
    def font_family(self) -> str:
        return getattr(self, "_font_family", "Segoe UI")

    @font_family.setter
    def font_family(self, value: str):
        self._font_family = value

    @property
    def font_size(self) -> int:
        return getattr(self, "_font_size", 9)

    @font_size.setter
    def font_size(self, value: int):
        self._font_size = value

    @property
    def ui_style(self) -> str:
        return getattr(self, "_ui_style", "default")

    @ui_style.setter
    def ui_style(self, value: str):
        self._ui_style = value

    @property
    def last_source_directory(self) -> str:
        return self.gui_state.get("last_source_directory", "")

    @last_source_directory.setter
    def last_source_directory(self, value: str):
        self.gui_state["last_source_directory"] = value

    @property
    def last_destination_directory(self) -> str:
        return self.gui_state.get("last_destination_directory", "")

    @last_destination_directory.setter
    def last_destination_directory(self, value: str):
        self.gui_state["last_destination_directory"] = value

    @property
    def window_geometry(self) -> Any:
        return self.gui_state.get("window_geometry", None)

    @window_geometry.setter
    def window_geometry(self, value: Any):
        self.gui_state["window_geometry"] = value

    @property
    def remember_last_session(self) -> bool:
        return self.gui_state.get("remember_last_session", True)

    @remember_last_session.setter
    def remember_last_session(self, value: bool):
        self.gui_state["remember_last_session"] = value


@dataclass
class UnifiedConfig:
    """통합 설정 스키마"""

    version: str = "1.0.0"
    services: ServiceConfig = field(default_factory=ServiceConfig)
    application: ApplicationSettings = field(default_factory=ApplicationSettings)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    metadata: dict[str, Any] = field(default_factory=dict)


class UnifiedConfigManager(QObject):
    """통합 설정 관리자"""

    config_changed = pyqtSignal(str, object)
    config_loaded = pyqtSignal()
    config_saved = pyqtSignal()
    config_save_failed = pyqtSignal(str)  # 저장 실패 시그널 (오류 메시지)

    def __init__(self, config_dir: Path | None = None):
        super().__init__()
        if config_dir:
            self.config_dir = config_dir
        else:
            # PyInstaller 환경에서 안전하게 작동하도록 수정
            self.config_dir = get_config_directory()

        # 디렉토리 생성 (부모 디렉토리도 함께 생성)
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # 디렉토리 쓰기 권한 확인
            test_file = self.config_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            logger.info(f"설정 디렉토리 권한 확인 완료: {self.config_dir.absolute()}")
        except (PermissionError, OSError) as e:
            logger.error(f"설정 디렉토리 생성/쓰기 권한 오류: {e}")
            logger.error(f"원본 경로: {self.config_dir.absolute()}")
            # 대안 경로 사용 (사용자 홈 디렉토리)
            home_dir = Path.home()
            self.config_dir = home_dir / "AnimeSorter" / "config"
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
                # 대안 경로도 권한 확인
                test_file = self.config_dir / ".test_write"
                test_file.write_text("test")
                test_file.unlink()
                logger.info(f"대안 설정 디렉토리 사용: {self.config_dir.absolute()}")
            except (PermissionError, OSError) as alt_e:
                logger.error(f"대안 설정 디렉토리도 실패: {alt_e}")
                # 최후의 수단: 임시 디렉토리 사용
                import tempfile

                temp_dir = Path(tempfile.gettempdir()) / "AnimeSorter" / "config"
                temp_dir.mkdir(parents=True, exist_ok=True)
                self.config_dir = temp_dir
                logger.warning(f"임시 디렉토리 사용: {self.config_dir.absolute()}")

        self.config = UnifiedConfig()
        self.config_file = self.config_dir / "unified_config.json"
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._change_callbacks: list[Callable] = []

        # 설정 파일 경로 로그 출력
        logger.info(f"설정 파일 경로: {self.config_file.absolute()}")
        logger.info(f"설정 디렉토리: {self.config_dir.absolute()}")
        logger.info(f"PyInstaller 환경: {getattr(sys, 'frozen', False)}")
        if getattr(sys, "frozen", False):
            logger.info(f"실행 파일 경로: {sys.executable}")

        self.load_config()

    def add_change_callback(self, callback: Callable):
        """설정 변경 콜백 등록"""
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable):
        """설정 변경 콜백 제거"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def _notify_change_callbacks(self, section: str, new_value: Any):
        """변경 콜백 호출"""
        for callback in self._change_callbacks:
            try:
                callback(section, new_value)
            except Exception as e:
                logger.error(f"Error in config change callback: {e}")

    def load_config(self) -> bool:
        """통합 설정 파일 로드"""
        try:
            logger.info(f"설정 파일 로드 시도: {self.config_file.absolute()}")
            if self.config_file.exists():
                with self.config_file.open(encoding="utf-8") as f:
                    data = json.load(f)
                    self._load_from_dict(data)
                    logger.info("통합 설정 파일 로드 완료")
                    self.config_loaded.emit()
                    return True
            else:
                logger.info("통합 설정 파일이 없습니다. 기본값으로 초기화합니다.")
                self._migrate_existing_configs()
                # 초기 설정 저장 시도
                if self.save_config():
                    logger.info("초기 설정 파일 생성 완료")
                else:
                    logger.warning("초기 설정 파일 생성 실패")
                return True
        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 JSON 파싱 오류: {e}")
            logger.error(f"파일 경로: {self.config_file.absolute()}")
            # 손상된 설정 파일 백업 후 기본값으로 초기화
            self._backup_corrupted_config()
            self._migrate_existing_configs()
            return self.save_config()
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            logger.error(f"파일 경로: {self.config_file.absolute()}")
            return False

    def _load_from_dict(self, data: dict[str, Any]):
        """딕셔너리에서 설정 로드"""
        try:
            if "services" in data:
                services_data = data["services"]
                self.config.services = ServiceConfig(
                    mcp_server=services_data.get("mcp_server", {}),
                    tmdb_api=services_data.get("tmdb_api", {}),
                    api_keys=services_data.get("api_keys", {}),
                )
            if "application" in data:
                app_data = data["application"]
                self.config.application = ApplicationSettings(
                    file_organization=app_data.get("file_organization", {}),
                    backup_settings=app_data.get("backup_settings", {}),
                    logging_config=app_data.get("logging_config", {}),
                    performance_settings=app_data.get("performance_settings", {}),
                )
            if "user_preferences" in data:
                user_data = data["user_preferences"]
                self.config.user_preferences = UserPreferences(
                    gui_state=user_data.get("gui_state", {}),
                    accessibility=user_data.get("accessibility", {}),
                    theme_preferences=user_data.get("theme_preferences", {}),
                    language_settings=user_data.get("language_settings", {}),
                )
            if "metadata" in data:
                self.config.metadata = data["metadata"]
            logger.info("설정 데이터 파싱 완료")
        except Exception as e:
            logger.error(f"설정 데이터 파싱 실패: {e}")
            self.config = UnifiedConfig()

    def _backup_corrupted_config(self):
        """손상된 설정 파일을 백업합니다"""
        try:
            if self.config_file.exists():
                import shutil
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.config_file.parent / f"unified_config_corrupted_{timestamp}.json"
                shutil.copy2(self.config_file, backup_file)
                logger.info(f"손상된 설정 파일 백업: {backup_file}")
        except Exception as e:
            logger.error(f"손상된 설정 파일 백업 실패: {e}")

    def _migrate_existing_configs(self):
        """기존 설정 파일들을 통합 설정으로 마이그레이션"""
        logger.info("기존 설정 파일들을 통합 설정으로 마이그레이션합니다.")
        opencode_file = Path("opencode.json")
        if opencode_file.exists():
            try:
                with opencode_file.open(encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.services.mcp_server = data.get("mcp", {})
                    self.config.services.api_keys = (
                        data.get("mcp", {}).get("task-master-ai", {}).get("environment", {})
                    )
                    logger.info("opencode.json 마이그레이션 완료")
            except Exception as e:
                logger.error(f"opencode.json 마이그레이션 실패: {e}")
        app_config_file = Path("src/animesorter_config.json")
        if app_config_file.exists():
            try:
                with app_config_file.open(encoding="utf-8") as f:
                    data = json.load(f)
                    self.config.application.file_organization = {
                        "destination_root": data.get("destination_root", ""),
                        "organize_mode": data.get("organize_mode", "복사"),
                        "naming_scheme": data.get("naming_scheme", "standard"),
                        "safe_mode": data.get("safe_mode", True),
                        "backup_before_organize": data.get("backup_before_organize", False),
                        "prefer_anitopy": data.get("prefer_anitopy", False),
                        "fallback_parser": data.get("fallback_parser", "FileParser"),
                        "realtime_monitoring": data.get("realtime_monitoring", False),
                        "auto_refresh_interval": data.get("auto_refresh_interval", 30),
                    }
                    self.config.application.backup_settings = {
                        "backup_location": data.get("backup_location", ""),
                        "max_backup_count": data.get("max_backup_count", 10),
                    }
                    self.config.application.logging_config = {
                        "log_level": data.get("log_level", "INFO"),
                        "log_to_file": data.get("log_to_file", False),
                    }
                    self.config.services.tmdb_api = {
                        "api_key": data.get("tmdb_api_key", ""),
                        "language": data.get("tmdb_language", "ko-KR"),
                    }
                    self.config.user_preferences.gui_state = {
                        "window_geometry": data.get("window_geometry", "100,100,1600,900"),
                        "last_source_directory": data.get("last_source_directory", ""),
                        "last_destination_directory": data.get("last_destination_directory", ""),
                        "remember_last_session": data.get("remember_last_session", True),
                    }
                    self.config.user_preferences.accessibility = {
                        "high_contrast_mode": data.get("high_contrast_mode", False),
                        "keyboard_navigation": data.get("keyboard_navigation", True),
                        "screen_reader_support": data.get("screen_reader_support", True),
                    }
                    self.config.user_preferences.theme_preferences = {
                        "theme": data.get("theme", "dark"),
                        "language": data.get("language", "ko"),
                    }
                    logger.info("animesorter_config.json 마이그레이션 완료")
            except Exception as e:
                logger.error(f"animesorter_config.json 마이그레이션 실패: {e}")
        source_files = []
        if opencode_file.exists():
            source_files.append(str(opencode_file))
        if app_config_file.exists():
            source_files.append(str(app_config_file))
        self.config.metadata = {
            "migrated_at": str(Path().cwd()),
            "migration_version": "1.0.0",
            "source_files": source_files,
        }

    def save_config(self) -> bool:
        """통합 설정 파일 저장"""
        try:
            logger.info(f"설정 저장 시작 - 파일 경로: {self.config_file.absolute()}")
            logger.info(f"설정 디렉토리 존재 여부: {self.config_dir.exists()}")
            logger.info(f"설정 파일 존재 여부: {self.config_file.exists()}")

            # 디렉토리 존재 확인 및 생성
            if not self.config_dir.exists():
                self.config_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"설정 디렉토리 생성: {self.config_dir.absolute()}")

            # 백업 디렉토리 확인 및 생성
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"백업 디렉토리 생성: {self.backup_dir.absolute()}")

            # 기존 파일이 있으면 백업 생성
            if self.config_file.exists():
                try:
                    backup_file = (
                        self.backup_dir
                        / f"unified_config_backup_{Path().cwd().name}_{len(list(self.backup_dir.glob('*')))}.json"
                    )
                    with backup_file.open("w", encoding="utf-8") as f:
                        json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)
                    logger.info(f"설정 백업 생성: {backup_file}")
                except Exception as backup_error:
                    logger.warning(f"백업 생성 실패 (계속 진행): {backup_error}")

            # 임시 파일로 먼저 저장한 후 원본 파일로 이동 (원자적 쓰기)
            temp_file = self.config_file.with_suffix(".tmp")
            try:
                with temp_file.open("w", encoding="utf-8") as f:
                    json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)

                # 임시 파일을 원본 파일로 이동
                temp_file.replace(self.config_file)
                logger.info(f"통합 설정 파일 저장 완료: {self.config_file.absolute()}")
                self.config_saved.emit()
                return True
            except Exception as write_error:
                # 임시 파일 정리
                if temp_file.exists():
                    temp_file.unlink()
                raise write_error

        except PermissionError as e:
            logger.error(f"설정 파일 저장 권한 오류: {e}")
            logger.error(f"원본 경로: {self.config_file.absolute()}")
            logger.error("관리자 권한으로 실행하거나 다른 위치에 저장을 시도합니다.")
            # 대안 경로로 재시도
            success = self._save_to_alternative_location()
            if not success:
                error_msg = (
                    f"설정 저장 실패: 권한 오류\n\n"
                    f"원본 경로: {self.config_file.absolute()}\n"
                    f"오류: {e}\n\n"
                    f"해결 방법:\n"
                    f"1. 관리자 권한으로 실행\n"
                    f"2. exe 파일을 다른 폴더로 이동\n"
                    f"3. 폴더 쓰기 권한 확인"
                )
                self.config_save_failed.emit(error_msg)
            return success
        except OSError as e:
            logger.error(f"설정 파일 저장 OS 오류: {e}")
            logger.error(f"원본 경로: {self.config_file.absolute()}")
            # 대안 경로로 재시도
            success = self._save_to_alternative_location()
            if not success:
                error_msg = (
                    f"설정 저장 실패: 시스템 오류\n\n"
                    f"원본 경로: {self.config_file.absolute()}\n"
                    f"오류: {e}\n\n"
                    f"해결 방법:\n"
                    f"1. 디스크 공간 확인\n"
                    f"2. 파일이 다른 프로그램에서 사용 중인지 확인\n"
                    f"3. 폴더 접근 권한 확인"
                )
                self.config_save_failed.emit(error_msg)
            return success
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            logger.error(f"설정 파일 경로: {self.config_file.absolute()}")
            logger.error(f"설정 디렉토리: {self.config_dir.absolute()}")
            error_msg = (
                f"설정 저장 실패: 예상치 못한 오류\n\n"
                f"경로: {self.config_file.absolute()}\n"
                f"오류: {e}\n\n"
                f"해결 방법:\n"
                f"1. 프로그램을 재시작\n"
                f"2. 설정 파일을 수동으로 삭제 후 재시도\n"
                f"3. 관리자 권한으로 실행"
            )
            self.config_save_failed.emit(error_msg)
            return False

    def _save_to_alternative_location(self) -> bool:
        """대안 위치에 설정 파일 저장"""
        try:
            # 사용자 홈 디렉토리에 AnimeSorter 폴더 생성
            home_dir = Path.home()
            alt_config_dir = home_dir / "AnimeSorter" / "config"
            alt_config_dir.mkdir(parents=True, exist_ok=True)

            alt_config_file = alt_config_dir / "unified_config.json"
            alt_backup_dir = alt_config_dir / "backups"
            alt_backup_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"대안 위치에 설정 저장 시도: {alt_config_file.absolute()}")

            # 기존 파일이 있으면 백업
            if alt_config_file.exists():
                backup_file = (
                    alt_backup_dir
                    / f"unified_config_backup_{len(list(alt_backup_dir.glob('*')))}.json"
                )
                with backup_file.open("w", encoding="utf-8") as f:
                    json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)
                logger.info(f"대안 위치 백업 생성: {backup_file}")

            # 임시 파일로 저장 후 이동
            temp_file = alt_config_file.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)

            temp_file.replace(alt_config_file)

            # 설정 경로 업데이트
            self.config_dir = alt_config_dir
            self.config_file = alt_config_file
            self.backup_dir = alt_backup_dir

            logger.info(f"대안 위치에 설정 저장 완료: {alt_config_file.absolute()}")
            self.config_saved.emit()
            return True

        except Exception as e:
            logger.error(f"대안 위치 저장도 실패: {e}")
            error_msg = (
                f"설정 저장 실패: 모든 저장 위치에서 실패\n\n"
                f"원본 경로: {self.config_file.absolute()}\n"
                f"대안 경로: {alt_config_file.absolute()}\n"
                f"오류: {e}\n\n"
                f"해결 방법:\n"
                f"1. 관리자 권한으로 실행\n"
                f"2. 바이러스 백신 프로그램 확인\n"
                f"3. 디스크 공간 및 권한 확인\n"
                f"4. 프로그램을 다른 폴더로 이동"
            )
            self.config_save_failed.emit(error_msg)
            return False

    def _to_dict(self) -> dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return asdict(self.config)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        try:
            section_obj = getattr(self.config, section, None)
            if section_obj:
                return getattr(section_obj, key, default)
            return default
        except Exception as e:
            logger.error(f"설정값 조회 실패: {section}.{key} - {e}")
            return default

    def set(self, section: str, key: str, value: Any) -> bool:
        """설정값 설정"""
        try:
            section_obj = getattr(self.config, section, None)
            if section_obj:
                setattr(section_obj, key, value)
                self._notify_change_callbacks(section, value)
                self.config_changed.emit(section, value)
                return True
            return False
        except Exception as e:
            logger.error(f"설정값 설정 실패: {section}.{key} = {value} - {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """설정값 조회 (SettingsManager 호환성)"""
        try:
            if key == "destination_root":
                return getattr(self.config.application, "destination_root", default)
            if key == "theme":
                return self.config.user_preferences.theme_preferences.get("theme", default)
            if key == "language":
                return self.config.user_preferences.theme_preferences.get("language", default)
            if key == "font_family":
                return getattr(self.config.user_preferences, "font_family", default)
            if key == "font_size":
                return getattr(self.config.user_preferences, "font_size", default)
            if key == "ui_style":
                return getattr(self.config.user_preferences, "ui_style", default)
            if key == "last_source_directory":
                return self.config.user_preferences.gui_state.get("last_source_directory", default)
            if key == "last_destination_directory":
                return self.config.user_preferences.gui_state.get(
                    "last_destination_directory", default
                )
            if key == "organize_mode":
                return self.config.application.file_organization.get("organize_mode", default)
            if key == "naming_scheme":
                return self.config.application.file_organization.get("naming_scheme", default)
            if key == "safe_mode":
                return self.config.application.file_organization.get("safe_mode", default)
            if key == "backup_before_organize":
                return self.config.application.file_organization.get(
                    "backup_before_organize", default
                )
            if key == "prefer_anitopy":
                return self.config.application.file_organization.get("prefer_anitopy", default)
            if key == "fallback_parser":
                return self.config.application.file_organization.get("fallback_parser", default)
            if key == "log_level":
                return self.config.application.logging_config.get("log_level", default)
            if key == "log_to_file":
                return self.config.application.logging_config.get("log_to_file", default)
            if key == "backup_location":
                return self.config.application.backup_settings.get("backup_location", default)
            if key == "max_backup_count":
                return self.config.application.backup_settings.get("max_backup_count", default)
            return default
        except Exception as e:
            logger.error(f"설정값 조회 실패: {key} - {e}")
            return default

    def set_setting(self, key: str, value: Any) -> bool:
        """설정값 설정 (SettingsManager 호환성)"""
        try:
            if key == "destination_root":
                if hasattr(self.config.application, "file_organization"):
                    self.config.application.file_organization["destination_root"] = value
                    self._notify_change_callbacks("application", value)
                    self.config_changed.emit("application", value)
                    return True
                return False
            if key == "theme":
                if hasattr(self.config.user_preferences, "theme_preferences"):
                    self.config.user_preferences.theme_preferences["theme"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            if key == "language":
                if hasattr(self.config.user_preferences, "theme_preferences"):
                    self.config.user_preferences.theme_preferences["language"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            if key == "font_family":
                return self.set("user_preferences", "font_family", value)
            if key == "font_size":
                return self.set("user_preferences", "font_size", value)
            if key == "ui_style":
                return self.set("user_preferences", "ui_style", value)
            if key == "last_source_directory":
                if hasattr(self.config.user_preferences, "gui_state"):
                    self.config.user_preferences.gui_state["last_source_directory"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            if key == "last_destination_directory":
                if hasattr(self.config.user_preferences, "gui_state"):
                    self.config.user_preferences.gui_state["last_destination_directory"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            return self.set("user_preferences", key, value)
        except Exception as e:
            logger.error(f"설정값 설정 실패: {key} = {value} - {e}")
            return False

    def get_section(self, section: str) -> Any | None:
        """섹션 전체 조회"""
        return getattr(self.config, section, None)

    def set_section(self, section: str, data: dict[str, Any]) -> bool:
        """섹션 전체 설정"""
        try:
            section_obj = getattr(self.config, section, None)
            if section_obj:
                for key, value in data.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
                self._notify_change_callbacks(section, data)
                self.config_changed.emit(section, data)
                return True
            return False
        except Exception as e:
            logger.error(f"섹션 설정 실패: {section} - {e}")
            return False

    def export_section(self, section: str, file_path: Path) -> bool:
        """특정 섹션을 별도 파일로 내보내기"""
        try:
            section_data = self.get_section(section)
            if section_data:
                with file_path.open("w", encoding="utf-8") as f:
                    json.dump(asdict(section_data), f, ensure_ascii=False, indent=2)
                logger.info(f"섹션 내보내기 완료: {section} -> {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"섹션 내보내기 실패: {section} -> {file_path} - {e}")
            return False

    def import_section(self, section: str, file_path: Path) -> bool:
        """별도 파일에서 특정 섹션 가져오기"""
        try:
            if file_path.exists():
                with file_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                if self.set_section(section, data):
                    logger.info(f"섹션 가져오기 완료: {file_path} -> {section}")
                    return True
            return False
        except Exception as e:
            logger.error(f"섹션 가져오기 실패: {file_path} -> {section} - {e}")
            return False


unified_config_manager = UnifiedConfigManager()
