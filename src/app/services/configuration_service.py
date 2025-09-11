"""
통합된 설정 관리 서비스 - AnimeSorter

기존의 여러 Configuration Manager 클래스들을 통합하여 단일 서비스로 제공합니다.
- UnifiedConfigManager
- ManagerRegistry
- PluginManager
- UIStateManager (설정 관련 부분)
"""

import logging
from pathlib import Path
from typing import Any, Optional, Protocol

from PyQt5.QtCore import QObject, QSettings, pyqtSignal

logger = logging.getLogger(__name__)


class IConfigurationManager(Protocol):
    """설정 관리자 인터페이스"""

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """설정 값 조회"""
        ...

    def set(self, section: str, key: str, value: Any) -> None:
        """설정 값 저장"""
        ...

    def save(self) -> bool:
        """설정 저장"""
        ...


class IPluginManager(Protocol):
    """플러그인 관리자 인터페이스"""

    def load_plugin(self, plugin_path: str) -> bool:
        """플러그인 로드"""
        ...

    def unload_plugin(self, plugin_name: str) -> bool:
        """플러그인 언로드"""
        ...

    def get_loaded_plugins(self) -> list[str]:
        """로드된 플러그인 목록"""
        ...


class ConfigurationService(QObject):
    """통합된 설정 관리 서비스"""

    # 시그널 정의
    configuration_changed = pyqtSignal(str, str, object)  # section, key, value
    plugin_loaded = pyqtSignal(str)  # plugin_name
    plugin_unloaded = pyqtSignal(str)  # plugin_name
    settings_saved = pyqtSignal()
    settings_loaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

        # 서비스 컴포넌트들
        self._config_manager: Optional[IConfigurationManager] = None
        self._plugin_manager: Optional[IPluginManager] = None
        self._ui_settings: Optional[QSettings] = None

        # 설정 파일 경로
        self._config_file_path = Path("config/unified_config.json")
        self._ui_settings_path = "AnimeSorter/UI_State"

        # 설정 캐시
        self._config_cache: dict[str, Any] = {}
        self._ui_cache: dict[str, Any] = {}

        self._initialize_components()
        self.logger.info("설정 서비스 초기화 완료")

    def _initialize_components(self):
        """설정 서비스 컴포넌트들 초기화"""
        try:
            self._initialize_config_manager()
            self._initialize_plugin_manager()
            self._initialize_ui_settings()
            self._load_configuration()
            self.logger.info("✅ 설정 서비스 컴포넌트 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 설정 서비스 컴포넌트 초기화 실패: {e}")

    def _initialize_config_manager(self):
        """설정 관리자 초기화"""
        try:
            from src.core.unified_config import unified_config_manager

            self._config_manager = unified_config_manager
            self.logger.info("✅ 설정 관리자 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 설정 관리자 초기화 실패: {e}")

    def _initialize_plugin_manager(self):
        """플러그인 관리자 초기화"""
        try:
            from src.plugins.base import PluginManager

            self._plugin_manager = PluginManager()
            self.logger.info("✅ 플러그인 관리자 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ 플러그인 관리자 초기화 실패: {e}")

    def _initialize_ui_settings(self):
        """UI 설정 초기화"""
        try:
            self._ui_settings = QSettings(self._ui_settings_path)
            self.logger.info("✅ UI 설정 초기화 완료")
        except Exception as e:
            self.logger.error(f"❌ UI 설정 초기화 실패: {e}")

    def _load_configuration(self):
        """설정 로드"""
        try:
            if self._config_manager:
                # 기본 설정 로드
                self._load_default_configuration()
                self.settings_loaded.emit()
                self.logger.info("✅ 설정 로드 완료")
        except Exception as e:
            self.logger.error(f"❌ 설정 로드 실패: {e}")

    def _load_default_configuration(self):
        """기본 설정 로드"""
        default_config = {
            "ui": {
                "theme": "auto",
                "language": "ko",
                "window_geometry": None,
                "window_state": None,
                "accessibility_enabled": False,
            },
            "services": {
                "tmdb_api": {
                    "api_key": "",
                    "base_url": "https://api.themoviedb.org/3",
                },
                "file_organization": {
                    "safe_mode": True,
                    "backup_before_operation": True,
                    "backup_strategy": "copy",
                },
            },
            "safety": {
                "default_mode": "normal",
                "backup_enabled": True,
                "confirmation_required": True,
                "can_interrupt": True,
            },
            "plugins": {
                "enabled_plugins": [],
                "plugin_directory": "plugins",
            },
        }

        for section, settings in default_config.items():
            for key, value in settings.items():
                if self._config_manager.get(section, key) is None:
                    self._config_manager.set(section, key, value)

    # 설정 관리
    def get_config(self, section: str, key: str, default: Any = None) -> Any:
        """설정 값 조회"""
        if not self._config_manager:
            return default

        try:
            value = self._config_manager.get(section, key, default)
            return value
        except Exception as e:
            self.logger.error(f"❌ 설정 조회 실패: {e}")
            return default

    def set_config(self, section: str, key: str, value: Any) -> bool:
        """설정 값 저장"""
        if not self._config_manager:
            return False

        try:
            self._config_manager.set(section, key, value)
            self.configuration_changed.emit(section, key, value)
            self.logger.info(f"✅ 설정 저장: {section}.{key} = {value}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 설정 저장 실패: {e}")
            return False

    def get_section(self, section: str) -> dict[str, Any]:
        """설정 섹션 조회"""
        if not self._config_manager:
            return {}

        try:
            # 실제 구현은 UnifiedConfigManager에 따라 달라질 수 있음
            # 여기서는 기본적인 구현만 제공
            return {}
        except Exception as e:
            self.logger.error(f"❌ 설정 섹션 조회 실패: {e}")
            return {}

    def set_section(self, section: str, settings: dict[str, Any]) -> bool:
        """설정 섹션 저장"""
        if not self._config_manager:
            return False

        try:
            for key, value in settings.items():
                self._config_manager.set(section, key, value)
                self.configuration_changed.emit(section, key, value)
            self.logger.info(f"✅ 설정 섹션 저장: {section}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 설정 섹션 저장 실패: {e}")
            return False

    def save_configuration(self) -> bool:
        """설정 저장"""
        if not self._config_manager:
            return False

        try:
            success = self._config_manager.save_config()
            if success:
                self.settings_saved.emit()
                self.logger.info("✅ 설정 저장 완료")
            return success
        except Exception as e:
            self.logger.error(f"❌ 설정 저장 실패: {e}")
            return False

    def load_configuration(self) -> bool:
        """설정 로드"""
        try:
            self._load_configuration()
            self.settings_loaded.emit()
            self.logger.info("✅ 설정 로드 완료")
            return True
        except Exception as e:
            self.logger.error(f"❌ 설정 로드 실패: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """설정을 기본값으로 초기화"""
        try:
            if self._config_manager:
                # 기본 설정 다시 로드
                self._load_default_configuration()
                self.save_configuration()
                self.logger.info("✅ 설정 기본값 초기화 완료")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ 설정 기본값 초기화 실패: {e}")
            return False

    # UI 설정 관리
    def get_ui_setting(self, key: str, default: Any = None) -> Any:
        """UI 설정 값 조회"""
        if not self._ui_settings:
            return default

        try:
            value = self._ui_settings.value(key, default)
            return value
        except Exception as e:
            self.logger.error(f"❌ UI 설정 조회 실패: {e}")
            return default

    def set_ui_setting(self, key: str, value: Any) -> bool:
        """UI 설정 값 저장"""
        if not self._ui_settings:
            return False

        try:
            self._ui_settings.setValue(key, value)
            self._ui_settings.sync()
            self.logger.info(f"✅ UI 설정 저장: {key} = {value}")
            return True
        except Exception as e:
            self.logger.error(f"❌ UI 설정 저장 실패: {e}")
            return False

    def save_ui_state(self, state_data: dict[str, Any]) -> bool:
        """UI 상태 저장"""
        try:
            for key, value in state_data.items():
                self.set_ui_setting(key, value)
            self.logger.info("✅ UI 상태 저장 완료")
            return True
        except Exception as e:
            self.logger.error(f"❌ UI 상태 저장 실패: {e}")
            return False

    def load_ui_state(self) -> dict[str, Any]:
        """UI 상태 로드"""
        try:
            state_data = {}
            if self._ui_settings:
                # 실제 구현에서는 필요한 키들을 미리 정의해야 함
                keys = [
                    "window_geometry",
                    "window_state",
                    "dock_layouts",
                    "tab_states",
                    "column_widths",
                    "splitter_ratios",
                    "search_terms",
                    "active_tab",
                    "ui_version",
                ]
                for key in keys:
                    value = self._ui_settings.value(key)
                    if value is not None:
                        state_data[key] = value
            self.logger.info("✅ UI 상태 로드 완료")
            return state_data
        except Exception as e:
            self.logger.error(f"❌ UI 상태 로드 실패: {e}")
            return {}

    def clear_ui_state(self) -> bool:
        """UI 상태 초기화"""
        try:
            if self._ui_settings:
                self._ui_settings.clear()
                self._ui_settings.sync()
                self.logger.info("✅ UI 상태 초기화 완료")
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ UI 상태 초기화 실패: {e}")
            return False

    # 플러그인 관리
    def load_plugin(self, plugin_path: str) -> bool:
        """플러그인 로드"""
        if not self._plugin_manager:
            return False

        try:
            success = self._plugin_manager.load_plugin(plugin_path)
            if success:
                plugin_name = Path(plugin_path).stem
                self.plugin_loaded.emit(plugin_name)
                self.logger.info(f"✅ 플러그인 로드 완료: {plugin_name}")
            return success
        except Exception as e:
            self.logger.error(f"❌ 플러그인 로드 실패: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """플러그인 언로드"""
        if not self._plugin_manager:
            return False

        try:
            success = self._plugin_manager.unload_plugin(plugin_name)
            if success:
                self.plugin_unloaded.emit(plugin_name)
                self.logger.info(f"✅ 플러그인 언로드 완료: {plugin_name}")
            return success
        except Exception as e:
            self.logger.error(f"❌ 플러그인 언로드 실패: {e}")
            return False

    def get_loaded_plugins(self) -> list[str]:
        """로드된 플러그인 목록"""
        if self._plugin_manager:
            return self._plugin_manager.get_loaded_plugins()
        return []

    def get_available_plugins(self) -> list[str]:
        """사용 가능한 플러그인 목록"""
        try:
            plugin_dir = Path(self.get_config("plugins", "plugin_directory", "plugins"))
            if plugin_dir.exists():
                return [f.stem for f in plugin_dir.glob("*.py") if f.is_file()]
            return []
        except Exception as e:
            self.logger.error(f"❌ 사용 가능한 플러그인 목록 조회 실패: {e}")
            return []

    # 설정 검증
    def validate_configuration(self) -> dict[str, list[str]]:
        """설정 검증"""
        validation_errors = {}

        try:
            # TMDB API 키 검증
            tmdb_api_key = self.get_config("services", "tmdb_api", {}).get("api_key", "")
            if not tmdb_api_key:
                validation_errors.setdefault("services", []).append(
                    "TMDB API 키가 설정되지 않았습니다"
                )

            # 플러그인 디렉토리 검증
            plugin_dir = self.get_config("plugins", "plugin_directory", "plugins")
            if not Path(plugin_dir).exists():
                validation_errors.setdefault("plugins", []).append(
                    f"플러그인 디렉토리가 존재하지 않습니다: {plugin_dir}"
                )

            # UI 설정 검증
            theme = self.get_config("ui", "theme", "auto")
            if theme not in ["auto", "light", "dark"]:
                validation_errors.setdefault("ui", []).append(f"잘못된 테마 설정: {theme}")

            language = self.get_config("ui", "language", "ko")
            if language not in ["ko", "en"]:
                validation_errors.setdefault("ui", []).append(f"지원되지 않는 언어: {language}")

            self.logger.info(f"✅ 설정 검증 완료: {len(validation_errors)}개 오류")
            return validation_errors
        except Exception as e:
            self.logger.error(f"❌ 설정 검증 실패: {e}")
            return {"general": [f"설정 검증 중 오류 발생: {e}"]}

    def fix_configuration_errors(self, errors: dict[str, list[str]]) -> bool:
        """설정 오류 수정"""
        try:
            fixed = True

            for section, error_list in errors.items():
                for error in error_list:
                    if "TMDB API 키" in error:
                        # 기본값으로 설정
                        self.set_config(
                            "services",
                            "tmdb_api",
                            {"api_key": "", "base_url": "https://api.themoviedb.org/3"},
                        )
                    elif "플러그인 디렉토리" in error:
                        # 기본 디렉토리 생성
                        plugin_dir = Path("plugins")
                        plugin_dir.mkdir(exist_ok=True)
                        self.set_config("plugins", "plugin_directory", "plugins")
                    elif "테마 설정" in error:
                        # 기본 테마로 설정
                        self.set_config("ui", "theme", "auto")
                    elif "언어" in error:
                        # 기본 언어로 설정
                        self.set_config("ui", "language", "ko")
                    else:
                        fixed = False

            if fixed:
                self.save_configuration()
                self.logger.info("✅ 설정 오류 수정 완료")
            else:
                self.logger.warning("⚠️ 일부 설정 오류를 수정할 수 없습니다")

            return fixed
        except Exception as e:
            self.logger.error(f"❌ 설정 오류 수정 실패: {e}")
            return False

    # 서비스 상태 관리
    def get_service_health_status(self) -> dict[str, Any]:
        """서비스 건강 상태 반환"""
        return {
            "config_manager_available": self._config_manager is not None,
            "plugin_manager_available": self._plugin_manager is not None,
            "ui_settings_available": self._ui_settings is not None,
            "loaded_plugins_count": len(self.get_loaded_plugins()),
            "available_plugins_count": len(self.get_available_plugins()),
            "validation_errors": len(self.validate_configuration()),
        }

    def export_configuration(self, file_path: str) -> bool:
        """설정 내보내기"""
        try:
            import json

            export_data = {
                "version": "1.0",
                "exported_at": self._get_current_timestamp(),
                "configuration": self._get_all_configuration(),
                "ui_state": self.load_ui_state(),
                "loaded_plugins": self.get_loaded_plugins(),
            }

            with Path(file_path).open("w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"✅ 설정 내보내기 완료: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 설정 내보내기 실패: {e}")
            return False

    def import_configuration(self, file_path: str) -> bool:
        """설정 가져오기"""
        try:
            import json

            with Path(file_path).open(encoding="utf-8") as f:
                import_data = json.load(f)

            # 설정 가져오기
            if "configuration" in import_data:
                for section, settings in import_data["configuration"].items():
                    self.set_section(section, settings)

            # UI 상태 가져오기
            if "ui_state" in import_data:
                self.save_ui_state(import_data["ui_state"])

            # 설정 저장
            self.save_configuration()

            self.logger.info(f"✅ 설정 가져오기 완료: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 설정 가져오기 실패: {e}")
            return False

    def _get_all_configuration(self) -> dict[str, Any]:
        """모든 설정 반환"""
        # 실제 구현에서는 UnifiedConfigManager의 모든 설정을 가져와야 함
        return {}

    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def shutdown(self):
        """서비스 종료"""
        try:
            self.logger.info("설정 서비스 종료 중...")

            # 설정 저장
            self.save_configuration()

            # 서비스 컴포넌트들 정리
            self._config_manager = None
            self._plugin_manager = None
            self._ui_settings = None

            self.logger.info("✅ 설정 서비스 종료 완료")
        except Exception as e:
            self.logger.error(f"❌ 설정 서비스 종료 실패: {e}")
