"""
애플리케이션 초기화 및 DI Container 설정

애플리케이션 시작 시 필요한 의존성들을 등록합니다.
"""

import logging

logger = logging.getLogger(__name__)
import threading
from typing import TypeVar

from src.app.container import get_container
from src.app.events import get_event_bus
# Journal 시스템 제거됨
from src.app.preflight import IPreflightCoordinator, PreflightCoordinator
from src.app.safety import (IInterruptionManager, InterruptionManager,
                            ISafetyManager, SafetyConfiguration, SafetyManager)
from src.app.services import (BackgroundTaskService, FileScanService,
                              IBackgroundTaskService, IFileScanService,
                              IMediaDataService, ITMDBSearchService,
                              IUIUpdateService, MediaDataService,
                              TMDBSearchService, UIUpdateService)


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
        if not container.is_registered(IBackgroundTaskService):
            container.register_singleton(IBackgroundTaskService, BackgroundTaskService)
            logger.info("IBackgroundTaskService가 BackgroundTaskService로 등록되었습니다")
        if not container.is_registered(IFileScanService):
            container.register_singleton(IFileScanService, FileScanService)
            logger.info("IFileScanService가 FileScanService로 등록되었습니다")
        if not container.is_registered(IUIUpdateService):
            container.register_singleton(IUIUpdateService, UIUpdateService)
            logger.info("IUIUpdateService가 UIUpdateService로 등록되었습니다")
        if not container.is_registered(IMediaDataService):
            container.register_singleton(IMediaDataService, MediaDataService)
            logger.info("IMediaDataService가 MediaDataService로 등록되었습니다")
        if not container.is_registered(ITMDBSearchService):
            container.register_singleton(ITMDBSearchService, TMDBSearchService)
            logger.info("ITMDBSearchService가 TMDBSearchService로 등록되었습니다")
        # Journal 시스템 제거됨
        if not container.is_registered(ISafetyManager):

            def create_safety_manager():
                config = container.resolve(SafetyConfiguration)
                return SafetyManager(config)

            container.register_singleton(ISafetyManager, factory=create_safety_manager)
            logger.info("ISafetyManager가 SafetyManager로 등록되었습니다")
        if not container.is_registered(IPreflightCoordinator):
            container.register_singleton(IPreflightCoordinator, PreflightCoordinator)
            logger.info("IPreflightCoordinator가 PreflightCoordinator로 등록되었습니다")
        # Journal 시스템 제거됨
        if not container.is_registered(SafetyConfiguration):
            container.register_singleton(SafetyConfiguration, factory=lambda: SafetyConfiguration())
            logger.info("SafetyConfiguration이 등록되었습니다")
        # 미구현 스텁 코드 제거됨 - 필요시 실제 구현체로 교체
        if not container.is_registered(IInterruptionManager):
            container.register_singleton(IInterruptionManager, InterruptionManager)
            logger.info("IInterruptionManager가 InterruptionManager로 등록되었습니다")
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
        event_bus = get_event_bus()
        logger.info("EventBus 인스턴스 생성: %s", id(event_bus))
        logger.info("DI Container EventBus를 전역 EventBus로 동기화 완료")
        background_task_service = get_service(IBackgroundTaskService)
        logger.info(f"BackgroundTaskService 인스턴스 생성: {id(background_task_service)}")
        file_scan_service = get_service(IFileScanService)
        logger.info(f"FileScanService 인스턴스 생성: {id(file_scan_service)}")
        ui_update_service = get_service(IUIUpdateService)
        logger.info(f"UIUpdateService 인스턴스 생성: {id(ui_update_service)}")
        media_data_service = get_service(IMediaDataService)
        logger.info(f"MediaDataService 인스턴스 생성: {id(media_data_service)}")
        tmdb_search_service = get_service(ITMDBSearchService)
        logger.info(f"TMDBSearchService 인스턴스 생성: {id(tmdb_search_service)}")
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
