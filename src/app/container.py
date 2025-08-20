"""
Dependency Injection Container

애플리케이션 전반의 의존성 주입을 관리하는 중앙 컨테이너
"""

import inspect
import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any, Generic, TypeVar

# Type variables for generic DI container
T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


class LifecycleType(Enum):
    """의존성 라이프사이클 타입"""

    SINGLETON = "singleton"  # 단일 인스턴스 (앱 전체 동안 유지)
    TRANSIENT = "transient"  # 매번 새 인스턴스 생성
    SCOPED = "scoped"  # 스코프 내에서만 유지


class DependencyRegistration(Generic[T]):
    """의존성 등록 정보"""

    def __init__(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        lifecycle: LifecycleType = LifecycleType.SINGLETON,
        name: str | None = None,
    ):
        self.interface = interface
        self.implementation = implementation
        self.factory = factory
        self.lifecycle = lifecycle
        self.name = name or interface.__name__
        self.instance: T | None = None
        self.creation_lock = threading.RLock()

        # 팩토리와 구현체 중 하나는 반드시 있어야 함
        if implementation is None and factory is None:
            raise ValueError("구현체 또는 팩토리 중 하나는 제공되어야 합니다")


class IDIContainer(ABC):
    """DI Container 인터페이스"""

    @abstractmethod
    def register_singleton(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None = None,
        factory: Callable[[], TInterface] | None = None,
        name: str | None = None,
    ) -> None:
        """싱글톤으로 의존성 등록"""

    @abstractmethod
    def register_transient(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None = None,
        factory: Callable[[], TInterface] | None = None,
        name: str | None = None,
    ) -> None:
        """매번 새 인스턴스로 의존성 등록"""

    @abstractmethod
    def register_scoped(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None = None,
        factory: Callable[[], TInterface] | None = None,
        name: str | None = None,
    ) -> None:
        """스코프 내에서만 유지되는 의존성 등록"""

    @abstractmethod
    def resolve(self, interface: type[T], name: str | None = None) -> T:
        """의존성 해결"""

    @abstractmethod
    def try_resolve(self, interface: type[T], name: str | None = None) -> T | None:
        """의존성 해결 시도 (실패 시 None 반환)"""

    @abstractmethod
    def is_registered(self, interface: type[T], name: str | None = None) -> bool:
        """의존성 등록 여부 확인"""

    @abstractmethod
    def create_scope(self) -> "IDIScope":
        """새 스코프 생성"""


class IDIScope(ABC):
    """DI 스코프 인터페이스"""

    @abstractmethod
    def resolve(self, interface: type[T], name: str | None = None) -> T:
        """스코프 내에서 의존성 해결"""

    @abstractmethod
    def dispose(self) -> None:
        """스코프 정리"""


class DIScope(IDIScope):
    """DI 스코프 구현체"""

    def __init__(self, container: "DIContainer"):
        self._container = container
        self._scoped_instances: dict[str, Any] = {}
        self._disposed = False

    def resolve(self, interface: type[T], name: str | None = None) -> T:
        """스코프 내에서 의존성 해결"""
        if self._disposed:
            raise RuntimeError("이미 해제된 스코프입니다")

        key = self._get_key(interface, name)

        # 스코프 내 인스턴스가 있으면 반환
        if key in self._scoped_instances:
            return self._scoped_instances[key]

        # 컨테이너에서 해결
        instance = self._container.resolve(interface, name)

        # Scoped 라이프사이클이면 스코프에 저장
        registration = self._container._get_registration(interface, name)
        if registration and registration.lifecycle == LifecycleType.SCOPED:
            self._scoped_instances[key] = instance

        return instance

    def dispose(self) -> None:
        """스코프 정리"""
        if self._disposed:
            return

        # 스코프 내 인스턴스들 정리
        for instance in self._scoped_instances.values():
            if hasattr(instance, "dispose"):
                try:
                    instance.dispose()
                except Exception as e:
                    logging.warning(f"스코프 인스턴스 정리 실패: {e}")

        self._scoped_instances.clear()
        self._disposed = True

    def _get_key(self, interface: type[T], name: str | None) -> str:
        """등록 키 생성"""
        module_name = getattr(interface, "__module__", "unknown")
        interface_name = getattr(interface, "__name__", str(interface))
        return f"{module_name}.{interface_name}:{name or 'default'}"


class DIContainer(IDIContainer):
    """의존성 주입 컨테이너"""

    def __init__(self):
        self._registrations: dict[str, DependencyRegistration] = {}
        self._resolution_stack: list[str] = []  # 순환 의존성 감지용
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)

        # 자기 자신을 등록
        self._register_self()

        self.logger.info("DIContainer 초기화 완료")

    def _register_self(self) -> None:
        """컨테이너 자신을 등록"""
        self_registration = DependencyRegistration(
            interface=IDIContainer,
            factory=lambda: self,
            lifecycle=LifecycleType.SINGLETON,
            name="DIContainer",
        )
        self_registration.instance = self

        key = self._get_key(IDIContainer, "DIContainer")
        self._registrations[key] = self_registration

    def register_singleton(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None = None,
        factory: Callable[[], TInterface] | None = None,
        name: str | None = None,
    ) -> None:
        """싱글톤으로 의존성 등록"""
        self._register(interface, implementation, factory, LifecycleType.SINGLETON, name)

    def register_transient(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None = None,
        factory: Callable[[], TInterface] | None = None,
        name: str | None = None,
    ) -> None:
        """매번 새 인스턴스로 의존성 등록"""
        self._register(interface, implementation, factory, LifecycleType.TRANSIENT, name)

    def register_scoped(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None = None,
        factory: Callable[[], TInterface] | None = None,
        name: str | None = None,
    ) -> None:
        """스코프 내에서만 유지되는 의존성 등록"""
        self._register(interface, implementation, factory, LifecycleType.SCOPED, name)

    def _register(
        self,
        interface: type[TInterface],
        implementation: type[TImplementation] | None,
        factory: Callable[[], TInterface] | None,
        lifecycle: LifecycleType,
        name: str | None,
    ) -> None:
        """의존성 등록 내부 구현"""
        with self._lock:
            registration = DependencyRegistration(
                interface=interface,
                implementation=implementation,
                factory=factory,
                lifecycle=lifecycle,
                name=name,
            )

            key = self._get_key(interface, name)
            self._registrations[key] = registration

            self.logger.debug(
                f"의존성 등록: {interface.__name__} -> "
                f"{implementation.__name__ if implementation else 'Factory'} "
                f"({lifecycle.value})"
            )

    def resolve(self, interface: type[T], name: str | None = None) -> T:
        """의존성 해결"""
        try:
            return self._resolve_internal(interface, name)
        except Exception as e:
            interface_name = getattr(interface, "__name__", str(interface))
            self.logger.error(f"의존성 해결 실패: {interface_name} - {e}")
            raise

    def try_resolve(self, interface: type[T], name: str | None = None) -> T | None:
        """의존성 해결 시도 (실패 시 None 반환)"""
        try:
            return self._resolve_internal(interface, name)
        except Exception as e:
            interface_name = getattr(interface, "__name__", str(interface))
            self.logger.debug(f"의존성 해결 실패 (try_resolve): {interface_name} - {e}")
            return None

    def _resolve_internal(self, interface: type[T], name: str | None = None) -> T:
        """의존성 해결 내부 구현"""
        key = self._get_key(interface, name)

        # 순환 의존성 검사
        if key in self._resolution_stack:
            cycle_path = " -> ".join(self._resolution_stack + [key])
            raise RuntimeError(f"순환 의존성 감지: {cycle_path}")

        with self._lock:
            registration = self._registrations.get(key)
            if not registration:
                interface_name = getattr(interface, "__name__", str(interface))
                raise ValueError(f"등록되지 않은 의존성: {interface_name} (name: {name})")

            # 싱글톤 인스턴스가 있으면 반환
            if (
                registration.lifecycle == LifecycleType.SINGLETON
                and registration.instance is not None
            ):
                return registration.instance

            # 인스턴스 생성
            self._resolution_stack.append(key)
            try:
                instance = self._create_instance(registration)

                # 싱글톤이면 저장
                if registration.lifecycle == LifecycleType.SINGLETON:
                    registration.instance = instance

                return instance
            finally:
                self._resolution_stack.pop()

    def _create_instance(self, registration: DependencyRegistration[T]) -> T:
        """인스턴스 생성"""
        with registration.creation_lock:
            # 팩토리가 있으면 팩토리 사용
            if registration.factory:
                return registration.factory()

            # 구현체로 인스턴스 생성
            if registration.implementation:
                return self._create_with_dependency_injection(registration.implementation)

            raise ValueError(f"인스턴스 생성 방법이 없습니다: {registration.interface.__name__}")

    def _create_with_dependency_injection(self, implementation: type[T]) -> T:
        """의존성 주입으로 인스턴스 생성"""
        # 생성자 시그니처 분석
        constructor = implementation.__init__
        signature = inspect.signature(constructor)

        # 생성자 인자 해결
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            # 타입 힌트가 있으면 의존성으로 해결
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = self.resolve(param.annotation)
                except Exception:
                    # 기본값이 있으면 사용
                    if param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default
                    else:
                        raise

        return implementation(**kwargs)

    def is_registered(self, interface: type[T], name: str | None = None) -> bool:
        """의존성 등록 여부 확인"""
        key = self._get_key(interface, name)
        return key in self._registrations

    def create_scope(self) -> IDIScope:
        """새 스코프 생성"""
        return DIScope(self)

    def _get_registration(
        self, interface: type[T], name: str | None = None
    ) -> DependencyRegistration[T] | None:
        """등록 정보 가져오기"""
        key = self._get_key(interface, name)
        return self._registrations.get(key)

    def _get_key(self, interface: type[T], name: str | None) -> str:
        """등록 키 생성"""
        module_name = getattr(interface, "__module__", "unknown")
        interface_name = getattr(interface, "__name__", str(interface))
        return f"{module_name}.{interface_name}:{name or 'default'}"

    def get_registrations(self) -> dict[str, str]:
        """등록된 의존성 목록 반환 (디버깅용)"""
        with self._lock:
            return {
                key: f"{reg.interface.__name__} -> "
                f"{reg.implementation.__name__ if reg.implementation else 'Factory'} "
                f"({reg.lifecycle.value})"
                for key, reg in self._registrations.items()
            }

    def dispose(self) -> None:
        """컨테이너 정리"""
        with self._lock:
            # 싱글톤 인스턴스들 정리 (복사본 생성하여 안전하게 순회)
            registrations_copy = list(self._registrations.values())
            for registration in registrations_copy:
                if (
                    registration.lifecycle == LifecycleType.SINGLETON
                    and registration.instance is not None
                ):
                    # 순환 참조 방지: DIContainer 자기 자신은 dispose하지 않음
                    if isinstance(registration.instance, DIContainer):
                        continue

                    if hasattr(registration.instance, "dispose"):
                        try:
                            class_name = registration.instance.__class__.__name__
                            self.logger.debug(f"인스턴스 정리 시작: {class_name}")
                            registration.instance.dispose()
                            self.logger.debug(f"인스턴스 정리 완료: {class_name}")
                        except Exception as e:
                            self.logger.warning(
                                f"인스턴스 정리 실패: {registration.instance.__class__.__name__} - {e}"
                            )

            self._registrations.clear()
            self.logger.debug("DIContainer 정리 완료")


# 전역 컨테이너 인스턴스 (애플리케이션 전체에서 사용)
_global_container: DIContainer | None = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """전역 DI 컨테이너 가져오기"""
    global _global_container

    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = DIContainer()

    return _global_container


def set_container(container: DIContainer) -> None:
    """전역 DI 컨테이너 설정 (테스트용)"""
    global _global_container
    with _container_lock:
        _global_container = container


def reset_container() -> None:
    """전역 DI 컨테이너 리셋 (테스트용)"""
    global _global_container
    with _container_lock:
        if _global_container:
            _global_container.dispose()
        _global_container = None
