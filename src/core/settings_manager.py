"""
설정 관리 모듈 - AnimeSorter

애플리케이션 설정을 관리하고 저장/로드하는 기능을 제공합니다.
통합 설정 시스템(UnifiedConfigManager)을 기반으로 호환성을 유지합니다.

DEPRECATED: 새로운 코드에서는 UnifiedConfigManager를 직접 사용하는 것을 권장.
이 클래스는 기존 코드의 호환성을 위해 유지됩니다.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

# 새로운 통합 설정 시스템 import
try:
    from src.core.unified_config import unified_config_manager

    UNIFIED_CONFIG_AVAILABLE = True
except ImportError:
    UNIFIED_CONFIG_AVAILABLE = False


@dataclass
class AppSettings:
    """애플리케이션 설정"""

    # 파일 정리 설정
    destination_root: str = ""
    organize_mode: str = "복사"  # 복사, 이동, 하드링크
    naming_scheme: str = "standard"  # standard, minimal, detailed
    safe_mode: bool = True
    backup_before_organize: bool = False

    # 파싱 설정
    prefer_anitopy: bool = False
    fallback_parser: str = "FileParser"  # GuessIt, Custom, FileParser
    realtime_monitoring: bool = False
    auto_refresh_interval: int = 30

    # TMDB 설정
    tmdb_api_key: str = ""
    tmdb_language: str = "ko-KR"  # ko-KR, en-US, ja-JP

    # 고급 설정
    show_advanced_options: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = False

    # 백업 설정
    backup_location: str = ""
    max_backup_count: int = 10

    # GUI 상태 (세션별)
    window_geometry: str | None = None
    table_column_widths: dict[str, int] | None = None
    last_source_directory: str = ""
    last_destination_directory: str = ""
    last_source_files: list[str] | None = None
    splitter_positions: list[int] | None = None

    # 세션 관리
    remember_last_session: bool = True

    # 외관 설정
    theme: str = "auto"  # auto, light, dark
    high_contrast_mode: bool = False
    keyboard_navigation: bool = True
    screen_reader_support: bool = True
    language: str = "ko"  # ko, en

    def get(self, key: str, default: Any = None) -> Any:
        """설정값을 안전하게 가져오는 메서드"""
        return getattr(self, key, default)


class SettingsManager(QObject):
    """
    설정 관리자

    DEPRECATED: UnifiedConfigManager를 직접 사용하세요.
    이 클래스는 호환성을 위해 유지됩니다.
    """

    settings_changed = pyqtSignal()

    def __init__(self, config_file: str = "data/config/unified_config.json"):
        """초기화"""
        super().__init__()
        self.config_file = Path(config_file)
        self.settings_file = str(self.config_file)  # settings_file 속성 추가
        self.settings = AppSettings()

        # 새로운 통합 설정 시스템이 사용 가능한 경우
        if UNIFIED_CONFIG_AVAILABLE:
            # 설정 변경 콜백 등록
            unified_config_manager.add_change_callback(self._on_config_changed)

        self.load_settings()

    def load_settings(self) -> bool:
        """설정 파일에서 설정 로드"""
        try:
            # 새로운 통합 설정 시스템이 사용 가능한 경우
            if UNIFIED_CONFIG_AVAILABLE:
                # 통합 설정에서 애플리케이션 설정 로드
                app_settings = unified_config_manager.get_section("application")
                user_prefs = unified_config_manager.get_section("user_preferences")

                if app_settings:
                    # 파일 정리 설정
                    file_org = app_settings.file_organization
                    self.settings.destination_root = file_org.get("destination_root", "")
                    self.settings.organize_mode = file_org.get("organize_mode", "복사")
                    self.settings.naming_scheme = file_org.get("naming_scheme", "standard")
                    self.settings.safe_mode = file_org.get("safe_mode", True)
                    self.settings.backup_before_organize = file_org.get(
                        "backup_before_organize", False
                    )
                    self.settings.prefer_anitopy = file_org.get("prefer_anitopy", False)
                    self.settings.fallback_parser = file_org.get("fallback_parser", "FileParser")
                    self.settings.realtime_monitoring = file_org.get("realtime_monitoring", False)
                    self.settings.auto_refresh_interval = file_org.get("auto_refresh_interval", 30)

                    # 백업 설정
                    backup_settings = app_settings.backup_settings
                    self.settings.backup_location = backup_settings.get("backup_location", "")
                    self.settings.max_backup_count = backup_settings.get("max_backup_count", 10)

                    # 로깅 설정
                    logging_config = app_settings.logging_config
                    self.settings.log_level = logging_config.get("log_level", "INFO")
                    self.settings.log_to_file = logging_config.get("log_to_file", False)

                if user_prefs:
                    # GUI 상태
                    gui_state = user_prefs.gui_state
                    self.settings.window_geometry = gui_state.get("window_geometry")
                    self.settings.last_source_directory = gui_state.get("last_source_directory", "")
                    self.settings.last_destination_directory = gui_state.get(
                        "last_destination_directory", ""
                    )
                    self.settings.remember_last_session = gui_state.get(
                        "remember_last_session", True
                    )

                    # 접근성 설정
                    accessibility = user_prefs.accessibility
                    self.settings.high_contrast_mode = accessibility.get(
                        "high_contrast_mode", False
                    )
                    self.settings.keyboard_navigation = accessibility.get(
                        "keyboard_navigation", True
                    )
                    self.settings.screen_reader_support = accessibility.get(
                        "screen_reader_support", True
                    )

                    # 테마 설정
                    theme_prefs = user_prefs.theme_preferences
                    self.settings.theme = theme_prefs.get("theme", "auto")
                    self.settings.language = theme_prefs.get("language", "ko")

                # TMDB 설정
                services_section = unified_config_manager.get_section("services")
                if services_section:
                    tmdb_config = getattr(services_section, "tmdb_api", None)
                    if tmdb_config:
                        self.settings.tmdb_api_key = tmdb_config.get("api_key", "")
                        self.settings.tmdb_language = tmdb_config.get("language", "ko-KR")

                print("✅ 통합 설정에서 설정 로드 완료")
                return True
            else:
                # 기존 방식으로 설정 로드
                if self.config_file.exists():
                    with self.config_file.open(encoding="utf-8") as f:
                        data = json.load(f)

                    # 기존 설정과 병합
                    for key, value in data.items():
                        if hasattr(self.settings, key):
                            setattr(self.settings, key, value)

                    print(f"✅ 설정 로드 완료: {self.config_file}")
                    return True
                print(f"⚠️ 설정 파일이 없습니다: {self.config_file}")
                return False

        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            return False

    def save_settings(self) -> bool:
        """설정을 파일에 저장"""
        try:
            # 새로운 통합 설정 시스템이 사용 가능한 경우
            if UNIFIED_CONFIG_AVAILABLE:
                # 통합 설정에 현재 설정값들을 업데이트
                app_settings = {
                    "file_organization": {
                        "destination_root": self.settings.destination_root,
                        "organize_mode": self.settings.organize_mode,
                        "naming_scheme": self.settings.naming_scheme,
                        "safe_mode": self.settings.safe_mode,
                        "backup_before_organize": self.settings.backup_before_organize,
                        "prefer_anitopy": self.settings.prefer_anitopy,
                        "fallback_parser": self.settings.fallback_parser,
                        "realtime_monitoring": self.settings.realtime_monitoring,
                        "auto_refresh_interval": self.settings.auto_refresh_interval,
                    },
                    "backup_settings": {
                        "backup_location": self.settings.backup_location,
                        "max_backup_count": self.settings.max_backup_count,
                    },
                    "logging_config": {
                        "log_level": self.settings.log_level,
                        "log_to_file": self.settings.log_to_file,
                    },
                }

                user_prefs = {
                    "gui_state": {
                        "window_geometry": self.settings.window_geometry,
                        "last_source_directory": self.settings.last_source_directory,
                        "last_destination_directory": self.settings.last_destination_directory,
                        "remember_last_session": self.settings.remember_last_session,
                    },
                    "accessibility": {
                        "high_contrast_mode": self.settings.high_contrast_mode,
                        "keyboard_navigation": self.settings.keyboard_navigation,
                        "screen_reader_support": self.settings.screen_reader_support,
                    },
                    "theme_preferences": {
                        "theme": self.settings.theme,
                        "language": self.settings.language,
                    },
                }

                # TMDB 설정
                services_settings = {
                    "tmdb_api": {
                        "api_key": getattr(self.settings, 'tmdb_api_key', ''),
                        "language": getattr(self.settings, 'tmdb_language', 'ko-KR'),
                    },
                    "api_keys": {
                        "tmdb": getattr(self.settings, 'tmdb_api_key', ''),
                    }
                }

                # 통합 설정에 업데이트
                unified_config_manager.set_section("application", app_settings)
                unified_config_manager.set_section("user_preferences", user_prefs)
                unified_config_manager.set_section("services", services_settings)

                # 통합 설정 파일 저장
                if unified_config_manager.save_config():
                    print("✅ 통합 설정에 설정 저장 완료")
                    print(f"📋 저장된 테마: {self.settings.theme}")
                    print(f"📋 저장된 소스 디렉토리: {self.settings.last_source_directory}")
                    print(f"📋 저장된 대상 디렉토리: {self.settings.last_destination_directory}")
                    return True

                print("❌ 통합 설정 저장 실패")
                return False
            else:
                # 기존 방식으로 설정 저장
                # 설정 디렉토리 생성
                self.config_file.parent.mkdir(parents=True, exist_ok=True)

                # 설정을 딕셔너리로 변환
                settings_dict = asdict(self.settings)

                # None 값 제거
                settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

                # UTF-8 인코딩으로 저장하고 ASCII 문자 변환 방지
                with self.config_file.open("w", encoding="utf-8", newline="\n") as f:
                    json.dump(
                        settings_dict, f, ensure_ascii=False, indent=2, separators=(",", ": ")
                    )

                print(f"✅ 설정 저장 완료: {self.config_file}")
                print(f"📋 저장된 테마: {self.settings.theme}")
                print(f"📋 저장된 소스 디렉토리: {self.settings.last_source_directory}")
                print(f"📋 저장된 대상 디렉토리: {self.settings.last_destination_directory}")
                return True

        except Exception as e:
            print(f"❌ 설정 저장 실패: {e}")
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기"""
        return getattr(self.settings, key, default)

    def set_setting(self, key: str, value: Any) -> bool:
        """설정 값 설정"""
        try:
            # AppSettings에 정의된 키이거나 ui_session_state 같은 동적 키인 경우
            if hasattr(self.settings, key) or key.startswith('ui_'):
                setattr(self.settings, key, value)
                self.settings_changed.emit()
                return True
            print(f"⚠️ 알 수 없는 설정 키: {key}")
            return False
        except Exception as e:
            print(f"❌ 설정 변경 실패: {e}")
            return False

    def update_settings(self, new_settings: dict[str, Any]) -> bool:
        """여러 설정을 한 번에 업데이트"""
        try:
            print("🔍 SettingsManager.update_settings 호출됨")
            print(f"  받은 설정: {new_settings}")
            updated = False
            for key, value in new_settings.items():
                if hasattr(self.settings, key):
                    old_value = getattr(self.settings, key)
                    setattr(self.settings, key, value)
                    print(f"  ✅ {key}: '{old_value}' -> '{value}'")
                    updated = True
                else:
                    print(f"⚠️ 알 수 없는 설정 키: {key}")

            if updated:
                print("  🔔 settingsChanged 시그널 발생")
                self.settings_changed.emit()

            return updated

        except Exception as e:
            print(f"❌ 설정 업데이트 실패: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """기본값으로 설정 초기화"""
        try:
            self.settings = AppSettings()
            self.settings_changed.emit()
            return True
        except Exception as e:
            print(f"❌ 설정 초기화 실패: {e}")
            return False

    def validate_settings(self) -> dict[str, str]:
        """설정 유효성 검사"""
        errors = {}

        # 경고 수준 검사 (애플리케이션 실행은 가능하지만 기능 제한)
        warnings = {}

        if not self.settings.tmdb_api_key:
            warnings["tmdb_api_key"] = (
                "TMDB API 키가 설정되지 않았습니다. TMDB 검색 기능이 제한됩니다."
            )

        if not self.settings.destination_root:
            warnings["destination_root"] = (
                "대상 디렉토리가 설정되지 않았습니다. 파일 정리 기능이 제한됩니다."
            )
        elif not Path(self.settings.destination_root).exists():
            errors["destination_root"] = "대상 디렉토리가 존재하지 않습니다"

        # 값 범위 검사
        if self.settings.auto_refresh_interval < 5:
            errors["auto_refresh_interval"] = "자동 새로고침 간격은 최소 5초여야 합니다"

        if self.settings.max_backup_count < 1:
            errors["max_backup_count"] = "최대 백업 개수는 최소 1개여야 합니다"

        # 경고는 errors에 포함하지 않음 (애플리케이션 실행 가능)
        return errors

    def export_settings(self, export_path: str) -> bool:
        """설정을 다른 파일로 내보내기"""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)

            settings_dict = asdict(self.settings)
            with export_file.open("w", encoding="utf-8") as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=2)

            print(f"✅ 설정 내보내기 완료: {export_file}")
            return True

        except Exception as e:
            print(f"❌ 설정 내보내기 실패: {e}")
            return False

    def import_settings(self, import_path: str) -> bool:
        """다른 파일에서 설정 가져오기"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                print(f"⚠️ 가져올 파일이 없습니다: {import_file}")
                return False

            with import_file.open(encoding="utf-8") as f:
                data = json.load(f)

            # 기존 설정과 병합
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)

            self.settings_changed.emit()
            print(f"✅ 설정 가져오기 완료: {import_file}")
            return True

        except Exception as e:
            print(f"❌ 설정 가져오기 실패: {e}")
            return False

    def get_default_settings(self) -> AppSettings:
        """기본 설정 반환"""
        return AppSettings()

    def get_settings_summary(self) -> dict[str, Any]:
        """설정 요약 반환"""
        summary = {
            "total_settings": len(asdict(self.settings)),
            "configured_settings": len([v for v in asdict(self.settings).values() if v]),
            "validation_errors": len(self.validate_settings()),
            "config_file_path": str(self.config_file),
            "config_file_exists": self.config_file.exists(),
        }

        # 새로운 통합 설정 시스템 정보 추가
        if UNIFIED_CONFIG_AVAILABLE:
            summary.update(
                {
                    "unified_config_available": True,
                    "config_file_path": str(unified_config_manager.config_file),
                    "config_file_exists": unified_config_manager.config_file.exists(),
                    "backup_dir_path": str(unified_config_manager.backup_dir),
                    "migrated_source_files": unified_config_manager.config.development.source_files,
                }
            )
        else:
            summary["unified_config_available"] = False

        return summary

    def _on_config_changed(self, section: str, value: Any) -> None:
        """통합 설정 시스템에서 설정이 변경되었을 때 호출"""
        try:
            if section == "application":
                # 애플리케이션 설정 동기화
                self._sync_application_settings(value)
            elif section == "user_preferences":
                # 사용자 설정 동기화
                self._sync_user_preferences(value)
            elif section == "services":
                # 서비스 설정 동기화
                self._sync_service_settings(value)
            else:
                # 기타 섹션 동기화
                self._sync_general_settings(section, value)
        except Exception as e:
            print(f"⚠️ 설정 동기화 실패: {e}")

    def _sync_application_settings(self, app_settings: Any) -> None:
        """애플리케이션 설정 동기화"""
        if not UNIFIED_CONFIG_AVAILABLE:
            return

        try:
            # 파일 정리 설정 동기화
            if hasattr(app_settings, "file_organization"):
                file_org = app_settings.file_organization
                if file_org.get("destination_root") != self.settings.destination_root:
                    self.settings.destination_root = file_org.get("destination_root", "")
                if file_org.get("organize_mode") != self.settings.organize_mode:
                    self.settings.organize_mode = file_org.get("organize_mode", "복사")
                # 기타 파일 정리 설정들도 동기화...

            # 백업 설정 동기화
            if hasattr(app_settings, "backup_settings"):
                backup_settings = app_settings.backup_settings
                if backup_settings.get("backup_location") != self.settings.backup_location:
                    self.settings.backup_location = backup_settings.get("backup_location", "")

            # 로깅 설정 동기화
            if hasattr(app_settings, "logging_config"):
                logging_config = app_settings.logging_config
                if logging_config.get("log_level") != self.settings.log_level:
                    self.settings.log_level = logging_config.get("log_level", "INFO")

            # 설정 변경 시그널 발생
            self.settings_changed.emit()
            print("✅ 새로운 설정 시스템과 동기화 완료")

        except Exception as e:
            print(f"❌ 설정 동기화 실패: {e}")

    def _sync_user_preferences(self, user_prefs: Any) -> None:
        """사용자 설정 동기화"""
        if not UNIFIED_CONFIG_AVAILABLE:
            return

        try:
            # GUI 상태 동기화
            if hasattr(user_prefs, "gui_state"):
                gui_state = user_prefs.gui_state
                if gui_state.get("window_geometry") != self.settings.window_geometry:
                    self.settings.window_geometry = gui_state.get("window_geometry")
                if gui_state.get("last_source_directory") != self.settings.last_source_directory:
                    self.settings.last_source_directory = gui_state.get("last_source_directory", "")
                if (
                    gui_state.get("last_destination_directory")
                    != self.settings.last_destination_directory
                ):
                    self.settings.last_destination_directory = gui_state.get(
                        "last_destination_directory", ""
                    )

            # 접근성 설정 동기화
            if hasattr(user_prefs, "accessibility"):
                accessibility = user_prefs.accessibility
                if accessibility.get("high_contrast_mode") != self.settings.high_contrast_mode:
                    self.settings.high_contrast_mode = accessibility.get(
                        "high_contrast_mode", False
                    )
                if accessibility.get("keyboard_navigation") != self.settings.keyboard_navigation:
                    self.settings.keyboard_navigation = accessibility.get(
                        "keyboard_navigation", True
                    )

            # 테마 설정 동기화
            if hasattr(user_prefs, "theme_preferences"):
                theme_prefs = user_prefs.theme_preferences
                if theme_prefs.get("theme") != self.settings.theme:
                    self.settings.theme = theme_prefs.get("theme", "auto")
                if theme_prefs.get("language") != self.settings.language:
                    self.settings.language = theme_prefs.get("language", "ko")

            # 설정 변경 시그널 발생
            self.settings_changed.emit()
            print("✅ 사용자 설정 동기화 완료")

        except Exception as e:
            print(f"❌ 사용자 설정 동기화 실패: {e}")

    def _sync_service_settings(self, service_settings: Any) -> None:
        """서비스 설정 동기화"""
        if not UNIFIED_CONFIG_AVAILABLE:
            return

        try:
            # TMDB 설정 동기화
            if hasattr(service_settings, "tmdb_api"):
                tmdb_config = service_settings.tmdb_api
                if tmdb_config.get("api_key") != self.settings.tmdb_api_key:
                    self.settings.tmdb_api_key = tmdb_config.get("api_key", "")
                if tmdb_config.get("language") != self.settings.tmdb_language:
                    self.settings.tmdb_language = tmdb_config.get("language", "ko-KR")

            # 설정 변경 시그널 발생
            self.settings_changed.emit()
            print("✅ 서비스 설정 동기화 완료")

        except Exception as e:
            print(f"❌ 서비스 설정 동기화 실패: {e}")

    def _sync_general_settings(self, section: str, value: Any) -> None:
        """일반 설정 동기화"""
        if not UNIFIED_CONFIG_AVAILABLE:
            return

        try:
            print(f"✅ 일반 설정 동기화: {section} = {value}")
            # 설정 변경 시그널 발생
            self.settings_changed.emit()

        except Exception as e:
            print(f"❌ 일반 설정 동기화 실패: {e}")

    # === 통합 설정 시스템 메서드들 ===

    def use_unified_config_system(self) -> bool:
        """통합 설정 시스템 사용 여부"""
        return UNIFIED_CONFIG_AVAILABLE

    def get_unified_config(self) -> Any:
        """통합 설정 시스템의 설정 반환"""
        if UNIFIED_CONFIG_AVAILABLE:
            return unified_config_manager.config
        return None

    def export_unified_config_section(self, section: str, file_path: Path) -> bool:
        """통합 설정의 특정 섹션을 별도 파일로 내보내기"""
        if UNIFIED_CONFIG_AVAILABLE:
            return unified_config_manager.export_section(section, file_path)
        return False

    def import_unified_config_section(self, section: str, file_path: Path) -> bool:
        """별도 파일에서 통합 설정의 특정 섹션 가져오기"""
        if UNIFIED_CONFIG_AVAILABLE:
            return unified_config_manager.import_section(section, file_path)
        return False
