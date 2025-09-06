"""
Manager 기본 클래스 - AnimeSorter

모든 Manager 클래스가 공통으로 사용할 수 있는 인터페이스와 기본 기능을 제공합니다.
- 공통 인터페이스 정의
- 기본 에러 처리 및 로깅
- 생명주기 관리
- 설정 관리
- 이벤트 시스템 통합
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from PyQt5.QtCore import QObject, pyqtSignal

from .unified_event_system import (BaseEvent, EventCategory, EventPriority,
                                   get_unified_event_bus)


class ManagerState(Enum):
    """Manager 상태"""

    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ManagerPriority(Enum):
    """Manager 우선순위"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ManagerConfig:
    """Manager 설정"""

    name: str
    priority: ManagerPriority = ManagerPriority.NORMAL
    auto_start: bool = True
    log_level: str = "INFO"
    config_file: Optional[str] = None
    backup_enabled: bool = True
    max_backup_count: int = 5
    health_check_interval: int = 30  # 초
    timeout: int = 300  # 초


@runtime_checkable
class IManager(Protocol):
    """Manager 인터페이스"""

    def initialize(self) -> bool:
        """초기화"""
        ...

    def start(self) -> bool:
        """시작"""
        ...

    def stop(self) -> bool:
        """중지"""
        ...

    def pause(self) -> bool:
        """일시정지"""
        ...

    def resume(self) -> bool:
        """재개"""
        ...

    def get_state(self) -> ManagerState:
        """상태 반환"""
        ...

    def get_health_status(self) -> dict[str, Any]:
        """건강 상태 반환"""
        ...

    def cleanup(self) -> None:
        """정리"""
        ...


class ManagerBase(QObject):
    """Manager 기본 클래스"""

    # Qt 시그널
    state_changed = pyqtSignal(str, str)  # old_state, new_state
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    health_status_changed = pyqtSignal(dict)  # health_status

    def __init__(self, config: ManagerConfig, parent=None):
        """초기화"""
        super().__init__(parent)

        # 기본 설정
        self.config = config
        self.name = config.name
        self.priority = config.priority

        # 상태 관리
        self._state = ManagerState.INITIALIZING
        self._previous_state = None
        self._state_lock = threading.RLock()

        # 로깅 설정
        self.logger = logging.getLogger(f"Manager.{self.name}")
        self.logger.setLevel(getattr(logging, config.log_level.upper()))

        # 이벤트 시스템
        self.unified_event_bus = get_unified_event_bus()

        # 생명주기 관리
        self._start_time = None
        self._stop_time = None
        self._last_health_check = None

        # 에러 추적
        self._error_count = 0
        self._last_error = None
        self._error_history: list[dict[str, Any]] = []

        # 설정 관리
        self._config_file = Path(config.config_file) if config.config_file else None
        self._backup_dir = None

        # 백업 관리
        if config.backup_enabled:
            self._setup_backup_system()

        # 초기화 완료
        self._set_state(ManagerState.READY)
        self.logger.info(f"Manager '{self.name}' 초기화 완료")

    def _initialize_impl(self) -> bool:
        """구현체별 초기화 로직 (기본 구현)"""
        return True

    def _start_impl(self) -> bool:
        """구현체별 시작 로직 (기본 구현)"""
        return True

    def _stop_impl(self) -> bool:
        """구현체별 중지 로직 (기본 구현)"""
        return True

    def _pause_impl(self) -> bool:
        """구현체별 일시정지 로직 (기본 구현)"""
        return True

    def _resume_impl(self) -> bool:
        """구현체별 재개 로직 (기본 구현)"""
        return True

    def initialize(self) -> bool:
        """초기화"""
        try:
            with self._state_lock:
                if self._state != ManagerState.INITIALIZING:
                    self.logger.warning(f"이미 초기화됨: {self._state}")
                    return True

                self.logger.info("초기화 시작")

                # 구현체별 초기화
                if not self._initialize_impl():
                    self._set_state(ManagerState.ERROR)
                    return False

                # 초기화 완료
                self._set_state(ManagerState.READY)
                self.logger.info("초기화 완료")
                return True

        except Exception as e:
            self._handle_error("initialization_error", str(e))
            return False

    def start(self) -> bool:
        """시작"""
        try:
            with self._state_lock:
                if self._state not in [ManagerState.READY, ManagerState.STOPPED]:
                    self.logger.warning(f"시작할 수 없는 상태: {self._state}")
                    return False

                self.logger.info("시작")
                self._start_time = datetime.now()

                # 구현체별 시작
                if not self._start_impl():
                    self._set_state(ManagerState.ERROR)
                    return False

                # 시작 완료
                self._set_state(ManagerState.RUNNING)
                self.logger.info("시작 완료")
                return True

        except Exception as e:
            self._handle_error("start_error", str(e))
            return False

    def stop(self) -> bool:
        """중지"""
        try:
            with self._state_lock:
                if self._state == ManagerState.STOPPED:
                    return True

                self.logger.info("중지 시작")
                self._set_state(ManagerState.STOPPING)

                # 구현체별 중지
                if not self._stop_impl():
                    self.logger.warning("중지 실패")

                # 중지 완료
                self._stop_time = datetime.now()
                self._set_state(ManagerState.STOPPED)
                self.logger.info("중지 완료")
                return True

        except Exception as e:
            self._handle_error("stop_error", str(e))
            return False

    def pause(self) -> bool:
        """일시정지"""
        try:
            with self._state_lock:
                if self._state != ManagerState.RUNNING:
                    self.logger.warning(f"일시정지할 수 없는 상태: {self._state}")
                    return False

                self.logger.info("일시정지")

                # 구현체별 일시정지
                if not self._pause_impl():
                    return False

                # 일시정지 완료
                self._set_state(ManagerState.PAUSED)
                self.logger.info("일시정지 완료")
                return True

        except Exception as e:
            self._handle_error("pause_error", str(e))
            return False

    def resume(self) -> bool:
        """재개"""
        try:
            with self._state_lock:
                if self._state != ManagerState.PAUSED:
                    self.logger.warning(f"재개할 수 없는 상태: {self._state}")
                    return False

                self.logger.info("재개")

                # 구현체별 재개
                if not self._resume_impl():
                    return False

                # 재개 완료
                self._set_state(ManagerState.RUNNING)
                self.logger.info("재개 완료")
                return True

        except Exception as e:
            self._handle_error("resume_error", str(e))
            return False

    def get_state(self) -> ManagerState:
        """상태 반환"""
        with self._state_lock:
            return self._state

    def get_health_status(self) -> dict[str, Any]:
        """건강 상태 반환"""
        try:
            current_time = datetime.now()

            # 기본 상태 정보
            health_status = {
                "name": self.name,
                "state": self._state.value,
                "priority": self.priority.value,
                "uptime": self._get_uptime(),
                "error_count": self._error_count,
                "last_error": self._last_error,
                "last_health_check": current_time.isoformat(),
                "config_file": str(self._config_file) if self._config_file else None,
                "backup_enabled": self.config.backup_enabled,
            }

            # 구현체별 건강 상태 추가
            custom_health = self._get_custom_health_status()
            if custom_health:
                health_status.update(custom_health)

            # 건강 상태 업데이트
            self._last_health_check = current_time
            self.health_status_changed.emit(health_status)

            return health_status

        except Exception as e:
            self.logger.error(f"건강 상태 조회 실패: {e}")
            return {"error": str(e)}

    def cleanup(self) -> None:
        """정리"""
        try:
            self.logger.info("정리 시작")

            # 중지 상태 확인
            if self._state != ManagerState.STOPPED:
                self.stop()

            # 구현체별 정리
            self._cleanup_impl()

            # 백업 생성
            if self.config.backup_enabled and self._backup_dir:
                self._create_backup()

            self.logger.info("정리 완료")

        except Exception as e:
            self.logger.error(f"정리 실패: {e}")

    def _set_state(self, new_state: ManagerState) -> None:
        """상태 변경"""
        with self._state_lock:
            if self._state != new_state:
                old_state = self._state
                self._previous_state = old_state
                self._state = new_state

                # 시그널 발생
                self.state_changed.emit(old_state.value, new_state.value)

                # 이벤트 발행
                if self.unified_event_bus:
                    event = BaseEvent(
                        source=self.name,
                        category=EventCategory.SYSTEM,
                        priority=EventPriority.NORMAL,
                        metadata={
                            "old_state": old_state.value,
                            "new_state": new_state.value,
                            "manager_name": self.name,
                        },
                    )
                    self.unified_event_bus.publish(event)

                self.logger.debug(f"상태 변경: {old_state.value} -> {new_state.value}")

    def _handle_error(self, error_type: str, error_message: str) -> None:
        """에러 처리"""
        try:
            self._error_count += 1
            self._last_error = {
                "type": error_type,
                "message": error_message,
                "timestamp": datetime.now().isoformat(),
                "state": self._state.value,
            }

            # 에러 히스토리에 추가
            self._error_history.append(self._last_error.copy())
            if len(self._error_history) > 100:  # 최대 100개 유지
                self._error_history.pop(0)

            # 에러 시그널 발생
            self.error_occurred.emit(error_type, error_message)

            # 상태를 ERROR로 변경
            self._set_state(ManagerState.ERROR)

            # 로깅
            self.logger.error(f"에러 발생 [{error_type}]: {error_message}")

        except Exception as e:
            self.logger.error(f"에러 처리 중 추가 에러 발생: {e}")

    def _get_uptime(self) -> Optional[float]:
        """가동 시간 계산 (초)"""
        if self._start_time and self._state in [ManagerState.RUNNING, ManagerState.PAUSED]:
            if self._stop_time:
                return (self._stop_time - self._start_time).total_seconds()
            else:
                return (datetime.now() - self._start_time).total_seconds()
        return None

    def _setup_backup_system(self) -> None:
        """백업 시스템 설정"""
        try:
            if self._config_file and self._config_file.exists():
                backup_base = self._config_file.parent / "_backup"
                self._backup_dir = backup_base / self.name
                self._backup_dir.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"백업 디렉토리 설정: {self._backup_dir}")
        except Exception as e:
            self.logger.warning(f"백업 시스템 설정 실패: {e}")

    def _create_backup(self) -> None:
        """백업 생성"""
        try:
            if not self._backup_dir or not self._config_file or not self._config_file.exists():
                return

            # 백업 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self._backup_dir / f"{self.name}_{timestamp}.json"

            # 설정 백업
            config_data = self._get_config_data()
            if config_data:
                import json

                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)

                # 오래된 백업 정리
                self._cleanup_old_backups()

                self.logger.debug(f"백업 생성: {backup_file}")

        except Exception as e:
            self.logger.warning(f"백업 생성 실패: {e}")

    def _cleanup_old_backups(self) -> None:
        """오래된 백업 정리"""
        try:
            if not self._backup_dir:
                return

            # 백업 파일 목록
            backup_files = sorted(
                self._backup_dir.glob(f"{self.name}_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            # 최대 백업 수 초과 시 오래된 것 삭제
            if len(backup_files) > self.config.max_backup_count:
                for old_backup in backup_files[self.config.max_backup_count :]:
                    old_backup.unlink()
                    self.logger.debug(f"오래된 백업 삭제: {old_backup}")

        except Exception as e:
            self.logger.warning(f"백업 정리 실패: {e}")

    def _get_config_data(self) -> Optional[dict[str, Any]]:
        """설정 데이터 반환 (구현체에서 오버라이드 가능)"""
        return {
            "name": self.name,
            "priority": self.priority.value,
            "state": self._state.value,
            "config": self.config.__dict__,
            "error_count": self._error_count,
            "last_error": self._last_error,
        }

    def _get_custom_health_status(self) -> Optional[dict[str, Any]]:
        """구현체별 건강 상태 반환 (구현체에서 오버라이드 가능)"""
        return None

    def _cleanup_impl(self) -> None:
        """구현체별 정리 로직 (구현체에서 오버라이드 가능)"""

    def __str__(self) -> str:
        return f"Manager({self.name}, state={self._state.value})"

    def __repr__(self) -> str:
        return f"ManagerBase(name='{self.name}', state={self._state.value}, priority={self.priority.value})"


class ManagerRegistry:
    """Manager 레지스트리"""

    def __init__(self):
        self._managers: dict[str, ManagerBase] = {}
        self._manager_configs: dict[str, ManagerConfig] = {}
        self._registry_lock = threading.RLock()

    def register_manager(self, manager: ManagerBase) -> bool:
        """Manager 등록"""
        try:
            with self._registry_lock:
                if manager.name in self._managers:
                    return False

                self._managers[manager.name] = manager
                self._manager_configs[manager.name] = manager.config
                return True

        except Exception as e:
            logging.error(f"Manager 등록 실패: {e}")
            return False

    def unregister_manager(self, name: str) -> bool:
        """Manager 등록 해제"""
        try:
            with self._registry_lock:
                if name not in self._managers:
                    return False

                manager = self._managers[name]
                manager.cleanup()

                del self._managers[name]
                del self._manager_configs[name]
                return True

        except Exception as e:
            logging.error(f"Manager 등록 해제 실패: {e}")
            return False

    def get_manager(self, name: str) -> Optional[ManagerBase]:
        """Manager 반환"""
        with self._registry_lock:
            return self._managers.get(name)

    def get_all_managers(self) -> list[ManagerBase]:
        """모든 Manager 반환"""
        with self._registry_lock:
            return list(self._managers.values())

    def get_managers_by_state(self, state: ManagerState) -> list[ManagerBase]:
        """상태별 Manager 반환"""
        with self._registry_lock:
            return [m for m in self._managers.values() if m.get_state() == state]

    def get_managers_by_priority(self, priority: ManagerPriority) -> list[ManagerBase]:
        """우선순위별 Manager 반환"""
        with self._registry_lock:
            return [m for m in self._managers.values() if m.priority == priority]

    def start_all_managers(self) -> dict[str, bool]:
        """모든 Manager 시작"""
        results = {}
        for name, manager in self._managers.items():
            try:
                results[name] = manager.start()
            except Exception as e:
                logging.error(f"Manager '{name}' 시작 실패: {e}")
                results[name] = False
        return results

    def stop_all_managers(self) -> dict[str, bool]:
        """모든 Manager 중지"""
        results = {}
        for name, manager in self._managers.items():
            try:
                results[name] = manager.stop()
            except Exception as e:
                logging.error(f"Manager '{name}' 중지 실패: {e}")
                results[name] = False
        return results

    def get_registry_status(self) -> dict[str, Any]:
        """레지스트리 상태 반환"""
        with self._registry_lock:
            return {
                "total_managers": len(self._managers),
                "managers": {
                    name: {
                        "state": manager.get_state().value,
                        "priority": manager.priority.value,
                        "uptime": manager._get_uptime(),
                        "error_count": manager._error_count,
                    }
                    for name, manager in self._managers.items()
                },
            }


# 전역 Manager 레지스트리
manager_registry = ManagerRegistry()


def get_manager_registry() -> ManagerRegistry:
    """Manager 레지스트리 반환"""
    return manager_registry
