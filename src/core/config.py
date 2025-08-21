"""
계층화된 설정 시스템

환경변수 > YAML > 기본값 우선순위를 가지는 설정 시스템입니다.
pydantic-settings를 사용하여 타입 안전성과 검증을 제공합니다.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """애플리케이션 설정 - pydantic-settings 기반"""

    model_config = SettingsConfigDict(
        env_file=".env",  # .env 파일 자동 로드 활성화
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # === 파일 정리 설정 ===
    destination_root: str = Field(
        default="", description="파일 정리의 기본 대상 디렉토리", env="ANIMESORTER_DESTINATION_ROOT"
    )

    organize_mode: str = Field(
        default="복사",
        description="파일 정리 모드: 복사, 이동, 하드링크",
        env="ANIMESORTER_ORGANIZE_MODE",
    )

    naming_scheme: str = Field(
        default="standard",
        description="파일명 생성 스키마: standard, minimal, detailed",
        env="ANIMESORTER_NAMING_SCHEME",
    )

    safe_mode: bool = Field(
        default=True,
        description="안전 모드 활성화 (파일 덮어쓰기 방지)",
        env="ANIMESORTER_SAFE_MODE",
    )

    backup_before_organize: bool = Field(
        default=False,
        description="파일 정리 전 백업 생성",
        env="ANIMESORTER_BACKUP_BEFORE_ORGANIZE",
    )

    # === 파싱 설정 ===
    prefer_anitopy: bool = Field(
        default=False, description="anitopy를 우선 사용", env="ANIMESORTER_PREFER_ANITOPY"
    )

    fallback_parser: str = Field(
        default="FileParser",
        description="대체 파서: GuessIt, Custom, FileParser",
        env="ANIMESORTER_FALLBACK_PARSER",
    )

    realtime_monitoring: bool = Field(
        default=False, description="실시간 모니터링 활성화", env="ANIMESORTER_REALTIME_MONITORING"
    )

    auto_refresh_interval: int = Field(
        default=30, description="자동 새로고침 간격 (초)", env="ANIMESORTER_AUTO_REFRESH_INTERVAL"
    )

    # === TMDB 설정 ===
    tmdb_api_key: str = Field(default="", description="TMDB API 키", env="TMDB_API_KEY")

    tmdb_language: str = Field(
        default="ko-KR",
        description="TMDB 언어 설정: ko-KR, en-US, ja-JP",
        env="ANIMESORTER_TMDB_LANGUAGE",
    )

    # === 고급 설정 ===
    show_advanced_options: bool = Field(
        default=False, description="고급 옵션 표시", env="ANIMESORTER_SHOW_ADVANCED_OPTIONS"
    )

    log_level: str = Field(
        default="INFO",
        description="로그 레벨: DEBUG, INFO, WARNING, ERROR",
        env="ANIMESORTER_LOG_LEVEL",
    )

    log_to_file: bool = Field(
        default=False, description="파일로 로그 저장", env="ANIMESORTER_LOG_TO_FILE"
    )

    # === 백업 설정 ===
    backup_location: str = Field(
        default="", description="백업 파일 저장 위치", env="ANIMESORTER_BACKUP_LOCATION"
    )

    max_backup_count: int = Field(
        default=10, description="최대 백업 파일 개수", env="ANIMESORTER_MAX_BACKUP_COUNT"
    )

    # === GUI 상태 (세션별) ===
    window_geometry: str | None = Field(
        default=None, description="윈도우 기하학 정보", env="ANIMESORTER_WINDOW_GEOMETRY"
    )

    table_column_widths: dict[str, int] | None = Field(
        default=None, description="테이블 컬럼 너비", env="ANIMESORTER_TABLE_COLUMN_WIDTHS"
    )

    last_source_directory: str = Field(
        default="", description="마지막 소스 디렉토리", env="ANIMESORTER_LAST_SOURCE_DIRECTORY"
    )

    last_destination_directory: str = Field(
        default="", description="마지막 대상 디렉토리", env="ANIMESORTER_LAST_DESTINATION_DIRECTORY"
    )

    last_source_files: list[str] | None = Field(
        default=None, description="마지막 소스 파일 목록", env="ANIMESORTER_LAST_SOURCE_FILES"
    )

    splitter_positions: list[int] | None = Field(
        default=None, description="스플리터 위치", env="ANIMESORTER_SPLITTER_POSITIONS"
    )

    # === 세션 관리 ===
    remember_last_session: bool = Field(
        default=True, description="마지막 세션 기억", env="ANIMESORTER_REMEMBER_LAST_SESSION"
    )

    # === 검증 메서드 ===
    @field_validator("organize_mode")
    @classmethod
    def validate_organize_mode(cls, v: str) -> str:
        """파일 정리 모드 검증"""
        valid_modes = ["복사", "이동", "하드링크"]
        if v not in valid_modes:
            raise ValueError(f"organize_mode는 다음 중 하나여야 합니다: {valid_modes}")
        return v

    @field_validator("naming_scheme")
    @classmethod
    def validate_naming_scheme(cls, v: str) -> str:
        """파일명 스키마 검증"""
        valid_schemes = ["standard", "minimal", "detailed"]
        if v not in valid_schemes:
            raise ValueError(f"naming_scheme는 다음 중 하나여야 합니다: {valid_schemes}")
        return v

    @field_validator("fallback_parser")
    @classmethod
    def validate_fallback_parser(cls, v: str) -> str:
        """대체 파서 검증"""
        valid_parsers = ["GuessIt", "Custom", "FileParser"]
        if v not in valid_parsers:
            raise ValueError(f"fallback_parser는 다음 중 하나여야 합니다: {valid_parsers}")
        return v

    @field_validator("tmdb_language")
    @classmethod
    def validate_tmdb_language(cls, v: str) -> str:
        """TMDB 언어 검증"""
        valid_languages = ["ko-KR", "en-US", "ja-JP"]
        if v not in valid_languages:
            raise ValueError(f"tmdb_language는 다음 중 하나여야 합니다: {valid_languages}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """로그 레벨 검증"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if v not in valid_levels:
            raise ValueError(f"log_level은 다음 중 하나여야 합니다: {valid_levels}")
        return v

    @field_validator("auto_refresh_interval")
    @classmethod
    def validate_auto_refresh_interval(cls, v: int) -> int:
        """자동 새로고침 간격 검증"""
        if v < 5:
            raise ValueError("auto_refresh_interval은 최소 5초여야 합니다")
        return v

    @field_validator("max_backup_count")
    @classmethod
    def validate_max_backup_count(cls, v: int) -> int:
        """최대 백업 개수 검증"""
        if v < 1:
            raise ValueError("max_backup_count는 최소 1개여야 합니다")
        return v


class ConfigManager:
    """계층화된 설정 관리자"""

    def __init__(self, config_dir: Path | None = None):
        """초기화"""
        if config_dir is None:
            config_dir = Path.home() / ".animesorter"

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 설정 파일 경로들
        # 프로젝트 루트의 .env 파일을 우선 사용
        project_root = Path.cwd()
        self.env_file = project_root / ".env"
        self.yaml_file = config_dir / "config.yaml"
        self.json_file = config_dir / "config.json"

        # 설정 인스턴스
        self._config: AppConfig | None = None

        # 설정 변경 콜백
        self._change_callbacks: list[callable] = []

    @property
    def config(self) -> AppConfig:
        """설정 인스턴스 반환 (지연 로딩)"""
        if self._config is None:
            self._load_config()
        return self._config

    def _load_config(self) -> None:
        """설정 로드 (환경변수 > YAML > 기본값)"""
        try:
            # 환경변수 파일이 있으면 로드 (안전하게)
            if self.env_file.exists():
                try:
                    # .env 파일을 직접 읽어서 환경변수로 설정
                    self._load_env_file_safely()
                except Exception as e:
                    print(f"⚠️ .env 파일 로드 실패 (무시됨): {e}")

            # 설정 로드
            self._config = AppConfig()

            # YAML 파일이 있으면 병합
            if self.yaml_file.exists():
                self._merge_yaml_config()

            print("✅ 계층화된 설정 로드 완료")
            print(f"  환경변수: {len([k for k in os.environ if k.startswith('ANIMESORTER_')])}개")
            print(f"  YAML 파일: {'있음' if self.yaml_file.exists() else '없음'}")
            print("  기본값: 사용됨")

        except Exception as e:
            print(f"❌ 설정 로드 실패: {e}")
            # 기본값으로 폴백
            self._config = AppConfig()

    def _load_env_file_safely(self) -> None:
        """안전하게 .env 파일 로드"""
        try:
            with self.env_file.open(encoding="utf-8") as f:
                for _line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # 주석이나 빈 줄 무시
                    if not line or line.startswith("#"):
                        continue

                    # KEY=VALUE 형식 파싱
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # 따옴표 제거
                        if (
                            value.startswith('"')
                            and value.endswith('"')
                            or value.startswith("'")
                            and value.endswith("'")
                        ):
                            value = value[1:-1]

                        # 환경변수로 설정
                        if key and not key.startswith("#"):
                            os.environ[key] = value
                            print(f"  환경변수 설정: {key}={value}")

        except UnicodeDecodeError:
            # UTF-8로 읽을 수 없는 경우 다른 인코딩 시도
            for encoding in ["cp1252", "latin-1", "iso-8859-1"]:
                try:
                    with self.env_file.open(encoding=encoding) as f:
                        for _line_num, line in enumerate(f, 1):
                            line = line.strip()

                            if not line or line.startswith("#"):
                                continue

                            if "=" in line:
                                key, value = line.split("=", 1)
                                key = key.strip()
                                value = value.strip()

                                if (
                                    value.startswith('"')
                                    and value.endswith('"')
                                    or value.startswith("'")
                                    and value.endswith("'")
                                ):
                                    value = value[1:-1]

                                if key and not key.startswith("#"):
                                    os.environ[key] = value
                                    print(f"  환경변수 설정 ({encoding}): {key}={value}")

                    print(f"✅ .env 파일을 {encoding} 인코딩으로 로드 성공")
                    return

                except Exception:
                    continue

            print("⚠️ .env 파일을 어떤 인코딩으로도 읽을 수 없습니다")
        except Exception as e:
            print(f"⚠️ .env 파일 로드 중 오류: {e}")

    def _merge_yaml_config(self) -> None:
        """YAML 설정 파일 병합"""
        try:
            import yaml

            with self.yaml_file.open(encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            if yaml_data:
                # YAML 데이터를 환경변수로 설정 (pydantic-settings가 자동으로 처리)
                for key, value in yaml_data.items():
                    env_key = f"ANIMESORTER_{key.upper()}"
                    if env_key not in os.environ:
                        os.environ[env_key] = str(value)

                print(f"  YAML 설정 병합: {len(yaml_data)}개 항목")

        except ImportError:
            print("  ⚠️ PyYAML이 설치되지 않아 YAML 설정을 로드할 수 없습니다")
        except Exception as e:
            print(f"  ❌ YAML 설정 병합 실패: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기"""
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any) -> bool:
        """설정 값 설정"""
        try:
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                self._notify_change(key, value)
                return True
            print(f"⚠️ 알 수 없는 설정 키: {key}")
            return False
        except Exception as e:
            print(f"❌ 설정 변경 실패: {e}")
            return False

    def update(self, updates: dict[str, Any]) -> bool:
        """여러 설정을 한 번에 업데이트"""
        try:
            updated = False
            for key, value in updates.items():
                if self.set(key, value):
                    updated = True

            return updated
        except Exception as e:
            print(f"❌ 설정 업데이트 실패: {e}")
            return False

    def save_to_yaml(self) -> bool:
        """현재 설정을 YAML 파일로 저장"""
        try:
            import yaml

            # 설정을 딕셔너리로 변환
            config_dict = self.config.model_dump()

            # None 값과 빈 문자열 제거
            config_dict = {k: v for k, v in config_dict.items() if v is not None and v != ""}

            with self.yaml_file.open("w", encoding="utf-8") as f:
                yaml.dump(
                    config_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False
                )

            print(f"✅ YAML 설정 저장 완료: {self.yaml_file}")
            return True

        except ImportError:
            print("❌ PyYAML이 설치되지 않아 YAML 저장을 할 수 없습니다")
            return False
        except Exception as e:
            print(f"❌ YAML 설정 저장 실패: {e}")
            return False

    def save_to_json(self) -> bool:
        """현재 설정을 JSON 파일로 저장"""
        try:
            config_dict = self.config.model_dump()

            # None 값과 빈 문자열 제거
            config_dict = {k: v for k, v in config_dict.items() if v is not None and v != ""}

            with self.json_file.open("w", encoding="utf-8") as f:
                import json

                json.dump(config_dict, f, ensure_ascii=False, indent=2)

            print(f"✅ JSON 설정 저장 완료: {self.json_file}")
            return True

        except Exception as e:
            print(f"❌ JSON 설정 저장 실패: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """기본값으로 설정 초기화"""
        try:
            self._config = AppConfig()
            self._notify_change("__all__", None)
            return True
        except Exception as e:
            print(f"❌ 설정 초기화 실패: {e}")
            return False

    def validate(self) -> dict[str, str]:
        """설정 유효성 검사"""
        try:
            # pydantic 검증 실행
            self.config.model_validate(self.config.model_dump())
            return {}
        except Exception as e:
            return {"validation_error": str(e)}

    def get_source_info(self) -> dict[str, Any]:
        """설정 소스 정보 반환"""
        return {
            "env_file": str(self.env_file) if self.env_file.exists() else None,
            "yaml_file": str(self.yaml_file) if self.yaml_file.exists() else None,
            "json_file": str(self.json_file) if self.json_file.exists() else None,
            "env_vars": len([k for k in os.environ if k.startswith("ANIMESORTER_")]),
            "config_dir": str(self.config_dir),
        }

    def add_change_callback(self, callback: callable) -> None:
        """설정 변경 콜백 추가"""
        self._change_callbacks.append(callback)

    def _notify_change(self, key: str, value: Any) -> None:
        """설정 변경 알림"""
        for callback in self._change_callbacks:
            try:
                callback(key, value)
            except Exception as e:
                print(f"⚠️ 설정 변경 콜백 실행 실패: {e}")

    def reload(self) -> None:
        """설정 재로드"""
        self._config = None
        self._load_config()
        self._notify_change("__reload__", None)


# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()
