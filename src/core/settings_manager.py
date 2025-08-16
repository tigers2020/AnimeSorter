"""
설정 관리 모듈 - AnimeSorter의 설정 저장 및 로드

이 모듈은 애플리케이션의 다양한 설정을 JSON 파일에 저장하고
불러오는 기능을 제공합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging


@dataclass
class AppSettings:
    """애플리케이션 설정 데이터 클래스"""
    # 파일 정리 설정
    destination_root: str = ""
    organize_mode: str = "복사"  # "복사", "이동", "하드링크"
    naming_scheme: str = "standard"  # "standard", "minimal", "detailed"
    safe_mode: bool = True
    backup_enabled: bool = False
    backup_location: str = ""
    max_backups: int = 5
    
    # 파서 설정
    prefer_anitopy: bool = True
    fallback_parser: str = "GuessIt"  # "GuessIt", "Custom"
    
    # TMDB 설정
    tmdb_api_key: str = ""
    tmdb_language: str = "ko-KR"
    
    # UI 설정
    realtime_monitoring: bool = True
    auto_refresh_interval: int = 30  # 초
    show_advanced_options: bool = False
    ui_theme: str = "Dark"  # "Dark", "Light"
    log_level: str = "INFO"  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    file_logging_enabled: bool = False
    
    # GUI 상태 저장 (프로그램 재시작 시 복원)
    last_source_directory: str = ""  # 마지막으로 선택한 소스 디렉토리
    last_source_files: list = None  # 마지막으로 선택한 소스 파일들
    last_destination_directory: str = ""  # 마지막으로 선택한 대상 디렉토리
    window_geometry: str = ""  # 윈도우 크기와 위치 (x,y,width,height)
    window_state: str = ""  # 윈도우 상태 (최대화, 최소화 등)
    splitter_positions: list = None  # 스플리터 위치들
    table_column_widths: dict = None  # 테이블 컬럼 너비들
    table_sort_column: int = 0  # 정렬된 컬럼 인덱스
    table_sort_order: str = "ascending"  # 정렬 순서
    
    # 사용자 선호 설정
    auto_start_scan: bool = False  # 프로그램 시작 시 자동 스캔
    remember_last_session: bool = True  # 마지막 세션 기억
    show_file_preview: bool = True  # 파일 미리보기 표시
    show_parsing_details: bool = False  # 파싱 상세 정보 표시
    confirm_before_organize: bool = True  # 정리 전 확인
    show_progress_dialog: bool = True  # 진행 상황 다이얼로그 표시
    
    # 고급 설정
    settings_file_path: str = ""  # This will be set by the manager, not user configurable directly


class SettingsManager:
    """설정 관리자"""
    
    def __init__(self, config_dir: str = ".animesorter"):
        """
        SettingsManager 초기화
        
        Args:
            config_dir: 설정 파일이 저장될 디렉토리
        """
        self.config_dir = Path(config_dir)
        self.settings_file = self.config_dir / "settings.json"
        self.logger = logging.getLogger(__name__)
        
        # 기본 설정
        self.settings = AppSettings()
        
        # 설정 디렉토리 생성
        self.config_dir.mkdir(exist_ok=True)
        
        # 기존 설정 로드
        self.load_settings()
    
    def load_settings(self) -> bool:
        """설정 파일에서 설정 로드"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 기존 설정을 현재 설정에 병합
                for key, value in data.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
                
                self.logger.info("설정을 성공적으로 로드했습니다")
                return True
            else:
                self.logger.info("설정 파일이 없습니다. 기본 설정을 사용합니다")
                return False
                
        except Exception as e:
            self.logger.error(f"설정 로드 실패: {e}")
            return False
    
    def save_settings(self) -> bool:
        """현재 설정을 파일에 저장"""
        try:
            # 설정을 딕셔너리로 변환
            settings_dict = asdict(self.settings)
            
            # 설정 파일에 저장
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info("설정을 성공적으로 저장했습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 저장 실패: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """특정 설정 값 반환"""
        return getattr(self.settings, key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """특정 설정 값 설정"""
        try:
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                return True
            else:
                self.logger.warning(f"알 수 없는 설정 키: {key}")
                return False
        except Exception as e:
            self.logger.error(f"설정 값 설정 실패: {key} = {value}, 오류: {e}")
            return False
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """여러 설정을 한 번에 업데이트"""
        try:
            for key, value in new_settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
                else:
                    self.logger.warning(f"알 수 없는 설정 키: {key}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"설정 업데이트 실패: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """설정을 기본값으로 초기화"""
        try:
            self.settings = AppSettings()
            self.logger.info("설정을 기본값으로 초기화했습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 초기화 실패: {e}")
            return False
    
    def export_settings(self, export_path: str) -> bool:
        """설정을 다른 파일로 내보내기"""
        try:
            export_file = Path(export_path)
            settings_dict = asdict(self.settings)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"설정을 {export_path}로 내보냈습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 내보내기 실패: {e}")
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """다른 파일에서 설정 가져오기"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                self.logger.error(f"가져올 파일이 존재하지 않습니다: {import_path}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 기존 설정을 가져온 설정으로 병합
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
            
            self.logger.info(f"{import_path}에서 설정을 가져왔습니다")
            return True
            
        except Exception as e:
            self.logger.error(f"설정 가져오기 실패: {e}")
            return False
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """설정 요약 반환"""
        return {
            'config_file': str(self.settings_file),
            'total_settings': len(asdict(self.settings)),
            'modified_settings': self._get_modified_settings()
        }
    
    def _get_modified_settings(self) -> Dict[str, Any]:
        """기본값과 다른 설정들 반환"""
        default_settings = AppSettings()
        current_settings = asdict(self.settings)
        default_dict = asdict(default_settings)
        
        modified = {}
        for key, value in current_settings.items():
            if value != default_dict[key]:
                modified[key] = {
                    'current': value,
                    'default': default_dict[key]
                }
        
        return modified
    
    def validate_settings(self) -> Dict[str, str]:
        """설정 유효성 검사"""
        errors = {}
        
        # 대상 디렉토리 검사
        if self.settings.destination_root:
            dest_path = Path(self.settings.destination_root)
            if not dest_path.exists():
                errors['destination_root'] = "대상 디렉토리가 존재하지 않습니다"
            elif not dest_path.is_dir():
                errors['destination_root'] = "대상 경로가 디렉토리가 아닙니다"
            elif not os.access(dest_path, os.W_OK):
                errors['destination_root'] = "대상 디렉토리에 쓰기 권한이 없습니다"
        
        # TMDB API 키 검사
        if self.settings.tmdb_api_key and len(self.settings.tmdb_api_key) < 10:
            errors['tmdb_api_key'] = "TMDB API 키가 너무 짧습니다"
        
        # 백업 위치 검사
        if self.settings.backup_location:
            backup_path = Path(self.settings.backup_location)
            if not backup_path.exists():
                errors['backup_location'] = "백업 위치가 존재하지 않습니다"
            elif not backup_path.is_dir():
                errors['backup_location'] = "백업 위치가 디렉토리가 아닙니다"
        
        return errors
