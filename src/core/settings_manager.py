"""
설정 관리 모듈 - AnimeSorter

애플리케이션 설정을 관리하고 저장/로드하는 기능을 제공합니다.
기존 SettingsManager와 새로운 ConfigManager를 통합하여
계층화된 설정 시스템을 제공합니다.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

# 새로운 계층화된 설정 시스템 import
try:
    from .config import config_manager

    NEW_CONFIG_AVAILABLE = True
except ImportError:
    NEW_CONFIG_AVAILABLE = False


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
    """설정 관리자"""

    settings_changed = pyqtSignal()

    def __init__(self, config_file: str = "animesorter_config.json"):
        """초기화"""
        super().__init__()
        self.config_file = Path(config_file)
        self.settings_file = str(self.config_file)  # settings_file 속성 추가
        self.settings = AppSettings()

        # 새로운 계층화된 설정 시스템이 사용 가능한 경우
        if NEW_CONFIG_AVAILABLE:
            # 설정 변경 콜백 등록
            config_manager.add_change_callback(self._on_config_changed)

        self.load_settings()

    def load_settings(self) -> bool:
        """설정 파일에서 설정 로드"""
        try:
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
            # 설정 디렉토리 생성
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            # 설정을 딕셔너리로 변환
            settings_dict = asdict(self.settings)

            # None 값 제거
            settings_dict = {k: v for k, v in settings_dict.items() if v is not None}

            # UTF-8 인코딩으로 저장하고 ASCII 문자 변환 방지
            with self.config_file.open("w", encoding="utf-8", newline="\n") as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=2, separators=(",", ": "))

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
            if hasattr(self.settings, key):
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

        # 새로운 설정 시스템 정보 추가
        if NEW_CONFIG_AVAILABLE:
            summary.update(
                {
                    "new_config_available": True,
                    "config_source_info": config_manager.get_source_info(),
                    "new_config_validation": config_manager.validate(),
                }
            )
        else:
            summary["new_config_available"] = False

        return summary

    def _on_config_changed(self, key: str, value: Any) -> None:
        """새로운 설정 시스템에서 설정이 변경되었을 때 호출"""
        try:
            if key == "__reload__":
                # 전체 설정 재로드
                self._sync_with_new_config()
            elif key == "__all__":
                # 기본값으로 초기화
                self._sync_with_new_config()
            else:
                # 특정 설정 동기화
                self._sync_specific_setting(key, value)
        except Exception as e:
            print(f"⚠️ 설정 동기화 실패: {e}")

    def _sync_with_new_config(self) -> None:
        """새로운 설정 시스템과 동기화"""
        if not NEW_CONFIG_AVAILABLE:
            return

        try:
            new_config = config_manager.config
            if new_config is None:
                return

            # 주요 설정들을 동기화
            if new_config.destination_root != self.settings.destination_root:
                self.settings.destination_root = new_config.destination_root

            if new_config.organize_mode != self.settings.organize_mode:
                self.settings.organize_mode = new_config.organize_mode

            if new_config.tmdb_api_key != self.settings.tmdb_api_key:
                self.settings.tmdb_api_key = new_config.tmdb_api_key

            if new_config.log_level != self.settings.log_level:
                self.settings.log_level = new_config.log_level

            # 설정 변경 시그널 발생
            self.settings_changed.emit()
            print("✅ 새로운 설정 시스템과 동기화 완료")

        except Exception as e:
            print(f"❌ 설정 동기화 실패: {e}")

    def _sync_specific_setting(self, key: str, value: Any) -> None:
        """특정 설정 동기화"""
        if not NEW_CONFIG_AVAILABLE:
            return

        try:
            # 키 매핑 (새로운 설정 키 -> 기존 설정 키)
            key_mapping = {
                "destination_root": "destination_root",
                "organize_mode": "organize_mode",
                "tmdb_api_key": "tmdb_api_key",
                "log_level": "log_level",
                "safe_mode": "safe_mode",
                "backup_before_organize": "backup_before_organize",
            }

            if key in key_mapping:
                old_key = key_mapping[key]
                if hasattr(self.settings, old_key):
                    old_value = getattr(self.settings, old_key)
                    setattr(self.settings, old_key, value)
                    print(f"✅ 설정 동기화: {old_key} = {old_value} -> {value}")

                    # 설정 변경 시그널 발생
                    self.settings_changed.emit()

        except Exception as e:
            print(f"❌ 특정 설정 동기화 실패: {e}")

    # === 새로운 설정 시스템 메서드들 ===

    def use_new_config_system(self) -> bool:
        """새로운 설정 시스템 사용 여부"""
        return NEW_CONFIG_AVAILABLE

    def get_new_config(self) -> Any:
        """새로운 설정 시스템의 설정 반환"""
        if NEW_CONFIG_AVAILABLE:
            return config_manager.config
        return None

    def set_new_config(self, key: str, value: Any) -> bool:
        """새로운 설정 시스템에 설정 값 설정"""
        if NEW_CONFIG_AVAILABLE:
            return config_manager.set(key, value)
        return False

    def save_new_config_to_yaml(self) -> bool:
        """새로운 설정을 YAML 파일로 저장"""
        if NEW_CONFIG_AVAILABLE:
            return config_manager.save_to_yaml()
        return False

    def reload_new_config(self) -> None:
        """새로운 설정 시스템 재로드"""
        if NEW_CONFIG_AVAILABLE:
            config_manager.reload()
