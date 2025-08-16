"""
설정 관리 모듈 - AnimeSorter

애플리케이션 설정을 관리하고 저장/로드하는 기능을 제공합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from PyQt5.QtCore import QObject, pyqtSignal


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
    window_geometry: Optional[str] = None
    table_column_widths: Optional[Dict[str, int]] = None
    last_source_directory: str = ""
    last_destination_directory: str = ""
    splitter_positions: Optional[List[int]] = None


class SettingsManager(QObject):
    """설정 관리자"""
    
    settingsChanged = pyqtSignal()
    
    def __init__(self, config_file: str = "animesorter_config.json"):
        """초기화"""
        super().__init__()
        self.config_file = Path(config_file)
        self.settings = AppSettings()
        self.load_settings()
    
    def load_settings(self) -> bool:
        """설정 파일에서 설정 로드"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 기존 설정과 병합
                for key, value in data.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
                        
                print(f"✅ 설정 로드 완료: {self.config_file}")
                return True
            else:
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
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=2)
                
            print(f"✅ 설정 저장 완료: {self.config_file}")
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
                self.settingsChanged.emit()
                return True
            else:
                print(f"⚠️ 알 수 없는 설정 키: {key}")
                return False
        except Exception as e:
            print(f"❌ 설정 변경 실패: {e}")
            return False
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """여러 설정을 한 번에 업데이트"""
        try:
            updated = False
            for key, value in new_settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
                    updated = True
                else:
                    print(f"⚠️ 알 수 없는 설정 키: {key}")
            
            if updated:
                self.settingsChanged.emit()
                
            return updated
            
        except Exception as e:
            print(f"❌ 설정 업데이트 실패: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """기본값으로 설정 초기화"""
        try:
            self.settings = AppSettings()
            self.settingsChanged.emit()
            return True
        except Exception as e:
            print(f"❌ 설정 초기화 실패: {e}")
            return False
    
    def validate_settings(self) -> Dict[str, str]:
        """설정 유효성 검사"""
        errors = {}
        
        # 필수 설정 검사
        if not self.settings.tmdb_api_key:
            errors['tmdb_api_key'] = "TMDB API 키가 필요합니다"
        
        if not self.settings.destination_root:
            errors['destination_root'] = "대상 디렉토리를 설정해야 합니다"
        elif not os.path.exists(self.settings.destination_root):
            errors['destination_root'] = "대상 디렉토리가 존재하지 않습니다"
        
        # 값 범위 검사
        if self.settings.auto_refresh_interval < 5:
            errors['auto_refresh_interval'] = "자동 새로고침 간격은 최소 5초여야 합니다"
        
        if self.settings.max_backup_count < 1:
            errors['max_backup_count'] = "최대 백업 개수는 최소 1개여야 합니다"
        
        return errors
    
    def export_settings(self, export_path: str) -> bool:
        """설정을 다른 파일로 내보내기"""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            settings_dict = asdict(self.settings)
            with open(export_file, 'w', encoding='utf-8') as f:
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
            
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 기존 설정과 병합
            for key, value in data.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)
            
            self.settingsChanged.emit()
            print(f"✅ 설정 가져오기 완료: {import_file}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 가져오기 실패: {e}")
            return False
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """설정 요약 반환"""
        return {
            'total_settings': len(asdict(self.settings)),
            'configured_settings': len([v for v in asdict(self.settings).values() if v]),
            'validation_errors': len(self.validate_settings()),
            'config_file_path': str(self.config_file),
            'config_file_exists': self.config_file.exists()
        }
