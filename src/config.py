"""
설정 관리 모듈

config.yaml 파일을 읽고 쓰는 기능 구현
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger


class Config:
    """설정 관리 클래스"""
    
    DEFAULT_CONFIG = {
        "api_key": "",  # TMDB API 키
        "language": "ko-KR",  # API 응답 언어
        "source_dir": str(Path.home() / "Downloads"),  # 소스 디렉토리
        "target_dir": str(Path.home() / "Videos" / "Anime"),  # 대상 디렉토리
        "folder_template": "{title} ({year})",  # 폴더 템플릿
        "keep_original_name": True,  # 원본 파일명 유지 여부
        "overwrite_existing": False,  # 기존 파일 덮어쓰기 여부
        "log_level": "INFO",  # 로그 레벨
    }
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Config 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        설정 파일 로드
        
        Returns:
            Dict[str, Any]: 설정 데이터
        """
        if not self.config_path.exists():
            logger.info(f"설정 파일이 없습니다. 기본 설정을 사용합니다: {self.config_path}")
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
            
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                
            # 필수 필드 누락 시 기본값으로 채우기
            for key, value in self.DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
                    
            return config
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return self.DEFAULT_CONFIG.copy()
            
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        설정 파일 저장
        
        Args:
            config: 저장할 설정 데이터
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                
            logger.info(f"설정 파일 저장 완료: {self.config_path}")
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정값 조회
        
        Args:
            key: 설정 키
            default: 키가 없을 경우 반환할 기본값
            
        Returns:
            Any: 설정값 또는 기본값
        """
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """
        설정값 변경
        
        Args:
            key: 설정 키
            value: 설정값
        """
        self.config[key] = value
        self._save_config(self.config)
        
    def reload(self) -> None:
        """설정 다시 로드"""
        self.config = self._load_config() 