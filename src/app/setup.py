"""
애플리케이션 초기화 및 DI Container 설정

애플리케이션 시작 시 필요한 의존성들을 등록합니다.
"""

import logging
import threading

from .container import get_container
from .events import TypedEventBus, set_event_bus
from .services import (
    BackgroundTaskService,
    FileScanService,
    IBackgroundTaskService,
    IFileScanService,
    IUIUpdateService,
    UIUpdateService,
)


def setup_application_services() -> None:
    """
    애플리케이션 서비스들을 DI Container에 등록합니다.

    이 함수는 애플리케이션 시작 시 한 번 호출되어야 합니다.
    """
    logger = logging.getLogger(__name__)
    container = get_container()

    try:
        # EventBus 등록 (Singleton)
        if not container.is_registered(TypedEventBus):
            container.register_singleton(TypedEventBus, TypedEventBus)
            logger.info("TypedEventBus가 Singleton으로 등록되었습니다")

        # BackgroundTaskService 등록 (Singleton)
        if not container.is_registered(IBackgroundTaskService):
            container.register_singleton(IBackgroundTaskService, BackgroundTaskService)
            logger.info("IBackgroundTaskService가 BackgroundTaskService로 등록되었습니다")

        # FileScanService 등록 (Singleton) - BackgroundTaskService 의존성 주입
        if not container.is_registered(IFileScanService):
            container.register_singleton(IFileScanService, FileScanService)
            logger.info("IFileScanService가 FileScanService로 등록되었습니다")

        # UIUpdateService 등록 (Singleton)
        if not container.is_registered(IUIUpdateService):
            container.register_singleton(IUIUpdateService, UIUpdateService)
            logger.info("IUIUpdateService가 UIUpdateService로 등록되었습니다")

        # 추가 서비스들은 여기에 등록
        # TODO: MetadataService, FileOperationService 등

        logger.info("애플리케이션 서비스 등록 완료")

    except Exception as e:
        logger.error(f"애플리케이션 서비스 등록 실패: {e}")
        raise


# 타입 변수
from typing import TypeVar

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

        # 1. 서비스 등록
        setup_application_services()

        # 2. DI Container에서 EventBus 인스턴스 가져오기
        container = get_container()
        event_bus = container.resolve(TypedEventBus)
        logger.info(f"EventBus 인스턴스 생성: {id(event_bus)}")

        # 3. DI Container의 EventBus를 전역 EventBus로 설정 (동기화)
        set_event_bus(event_bus)
        logger.info("DI Container EventBus를 전역 EventBus로 동기화 완료")

        # 4. 핵심 서비스들 인스턴스 생성 (eager loading)
        background_task_service = get_service(IBackgroundTaskService)
        logger.info(f"BackgroundTaskService 인스턴스 생성: {id(background_task_service)}")

        file_scan_service = get_service(IFileScanService)
        logger.info(f"FileScanService 인스턴스 생성: {id(file_scan_service)}")

        ui_update_service = get_service(IUIUpdateService)
        logger.info(f"UIUpdateService 인스턴스 생성: {id(ui_update_service)}")

        logger.info("애플리케이션 초기화 완료")

    except Exception as e:
        logger.error(f"애플리케이션 초기화 실패: {e}")
        raise


# 정리 완료 플래그
_cleanup_completed = False
_cleanup_lock = threading.Lock()


def cleanup_application() -> None:
    """
    애플리케이션 정리

    애플리케이션 종료 시 호출하여 리소스를 정리합니다.
    """
    global _cleanup_completed

    # 스레드 안전한 중복 호출 방지
    with _cleanup_lock:
        if _cleanup_completed:
            return

        # 즉시 플래그 설정하여 추가 호출 방지
        _cleanup_completed = True

    logger = logging.getLogger(__name__)

    try:
        logger.info("애플리케이션 정리 시작")

        # DI Container 정리 (EventBus도 함께 정리됨)
        container = get_container()
        if container:
            container.dispose()

        logger.info("애플리케이션 정리 완료")

    except Exception as e:
        logger.error(f"애플리케이션 정리 실패: {e}")
        # 정리 실패는 로그만 남기고 계속 진행
