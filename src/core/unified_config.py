"""
통합 설정 관리 시스템 - AnimeSorter

기존의 여러 설정 파일들을 통합하여 관리하는 시스템입니다.
- opencode.json: MCP 서버 설정
- animesorter_config.json: 애플리케이션 설정
"""

import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

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

    # 호환성을 위한 직접 속성들
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

    # 호환성을 위한 직접 속성들
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

    config_changed = pyqtSignal(str, object)  # section, new_value
    config_loaded = pyqtSignal()
    config_saved = pyqtSignal()

    def __init__(self, config_dir: Path | None = None):
        super().__init__()
        # data 디렉토리를 기준으로 config 디렉토리 찾기
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "data" / "config"
        self.config_dir.mkdir(exist_ok=True)

        self.config = UnifiedConfig()
        self.config_file = self.config_dir / "unified_config.json"
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        self._change_callbacks: list[Callable] = []

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
                self.save_config()
                return True
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
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
            # 기본값으로 초기화
            self.config = UnifiedConfig()

    def _migrate_existing_configs(self):
        """기존 설정 파일들을 통합 설정으로 마이그레이션"""
        logger.info("기존 설정 파일들을 통합 설정으로 마이그레이션합니다.")

        # opencode.json 마이그레이션
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

        # animesorter_config.json 마이그레이션
        app_config_file = Path("src/animesorter_config.json")
        if app_config_file.exists():
            try:
                with app_config_file.open(encoding="utf-8") as f:
                    data = json.load(f)

                    # 파일 정리 설정
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

                    # 백업 설정
                    self.config.application.backup_settings = {
                        "backup_location": data.get("backup_location", ""),
                        "max_backup_count": data.get("max_backup_count", 10),
                    }

                    # 로깅 설정
                    self.config.application.logging_config = {
                        "log_level": data.get("log_level", "INFO"),
                        "log_to_file": data.get("log_to_file", False),
                    }

                    # TMDB 설정
                    self.config.services.tmdb_api = {
                        "api_key": data.get("tmdb_api_key", ""),
                        "language": data.get("tmdb_language", "ko-KR"),
                    }

                    # GUI 상태
                    self.config.user_preferences.gui_state = {
                        "window_geometry": data.get("window_geometry", "100,100,1600,900"),
                        "last_source_directory": data.get("last_source_directory", ""),
                        "last_destination_directory": data.get("last_destination_directory", ""),
                        "remember_last_session": data.get("remember_last_session", True),
                    }

                    # 접근성 설정
                    self.config.user_preferences.accessibility = {
                        "high_contrast_mode": data.get("high_contrast_mode", False),
                        "keyboard_navigation": data.get("keyboard_navigation", True),
                        "screen_reader_support": data.get("screen_reader_support", True),
                    }

                    # 테마 설정
                    self.config.user_preferences.theme_preferences = {
                        "theme": data.get("theme", "dark"),
                        "language": data.get("language", "ko"),
                    }

                    logger.info("animesorter_config.json 마이그레이션 완료")
            except Exception as e:
                logger.error(f"animesorter_config.json 마이그레이션 실패: {e}")

        # 메타데이터 설정
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
            # 백업 생성
            if self.config_file.exists():
                backup_file = (
                    self.backup_dir
                    / f"unified_config_backup_{Path().cwd().name}_{len(list(self.backup_dir.glob('*')))}.json"
                )
                with backup_file.open("w", encoding="utf-8") as f:
                    json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)
                logger.info(f"설정 백업 생성: {backup_file}")

            # 새 설정 저장
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, ensure_ascii=False, indent=2)

            logger.info("통합 설정 파일 저장 완료")
            self.config_saved.emit()
            return True
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
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
            # key에 따라 적절한 섹션과 키로 변환
            if key == "destination_root":
                # file_organization 딕셔너리 안의 destination_root 설정
                if hasattr(self.config.application, "file_organization"):
                    self.config.application.file_organization["destination_root"] = value
                    self._notify_change_callbacks("application", value)
                    self.config_changed.emit("application", value)
                    return True
                return False
            if key == "theme":
                # theme_preferences 딕셔너리 안의 theme 설정
                if hasattr(self.config.user_preferences, "theme_preferences"):
                    self.config.user_preferences.theme_preferences["theme"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            if key == "language":
                # theme_preferences 딕셔너리 안의 language 설정
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
                # gui_state 딕셔너리 안의 last_source_directory 설정
                if hasattr(self.config.user_preferences, "gui_state"):
                    self.config.user_preferences.gui_state["last_source_directory"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            if key == "last_destination_directory":
                # gui_state 딕셔너리 안의 last_destination_directory 설정
                if hasattr(self.config.user_preferences, "gui_state"):
                    self.config.user_preferences.gui_state["last_destination_directory"] = value
                    self._notify_change_callbacks("user_preferences", value)
                    self.config_changed.emit("user_preferences", value)
                    return True
                return False
            # 기본적으로 user_preferences에 설정
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


# 전역 인스턴스
unified_config_manager = UnifiedConfigManager()
