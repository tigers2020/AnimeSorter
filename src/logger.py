"""
로깅 설정 모듈

로깅 초기화 및 설정 관리
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    app_name: str = "animesorter"
) -> logger:
    """
    애플리케이션 로거 설정
    
    Args:
        log_level: 로그 레벨 (기본값: INFO)
        log_file: 로그 파일 경로 (기본값: None, 지정되지 않으면 자동 생성)
        app_name: 애플리케이션 이름
    
    Returns:
        logger: 설정된 로거 인스턴스
    """
    # 기존 핸들러 제거
    logger.remove()
    
    # 로그 레벨 확인
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        log_level = "INFO"
    
    # 콘솔 핸들러 추가
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # 파일 핸들러 설정
    if log_file:
        file_path = Path(log_file)
    else:
        # 기본 로그 디렉토리 및 파일명 설정
        log_dir = Path.home() / f".{app_name}" / "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 현재 날짜를 파일명에 포함
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = log_dir / f"{app_name}_{today}.log"
    
    # 파일 핸들러 추가 (1MB, 최대 5개 백업)
    logger.add(
        str(file_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="1 MB",
        compression="zip",
        retention=5
    )
    
    logger.info(f"로거가 초기화 되었습니다. 로그 레벨: {log_level}, 로그 파일: {file_path}")
    
    return logger


# 기본 설정으로 로거 초기화
logger = setup_logger() 