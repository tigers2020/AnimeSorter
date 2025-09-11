"""
애플리케이션 초기화 및 DI Container 설정

애플리케이션 시작 시 필요한 의존성들을 등록합니다.
"""

import logging

logger = logging.getLogger(__name__)
import threading
from typing import TypeVar

from src.app.container import get_container
# Journal 시스템 제거됨
from src.app.preflight import IPreflightCoordinator, PreflightCoordinator
from src.app.undo_redo import UndoRedoConfiguration
from src.core.unified_event_system import get_unified_event_bus

# Safety 모듈은 새로운 서비스 아키텍처로 대체됨
# from src.app.safety import ...


def setup_application_services() -> None:
    """
    애플리케이션 서비스들을 DI Container에 등록합니다.

    이 함수는 애플리케이션 시작 시 한 번 호출되어야 합니다.
    """
    logger = logging.getLogger(__name__)
    container = get_container()
    try:
        # EventBus는 get_event_bus()를 통해 직접 사용
        logger.info("EventBus는 get_event_bus()를 통해 직접 사용됩니다")
        # 제거된 서비스들 - 필요시 실제 구현체로 교체
        # BackgroundTaskService, UIUpdateService, MediaDataService는 제거됨
        # Journal 시스템 제거됨
        if not container.is_registered(IPreflightCoordinator):
            container.register_singleton(IPreflightCoordinator, PreflightCoordinator)
            logger.info("IPreflightCoordinator가 PreflightCoordinator로 등록되었습니다")
        # 누락된 의존성들 등록
        from src.app.commands import CommandInvoker, ICommandInvoker
        from src.app.undo_redo import IUndoRedoManager, UndoRedoManager

        if not container.is_registered(ICommandInvoker):
            container.register_singleton(ICommandInvoker, CommandInvoker)
            logger.info("ICommandInvoker가 CommandInvoker로 등록되었습니다")

        if not container.is_registered(IUndoRedoManager):
            container.register_singleton(IUndoRedoManager, UndoRedoManager)
            logger.info("IUndoRedoManager가 UndoRedoManager로 등록되었습니다")

        # UndoRedoConfiguration 등록
        if not container.is_registered(UndoRedoConfiguration):
            container.register_singleton(UndoRedoConfiguration, UndoRedoConfiguration)
            logger.info("UndoRedoConfiguration이 등록되었습니다")

        # Safety 관련 서비스들은 새로운 서비스 아키텍처로 대체됨
        # ApplicationFacade를 통해 접근
        logger.info("애플리케이션 서비스 등록 완료")
    except Exception as e:
        logger.error(f"애플리케이션 서비스 등록 실패: {e}")
        raise


T = TypeVar("T")


def get_service(service_type: type[T]) -> T:
    """
    DI Container에서 서비스를 가져오는 편의 함수

    Args:
        service_type: 가져올 서비스 타입

    Returns:
        서비스 인스턴스
    """
    container = get_container()
    return container.resolve(service_type)


def initialize_application() -> None:
    """
    애플리케이션 전체 초기화

    메인 진입점에서 호출하여 모든 의존성을 설정합니다.
    """
    logger = logging.getLogger(__name__)
    try:
        logger.info("애플리케이션 초기화 시작")
        setup_application_services()
        event_bus = get_unified_event_bus()
        logger.info("EventBus 인스턴스 생성: %s", id(event_bus))
        logger.info("DI Container EventBus를 전역 EventBus로 동기화 완료")
        # 제거된 서비스들 - 필요시 실제 구현체로 교체
        # BackgroundTaskService, UIUpdateService, MediaDataService는 제거됨
        logger.info("애플리케이션 초기화 완료")
    except Exception as e:
        logger.error(f"애플리케이션 초기화 실패: {e}")
        raise


_cleanup_completed = False
_cleanup_lock = threading.Lock()


def cleanup_application() -> None:
    """
    애플리케이션 정리

    애플리케이션 종료 시 호출하여 리소스를 정리합니다.
    """
    global _cleanup_completed
    with _cleanup_lock:
        if _cleanup_completed:
            return
        _cleanup_completed = True
    logger = logging.getLogger(__name__)
    try:
        logger.info("애플리케이션 정리 시작")
        container = get_container()
        if container:
            container.dispose()
        logger.info("애플리케이션 정리 완료")
    except Exception as e:
        logger.error(f"애플리케이션 정리 실패: {e}")
