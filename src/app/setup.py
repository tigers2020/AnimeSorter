"""
애플리케이션 초기화 및 DI Container 설정

애플리케이션 시작 시 필요한 의존성들을 등록합니다.
"""

import logging
import threading
from typing import TypeVar

from .commands import ICommandInvoker
from .container import get_container
from .events import TypedEventBus, set_event_bus
from .journal import (IJournalManager, IRollbackEngine, JournalConfiguration,
                      JournalManager)
from .preflight import IPreflightCoordinator, PreflightCoordinator
from .safety import (IBackupManager, IConfirmationManager,
                     IInterruptionManager, InterruptionManager, ISafetyManager,
                     SafetyConfiguration, SafetyManager)
from .services import (BackgroundTaskService, FileOrganizationService,
                       FileScanService, IBackgroundTaskService,
                       IFileOrganizationService, IFileScanService,
                       IMediaDataService, ITMDBSearchService, IUIUpdateService,
                       MediaDataService, TMDBSearchService, UIUpdateService)
from .undo_redo import IUndoRedoManager


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

        # FileOrganizationService 등록 (Singleton)
        if not container.is_registered(IFileOrganizationService):
            container.register_singleton(IFileOrganizationService, FileOrganizationService)
            logger.info("IFileOrganizationService가 FileOrganizationService로 등록되었습니다")

        # MediaDataService 등록 (Singleton)
        if not container.is_registered(IMediaDataService):
            container.register_singleton(IMediaDataService, MediaDataService)
            logger.info("IMediaDataService가 MediaDataService로 등록되었습니다")

        # TMDBSearchService 등록 (Singleton)
        if not container.is_registered(ITMDBSearchService):
            container.register_singleton(ITMDBSearchService, TMDBSearchService)
            logger.info("ITMDBSearchService가 TMDBSearchService로 등록되었습니다")

        # SafetyManager 등록 (Singleton)
        if not container.is_registered(ISafetyManager):

            def create_safety_manager():
                config = container.resolve(SafetyConfiguration)
                return SafetyManager(config)

            container.register_singleton(ISafetyManager, factory=create_safety_manager)
            logger.info("ISafetyManager가 SafetyManager로 등록되었습니다")

        # PreflightCoordinator 등록 (Singleton)
        if not container.is_registered(IPreflightCoordinator):
            container.register_singleton(IPreflightCoordinator, PreflightCoordinator)
            logger.info("IPreflightCoordinator가 PreflightCoordinator로 등록되었습니다")

        # JournalManager 등록 (Singleton)
        if not container.is_registered(IJournalManager):

            def create_journal_manager():
                config = container.resolve(JournalConfiguration)
                return JournalManager(config)

            container.register_singleton(IJournalManager, factory=create_journal_manager)
            logger.info("IJournalManager가 JournalManager로 등록되었습니다")

        # SafetyConfiguration 등록 (Singleton)
        if not container.is_registered(SafetyConfiguration):
            container.register_singleton(SafetyConfiguration, factory=lambda: SafetyConfiguration())
            logger.info("SafetyConfiguration이 등록되었습니다")

        # IBackupManager 등록 (Singleton) - 미래 확장용
        if not container.is_registered(IBackupManager):
            container.register_singleton(
                IBackupManager, factory=lambda: None
            )  # NOTE: 현재 미구현. 향후 백업 기능 구현 시 교체 예정
            logger.info("IBackupManager가 등록되었습니다 (미구현)")

        # JournalConfiguration 등록 (Singleton)
        if not container.is_registered(JournalConfiguration):
            container.register_singleton(
                JournalConfiguration, factory=lambda: JournalConfiguration()
            )
            logger.info("JournalConfiguration이 등록되었습니다")

        # IRollbackEngine 등록 (Singleton) - 미래 확장용
        if not container.is_registered(IRollbackEngine):
            container.register_singleton(
                IRollbackEngine, factory=lambda: None
            )  # NOTE: 현재 미구현. 향후 롤백 기능 구현 시 교체 예정
            logger.info("IRollbackEngine이 등록되었습니다 (미구현)")

        # IInterruptionManager 등록 (Singleton)
        if not container.is_registered(IInterruptionManager):
            container.register_singleton(IInterruptionManager, InterruptionManager)
            logger.info("IInterruptionManager가 InterruptionManager로 등록되었습니다")

        # IConfirmationManager 등록 (Singleton) - 미래 확장용
        if not container.is_registered(IConfirmationManager):
            container.register_singleton(
                IConfirmationManager, factory=lambda: None
            )  # NOTE: 현재 미구현. 향후 사용자 확인 기능 구현 시 교체 예정
            logger.info("IConfirmationManager가 등록되었습니다 (미구현)")

        # ICommandInvoker 등록 (Singleton) - 미래 확장용
        if not container.is_registered(ICommandInvoker):
            container.register_singleton(
                ICommandInvoker, factory=lambda: None
            )  # NOTE: 현재 미구현. 향후 고급 명령 시스템 구현 시 교체 예정
            logger.info("ICommandInvoker가 등록되었습니다 (미구현)")

        # IUndoRedoManager 등록 (Singleton) - 미래 확장용
        if not container.is_registered(IUndoRedoManager):
            container.register_singleton(
                IUndoRedoManager, factory=lambda: None
            )  # NOTE: 현재 미구현. 향후 고급 실행 취소/재실행 기능 구현 시 교체 예정
            logger.info("IUndoRedoManager가 등록되었습니다 (미구현)")

        # 추가 서비스들은 여기에 등록
        # TODO: 향후 추가 서비스들

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

        file_organization_service = get_service(IFileOrganizationService)
        logger.info(f"FileOrganizationService 인스턴스 생성: {id(file_organization_service)}")

        media_data_service = get_service(IMediaDataService)
        logger.info(f"MediaDataService 인스턴스 생성: {id(media_data_service)}")

        tmdb_search_service = get_service(ITMDBSearchService)
        logger.info(f"TMDBSearchService 인스턴스 생성: {id(tmdb_search_service)}")

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
