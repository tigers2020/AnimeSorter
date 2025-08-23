"""
컴포넌트 팩토리

컴포넌트 생성 및 의존성 주입을 담당하는 팩토리 클래스
"""

import logging
from collections.abc import Callable
from typing import Any

from ..commands.base_command import BaseCommand
from ..commands.file_commands import (ChooseFilesCommand, ChooseFolderCommand,
                                      StartScanCommand, StopScanCommand)
from ..commands.organize_commands import (CancelOrganizeCommand,
                                          StartOrganizeCommand)
from ..commands.tmdb_commands import (SelectTMDBAnimeCommand,
                                      SkipTMDBGroupCommand,
                                      StartTMDBSearchCommand)
from ..interfaces.i_controller import IController
from ..interfaces.i_event_bus import IEventBus
from ..interfaces.i_service import IService
from ..interfaces.i_view_model import IViewModel
from ..services.file_service import FileService
from ..services.metadata_service import MetadataService
from ..services.state_service import StateService
from ..view_models.detail_view_model import DetailViewModel
from ..view_models.file_list_view_model import FileListViewModel
from ..view_models.main_window import MainWindowViewModel


class ComponentFactory:
    """
    컴포넌트 팩토리 클래스

    컴포넌트 생성, 의존성 주입, 설정 적용을 담당
    """

    def __init__(self, event_bus: IEventBus):
        """
        팩토리 초기화

        Args:
            event_bus: 이벤트 버스 인스턴스
        """
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

        # 등록된 컴포넌트 타입들
        self._registered_controllers: dict[str, type[IController]] = {}
        self._registered_services: dict[str, type[IService]] = {}
        self._registered_view_models: dict[str, type[IViewModel]] = {}
        self._registered_commands: dict[str, type[BaseCommand]] = {}

        # 생성된 인스턴스들 (싱글톤 관리)
        self._controller_instances: dict[str, IController] = {}
        self._service_instances: dict[str, IService] = {}
        self._view_model_instances: dict[str, IViewModel] = {}
        self._command_instances: dict[str, BaseCommand] = {}

        # 설정 저장소
        self._configurations: dict[str, dict[str, Any]] = {}

        # 생성 후 초기화 콜백
        self._post_creation_callbacks: dict[str, Callable] = {}

        self.logger.info("ComponentFactory 초기화 완료")

        # 기본 서비스들 자동 등록
        self._register_default_services()

        # 기본 뷰모델들 자동 등록
        self._register_default_view_models()

        # 기본 명령들 자동 등록
        self._register_default_commands()

        # 기본 컨트롤러들 자동 등록
        self._register_default_controllers()

    def _register_default_services(self) -> None:
        """기본 서비스들 자동 등록"""
        self.register_service("file_service", FileService)
        self.register_service("metadata_service", MetadataService)
        self.register_service("state_service", StateService)
        self.logger.info("기본 서비스 등록 완료")

    def _register_default_view_models(self) -> None:
        """기본 뷰모델들 자동 등록"""
        self.register_view_model("main_window_view_model", MainWindowViewModel)
        self.register_view_model("file_list_view_model", FileListViewModel)
        self.register_view_model("detail_view_model", DetailViewModel)
        self.logger.info("기본 뷰모델 등록 완료")

    def _register_default_commands(self) -> None:
        """기본 명령들 자동 등록"""
        self.register_command("choose_files", ChooseFilesCommand)
        self.register_command("choose_folder", ChooseFolderCommand)
        self.register_command("start_scan", StartScanCommand)
        self.register_command("stop_scan", StopScanCommand)
        self.register_command("start_tmdb_search", StartTMDBSearchCommand)
        self.register_command("select_tmdb_anime", SelectTMDBAnimeCommand)
        self.register_command("skip_tmdb_group", SkipTMDBGroupCommand)
        self.register_command("start_organize", StartOrganizeCommand)
        self.register_command("cancel_organize", CancelOrganizeCommand)
        self.logger.info("기본 명령 등록 완료")

    def _register_default_controllers(self) -> None:
        """기본 컨트롤러들 자동 등록"""
        from ..controllers.file_processing_controller import \
            FileProcessingController
        from ..controllers.organize_controller import OrganizeController
        from ..controllers.tmdb_controller import TMDBController
        from ..controllers.window_manager import WindowManager

        self.register_controller("window_manager", WindowManager)
        self.register_controller("file_processing_controller", FileProcessingController)
        self.register_controller("tmdb_controller", TMDBController)
        self.register_controller("organize_controller", OrganizeController)
        self.logger.info("기본 컨트롤러 등록 완료")

    def register_controller(
        self, name: str, controller_class: type[IController], _singleton: bool = True
    ) -> None:
        """
        컨트롤러 등록

        Args:
            name: 컨트롤러 이름
            controller_class: 컨트롤러 클래스
            _singleton: 싱글톤 여부 (현재 미사용)
        """
        self._registered_controllers[name] = controller_class
        self.logger.debug(f"컨트롤러 등록: {name} ({controller_class.__name__})")

    def register_service(
        self, name: str, service_class: type[IService], _singleton: bool = True
    ) -> None:
        """
        서비스 등록

        Args:
            name: 서비스 이름
            service_class: 서비스 클래스
            _singleton: 싱글톤 여부 (현재 미사용)
        """
        self._registered_services[name] = service_class
        self.logger.debug(f"서비스 등록: {name} ({service_class.__name__})")

    def register_view_model(
        self, name: str, view_model_class: type[IViewModel], _singleton: bool = True
    ) -> None:
        """
        뷰모델 등록

        Args:
            name: 뷰모델 이름
            view_model_class: 뷰모델 클래스
            _singleton: 싱글톤 여부 (현재 미사용)
        """
        self._registered_view_models[name] = view_model_class
        self.logger.debug(f"뷰모델 등록: {name} ({view_model_class.__name__})")

    def register_command(
        self, name: str, command_class: type[BaseCommand], _singleton: bool = True
    ) -> None:
        """
        명령 등록

        Args:
            name: 명령 이름
            command_class: 명령 클래스
            _singleton: 싱글톤 여부 (현재 미사용)
        """
        self._registered_commands[name] = command_class
        self.logger.debug(f"명령 등록: {name} ({command_class.__name__})")

    def create_controller(self, name: str, config: dict[str, Any] | None = None) -> IController:
        """
        컨트롤러 생성

        Args:
            name: 컨트롤러 이름
            config: 설정 딕셔너리

        Returns:
            생성된 컨트롤러 인스턴스

        Raises:
            ValueError: 등록되지 않은 컨트롤러인 경우
        """
        if name in self._controller_instances:
            return self._controller_instances[name]

        if name not in self._registered_controllers:
            raise ValueError(f"등록되지 않은 컨트롤러: {name}")

        try:
            controller_class = self._registered_controllers[name]
            controller = controller_class(self.event_bus)

            # 설정 적용
            if config:
                self._apply_configuration(controller, config)
            elif name in self._configurations:
                self._apply_configuration(controller, self._configurations[name])

            # 초기화 콜백 실행
            if name in self._post_creation_callbacks:
                self._post_creation_callbacks[name](controller)

            # 싱글톤으로 저장
            self._controller_instances[name] = controller

            self.logger.info(f"컨트롤러 생성 완료: {name}")
            return controller

        except Exception as e:
            self.logger.error(f"컨트롤러 생성 실패: {name} - {e}")
            raise

    def create_service(self, name: str, config: dict[str, Any] | None = None) -> IService:
        """
        서비스 생성

        Args:
            name: 서비스 이름
            config: 설정 딕셔너리

        Returns:
            생성된 서비스 인스턴스

        Raises:
            ValueError: 등록되지 않은 서비스인 경우
        """
        if name in self._service_instances:
            return self._service_instances[name]

        if name not in self._registered_services:
            raise ValueError(f"등록되지 않은 서비스: {name}")

        try:
            service_class = self._registered_services[name]
            service = service_class(self.event_bus)

            # 설정 적용
            if config:
                service.configure(config)
            elif name in self._configurations:
                service.configure(self._configurations[name])

            # 초기화 콜백 실행
            if name in self._post_creation_callbacks:
                self._post_creation_callbacks[name](service)

            # 싱글톤으로 저장
            self._service_instances[name] = service

            self.logger.info(f"서비스 생성 완료: {name}")
            return service

        except Exception as e:
            self.logger.error(f"서비스 생성 실패: {name} - {e}")
            raise

    def create_view_model(
        self, name: str, config: dict[str, Any] | None = None, parent=None
    ) -> IViewModel:
        """
        뷰모델 생성

        Args:
            name: 뷰모델 이름
            config: 설정 딕셔너리
            parent: 부모 QObject

        Returns:
            생성된 뷰모델 인스턴스

        Raises:
            ValueError: 등록되지 않은 뷰모델인 경우
        """
        if name in self._view_model_instances:
            return self._view_model_instances[name]

        if name not in self._registered_view_models:
            raise ValueError(f"등록되지 않은 뷰모델: {name}")

        try:
            view_model_class = self._registered_view_models[name]
            view_model = view_model_class(self.event_bus, parent)

            # 설정 적용
            if config:
                for key, value in config.items():
                    view_model.set_property(key, value, validate=False)
            elif name in self._configurations:
                for key, value in self._configurations[name].items():
                    view_model.set_property(key, value, validate=False)

            # 초기화 콜백 실행
            if name in self._post_creation_callbacks:
                self._post_creation_callbacks[name](view_model)

            # 싱글톤으로 저장
            self._view_model_instances[name] = view_model

            self.logger.info(f"뷰모델 생성 완료: {name}")
            return view_model

        except Exception as e:
            self.logger.error(f"뷰모델 생성 실패: {name} - {e}")
            raise

    def create_command(
        self, name: str, config: dict[str, Any] | None = None, **kwargs
    ) -> BaseCommand:
        """
        명령 생성

        Args:
            name: 명령 이름
            config: 설정 딕셔너리
            **kwargs: 명령 생성에 필요한 추가 인자들

        Returns:
            생성된 명령 인스턴스

        Raises:
            ValueError: 등록되지 않은 명령인 경우
        """
        if name not in self._registered_commands:
            raise ValueError(f"등록되지 않은 명령: {name}")

        try:
            command_class = self._registered_commands[name]

            # 명령 생성 (이벤트 버스 + 추가 인자들)
            command = command_class(self.event_bus, **kwargs)

            # 설정 적용
            if config:
                for key, value in config.items():
                    if hasattr(command, key):
                        setattr(command, key, value)

            # 초기화 콜백 실행
            if name in self._post_creation_callbacks:
                self._post_creation_callbacks[name](command)

            self.logger.info(f"명령 생성 완료: {name}")
            return command

        except Exception as e:
            self.logger.error(f"명령 생성 실패: {name} - {e}")
            raise

    def get_controller(self, name: str) -> IController | None:
        """컨트롤러 인스턴스 가져오기"""
        return self._controller_instances.get(name)

    def get_service(self, name: str) -> IService | None:
        """서비스 인스턴스 가져오기"""
        return self._service_instances.get(name)

    def get_view_model(self, name: str) -> IViewModel | None:
        """뷰모델 인스턴스 가져오기"""
        return self._view_model_instances.get(name)

    def get_command(self, name: str) -> BaseCommand | None:
        """명령 인스턴스 가져오기"""
        return self._command_instances.get(name)

    def set_configuration(self, component_name: str, config: dict[str, Any]) -> None:
        """컴포넌트 설정 저장"""
        self._configurations[component_name] = config

    def set_post_creation_callback(self, component_name: str, callback: Callable) -> None:
        """생성 후 초기화 콜백 설정"""
        self._post_creation_callbacks[component_name] = callback

    def cleanup_all(self) -> None:
        """모든 컴포넌트 정리"""
        # 컨트롤러 정리
        for controller in self._controller_instances.values():
            try:
                controller.cleanup()
            except Exception as e:
                self.logger.error(f"컨트롤러 정리 실패: {e}")

        # 서비스 정리
        for service in self._service_instances.values():
            try:
                if service.is_running:
                    service.stop()
            except Exception as e:
                self.logger.error(f"서비스 정리 실패: {e}")

        # 뷰모델 정리
        for view_model in self._view_model_instances.values():
            try:
                view_model.cleanup()
            except Exception as e:
                self.logger.error(f"뷰모델 정리 실패: {e}")

        # 명령 정리 (명령은 특별한 정리 로직이 없으므로 무시)

        # 인스턴스 정리
        self._controller_instances.clear()
        self._service_instances.clear()
        self._view_model_instances.clear()
        self._command_instances.clear()

        self.logger.info("모든 컴포넌트 정리 완료")

    def _apply_configuration(self, component: Any, config: dict[str, Any]) -> None:
        """컴포넌트에 설정 적용"""
        for key, value in config.items():
            if hasattr(component, key):
                setattr(component, key, value)

    def get_stats(self) -> dict[str, Any]:
        """팩토리 통계 정보 반환"""
        return {
            "registered_controllers": len(self._registered_controllers),
            "registered_services": len(self._registered_services),
            "registered_view_models": len(self._registered_view_models),
            "registered_commands": len(self._registered_commands),
            "active_controller_instances": len(self._controller_instances),
            "active_service_instances": len(self._service_instances),
            "active_view_model_instances": len(self._view_model_instances),
            "active_command_instances": len(self._command_instances),
            "configurations": len(self._configurations),
            "post_creation_callbacks": len(self._post_creation_callbacks),
        }
