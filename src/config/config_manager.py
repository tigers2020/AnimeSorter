import os
from pathlib import Path
import yaml
from typing import Any, Dict, Optional

class ConfigManager:
    """설정 관리자"""
    
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
            "api_key": "",
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
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        ConfigManager 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = Path(config_path)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
        
    def load_config(self) -> None:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        self._update_recursive(self.config, loaded_config)
        except Exception as e:
            print(f"설정 파일 로드 중 오류 발생: {e}")
            
    def save_config(self) -> None:
        """현재 설정을 파일에 저장"""
        try:
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