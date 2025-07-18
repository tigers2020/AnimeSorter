import os
from pathlib import Path
import yaml
from typing import Any, Dict, Optional

class ConfigManager:
    """설정 관리자"""
    
    # ⚠️ 보안 주의: 실제 배포 시에는 이 방법을 사용하지 마세요!
    # 대신 환경 변수나 암호화된 설정 파일을 사용하세요.
    
    # 방법 1: 직접 API 키 설정 (가장 간단하지만 보안상 위험)
    # DEFAULT_API_KEY = "your_actual_tmdb_api_key_here"
    
    # 방법 2: 환경 변수 사용 (권장)
    # DEFAULT_API_KEY = os.getenv('TMDB_API_KEY', '')
    
    # 방법 3: 기본값 (사용자가 설정에서 입력해야 함)
    DEFAULT_API_KEY = "c479f9ce20ccbcc06dbcce991a238120"
    
    DEFAULT_CONFIG = {
        "language": "ko-KR",
        "directories": {
            "source": "",
            "target": "",
            "cache": "./cache",
            "log": "./logs"
        },
        "file_formats": {
            "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
            "subtitle": [".srt", ".ass", ".smi", ".sub"]
        },
        "tmdb": {
            "api_key": "",  # 환경 변수나 기본값으로 설정됨
            "language": "ko-KR",
            "region": "KR",
            "timeout": 10,
            "include_adult": False
        },
        "folder_structure": {
            "tv_series": "{title}/시즌 {season}",
            "movies": "{title} ({year})",
            "episode_filename": "{title} - S{season:02d}E{episode:02d}"
        },
        "file_processing": {
            "overwrite_existing": False,
            "preserve_subtitles": True,
            "copy_instead_of_move": False,
            "clean_empty_folders": True
        },
        "ui": {
            "language": "ko",
            "theme": "light",
            "show_progress": True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        ConfigManager 초기화
        
        Args:
            config_path: 설정 파일 경로 (None이면 외부 파일 사용 안함)
        """
        self.config_path = Path(config_path) if config_path else None
        self.config = self.DEFAULT_CONFIG.copy()
        
        # API 키 설정 (환경 변수 우선, 없으면 기본값)
        self._setup_api_key()
        
        # 외부 파일이 지정된 경우에만 로드
        if self.config_path:
            self.load_config()
    
    def _setup_api_key(self):
        """API 키 설정 (환경 변수 우선)"""
        # 환경 변수에서 API 키 확인
        env_api_key = os.getenv('TMDB_API_KEY') or os.getenv('ANIMESORTER_API_KEY')
        
        if env_api_key:
            self.config["tmdb"]["api_key"] = env_api_key
        elif self.config["tmdb"]["api_key"] == "":
            # 환경 변수도 없고 기본값도 없으면 기본 API 키 사용
            self.config["tmdb"]["api_key"] = self.DEFAULT_API_KEY
        
    def load_config(self) -> None:
        """설정 파일 로드 (외부 파일이 있는 경우에만)"""
        if not self.config_path:
            return
            
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        self._update_recursive(self.config, loaded_config)
                        # 설정 파일 로드 후 API 키 재설정 (환경 변수 우선)
                        self._setup_api_key()
        except Exception as e:
            print(f"설정 파일 로드 중 오류 발생: {e}")
            
    def save_config(self) -> None:
        """현재 설정을 파일에 저장 (외부 파일이 있는 경우에만)"""
        if not self.config_path:
            return
            
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f"설정 파일 저장 중 오류 발생: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정값 가져오기
        
        Args:
            key: 설정 키 (점으로 구분된 경로)
            default: 기본값
            
        Returns:
            설정값 또는 기본값
        """
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> None:
        """
        설정값 설정
        
        Args:
            key: 설정 키 (점으로 구분된 경로)
            value: 설정값
        """
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        
    def _update_recursive(self, base: Dict, update: Dict) -> None:
        """
        딕셔너리 재귀적 업데이트
        
        Args:
            base: 기본 딕셔너리
            update: 업데이트할 딕셔너리
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._update_recursive(base[key], value)
            else:
                base[key] = value 