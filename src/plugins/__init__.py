"""
Plugin 모듈 - 확장 가능한 플러그인 시스템

이 모듈은 AnimeSorter의 플러그인 시스템을 제공합니다.
메타데이터 제공자나 파일 처리기 등을 확장할 수 있습니다.
"""

import logging

logger = logging.getLogger(__name__)
from .base import BasePlugin, PluginManager

__all__ = ["BasePlugin", "PluginManager"]
