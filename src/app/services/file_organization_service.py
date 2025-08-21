"""
파일 정리 서비스

MainWindow의 파일 정리 로직을 분리한 서비스입니다.
백그라운드 작업을 통해 UI를 블로킹하지 않고 파일 정리를 수행합니다.
"""

import logging
import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.background_task import BaseTask, TaskResult
from app.events import TypedEventBus
from app.organization_events import (
    OrganizationCancelledEvent,
    OrganizationCompletedEvent,
    OrganizationErrorType,
    OrganizationFailedEvent,
    OrganizationPreflightCompletedEvent,
    OrganizationPreflightData,
    OrganizationPreflightStartedEvent,
    OrganizationProgressEvent,
    OrganizationResult,
    OrganizationStartedEvent,
    OrganizationStatus,
    OrganizationValidationCompletedEvent,
    OrganizationValidationFailedEvent,
    OrganizationValidationResult,
    OrganizationValidationStartedEvent,
)
from app.services.background_task_service import IBackgroundTaskService


class IFileOrganizationService(ABC):
    """파일 정리 서비스 인터페이스"""

    @abstractmethod
    def validate_organization_request(
        self, grouped_items: dict[str, Any], destination_directory: Path
    ) -> OrganizationValidationResult:
        """파일 정리 요청 검증"""

    @abstractmethod
    def create_preflight_data(
        self, grouped_items: dict[str, Any], destination_directory: Path
    ) -> OrganizationPreflightData:
        """프리플라이트 데이터 생성"""

    @abstractmethod
    def start_organization(
        self, grouped_items: dict[str, Any], destination_directory: Path, dry_run: bool = False
    ) -> UUID:
        """파일 정리 시작 (백그라운드 실행, 조직화 ID 반환)"""

    @abstractmethod
    def cancel_organization(self, organization_id: UUID) -> bool:
        """파일 정리 취소"""

    @abstractmethod
    def get_organization_status(self, organization_id: UUID) -> OrganizationStatus | None:
        """파일 정리 상태 조회"""

    @abstractmethod
    def dispose(self) -> None:
        """서비스 정리"""


class FileOrganizationTask(BaseTask):
    """파일 정리 백그라운드 작업"""

    def __init__(
        self,
        organization_id: UUID,
        grouped_items: dict[str, Any],
        destination_directory: Path,
        event_bus: TypedEventBus,
        dry_run: bool = False,
    ):
        super().__init__(f"파일 정리: {destination_directory.name}")
        self.organization_id = organization_id
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.event_bus = event_bus
        self.dry_run = dry_run
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{organization_id}")
        self._cancelled = False

    def execute(self) -> TaskResult:
        """파일 정리 실행"""
        try:
            self.logger.info(f"파일 정리 작업 시작: {self.destination_directory}")
            start_time = time.time()

            # 결과 객체 초기화
            result = OrganizationResult()

            # 시작 이벤트 발행
            total_files = self._count_total_files(self.grouped_items)
            total_groups = len(self.grouped_items)

            self.event_bus.publish(
                OrganizationStartedEvent(
                    organization_id=self.organization_id,
                    destination_directory=self.destination_directory,
                    total_files=total_files,
                    total_groups=total_groups,
                )
            )

            result.total_count = total_files
            processed_files = 0

            # 각 그룹별로 파일 정리
            for _group_index, (group_name, group_data) in enumerate(self.grouped_items.items()):
                if self._cancelled:
                    break

                try:
                    self.logger.info(f"그룹 처리 중: {group_name}")

                    # 그룹 디렉토리 생성
                    group_dir = self.destination_directory / self._sanitize_filename(group_name)

                    if not self.dry_run:
                        group_dir.mkdir(parents=True, exist_ok=True)
                        result.created_directories.append(group_dir)

                    # 그룹 내 파일들 처리
                    files = group_data.get("files", [])
                    for _file_index, file_data in enumerate(files):
                        if self._cancelled:
                            break

                        try:
                            # 파일 정리 수행
                            success = self._organize_single_file(file_data, group_dir, result)

                            processed_files += 1
                            if success:
                                result.success_count += 1
                            else:
                                result.error_count += 1

                            # 진행률 이벤트 발행
                            progress_percent = int((processed_files / total_files) * 100)
                            self.event_bus.publish(
                                OrganizationProgressEvent(
                                    organization_id=self.organization_id,
                                    current_file=processed_files,
                                    total_files=total_files,
                                    current_group=group_name,
                                    operation_type="copy" if not self.dry_run else "validate",
                                    current_file_path=Path(file_data.get("source_path", "")),
                                    progress_percent=progress_percent,
                                )
                            )

                        except Exception as e:
                            self.logger.error(f"파일 처리 실패: {file_data}: {e}")
                            result.error_count += 1
                            result.errors.append(str(e))
                            processed_files += 1

                except Exception as e:
                    self.logger.error(f"그룹 처리 실패: {group_name}: {e}")
                    result.errors.append(f"그룹 '{group_name}' 처리 실패: {str(e)}")

            # 완료 처리
            result.operation_duration_seconds = time.time() - start_time

            if self._cancelled:
                self.event_bus.publish(
                    OrganizationCancelledEvent(
                        organization_id=self.organization_id,
                        cancellation_reason="사용자 요청",
                        partial_result=result,
                    )
                )
                return TaskResult(False, "사용자에 의해 취소됨", {"result": result})
            self.event_bus.publish(
                OrganizationCompletedEvent(
                    organization_id=self.organization_id,
                    result=result,
                    status=OrganizationStatus.ORGANIZATION_COMPLETED,
                )
            )
            return TaskResult(True, "파일 정리 완료", {"result": result})

        except Exception as e:
            self.logger.error(f"파일 정리 작업 실패: {e}")
            error_result = OrganizationResult(error_count=1, total_count=1)
            error_result.errors.append(str(e))

            self.event_bus.publish(
                OrganizationFailedEvent(
                    organization_id=self.organization_id,
                    error_type=OrganizationErrorType.UNKNOWN_ERROR,
                    error_message=str(e),
                    partial_result=error_result,
                )
            )
            return TaskResult(False, f"파일 정리 실패: {str(e)}", {"error": str(e)})

    def cancel(self) -> None:
        """작업 취소"""
        self._cancelled = True
        self.logger.info(f"파일 정리 작업 취소 요청: {self.organization_id}")

    def _count_total_files(self, grouped_items: dict[str, Any]) -> int:
        """전체 파일 수 계산"""
        total = 0
        for group_data in grouped_items.values():
            files = group_data.get("files", [])
            total += len(files)
        return total

    def _organize_single_file(
        self, file_data: dict[str, Any], group_dir: Path, result: OrganizationResult
    ) -> bool:
        """단일 파일 정리"""
        try:
            source_path = Path(file_data.get("source_path", ""))
            if not source_path.exists():
                result.errors.append(f"소스 파일이 존재하지 않음: {source_path}")
                result.failed_files.append(source_path)
                return False

            # 대상 파일명 생성
            target_filename = self._generate_target_filename(file_data)
            target_path = group_dir / target_filename

            # 파일 복사/이동 (dry_run이 아닌 경우)
            if not self.dry_run:
                if target_path.exists():
                    # 파일이 이미 존재하는 경우 처리
                    target_path = self._generate_unique_filename(target_path)

                shutil.copy2(source_path, target_path)
                result.processed_files.append(target_path)
            else:
                result.processed_files.append(target_path)

            return True

        except Exception as e:
            self.logger.error(f"단일 파일 정리 실패: {file_data}: {e}")
            result.errors.append(f"파일 정리 실패: {str(e)}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """파일명 정리 (금지 문자 제거)"""
        forbidden_chars = '<>:"/\\|?*'
        for char in forbidden_chars:
            filename = filename.replace(char, "_")
        return filename.strip()

    def _generate_target_filename(self, file_data: dict[str, Any]) -> str:
        """대상 파일명 생성"""
        # 파일 데이터에서 제목, 에피소드 등 정보 추출하여 파일명 생성
        title = file_data.get("title", "Unknown")
        episode = file_data.get("episode", "")
        source_path = Path(file_data.get("source_path", ""))

        if episode:
            filename = f"{title} - E{episode:02d}{source_path.suffix}"
        else:
            filename = f"{title}{source_path.suffix}"

        return self._sanitize_filename(filename)

    def _generate_unique_filename(self, target_path: Path) -> Path:
        """중복 파일명에 대한 고유 파일명 생성"""
        base = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        counter = 1
        while True:
            new_name = f"{base}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1


class FileOrganizationService(IFileOrganizationService):
    """파일 정리 서비스 구현"""

    def __init__(self, event_bus: TypedEventBus, background_task_service: IBackgroundTaskService):
        self.event_bus = event_bus
        self.background_task_service = background_task_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self._active_organizations: dict[UUID, UUID] = {}  # organization_id -> background_task_id

        self.logger.info("FileOrganizationService 초기화 완료")

    def validate_organization_request(
        self, grouped_items: dict[str, Any], destination_directory: Path
    ) -> OrganizationValidationResult:
        """파일 정리 요청 검증"""
        validation_id = uuid4()

        self.event_bus.publish(
            OrganizationValidationStartedEvent(
                organization_id=validation_id, destination_directory=destination_directory
            )
        )

        result = OrganizationValidationResult()

        try:
            # 그룹 데이터 검증
            if not grouped_items:
                result.validation_errors.append("정리할 그룹이 없습니다")
            else:
                result.has_grouped_items = True
                result.total_groups = len(grouped_items)
                result.total_files = sum(
                    len(group.get("files", [])) for group in grouped_items.values()
                )

            # 대상 디렉토리 검증
            if (
                not destination_directory
                or str(destination_directory) == "."
                or str(destination_directory) == ""
            ):
                result.validation_errors.append("대상 디렉토리가 설정되지 않았습니다")
            else:
                result.has_destination = True

                if not destination_directory.exists():
                    result.validation_errors.append("대상 디렉토리가 존재하지 않습니다")
                else:
                    result.destination_exists = True

                    # 쓰기 권한 확인
                    try:
                        test_file = destination_directory / ".animsorter_write_test"
                        test_file.touch()
                        test_file.unlink()
                        result.destination_writable = True
                    except Exception:
                        result.validation_errors.append("대상 디렉토리에 쓰기 권한이 없습니다")

            # 파일 크기 추정
            result.estimated_size_mb = self._estimate_total_size(grouped_items)

            # 전체 검증 결과
            result.is_valid = len(result.validation_errors) == 0

            self.event_bus.publish(
                OrganizationValidationCompletedEvent(
                    organization_id=validation_id, validation_result=result
                )
            )

            return result

        except Exception as e:
            self.logger.error(f"검증 중 오류 발생: {e}")
            self.event_bus.publish(
                OrganizationValidationFailedEvent(
                    organization_id=validation_id,
                    error_type=OrganizationErrorType.VALIDATION_ERROR,
                    error_message=str(e),
                    validation_errors=[str(e)],
                )
            )

            result.validation_errors.append(str(e))
            return result

    def create_preflight_data(
        self, grouped_items: dict[str, Any], destination_directory: Path
    ) -> OrganizationPreflightData:
        """프리플라이트 데이터 생성"""
        preflight_id = uuid4()

        try:
            self.event_bus.publish(OrganizationPreflightStartedEvent(organization_id=preflight_id))

            # 예상 작업 수 계산
            estimated_operations = sum(
                len(group.get("files", [])) for group in grouped_items.values()
            )

            # 예상 크기 계산
            estimated_size_mb = self._estimate_total_size(grouped_items)

            # 디스크 공간 확인
            disk_space_available_mb = self._get_available_disk_space(destination_directory)

            # 생성될 디렉토리 목록
            will_create_directories = [
                destination_directory / self._sanitize_filename(group_name)
                for group_name in grouped_items
            ]

            # 잠재적 충돌 검사
            potential_conflicts = self._check_potential_conflicts(
                grouped_items, destination_directory
            )

            preflight_data = OrganizationPreflightData(
                destination_directory=destination_directory,
                grouped_items=grouped_items,
                estimated_operations=estimated_operations,
                estimated_size_mb=estimated_size_mb,
                disk_space_available_mb=disk_space_available_mb,
                will_create_directories=will_create_directories,
                potential_conflicts=potential_conflicts,
            )

            self.event_bus.publish(
                OrganizationPreflightCompletedEvent(
                    organization_id=preflight_id,
                    user_approved=False,  # 아직 사용자 승인 전
                    preflight_data=preflight_data,
                )
            )

            return preflight_data

        except Exception as e:
            self.logger.error(f"프리플라이트 데이터 생성 실패: {e}")
            # 기본 데이터 반환
            return OrganizationPreflightData(
                destination_directory=destination_directory, grouped_items=grouped_items
            )

    def start_organization(
        self, grouped_items: dict[str, Any], destination_directory: Path, dry_run: bool = False
    ) -> UUID:
        """파일 정리 시작 (백그라운드 실행)"""
        organization_id = uuid4()
        self.logger.info(f"파일 정리 시작: {destination_directory} (조직화 ID: {organization_id})")

        # FileOrganizationTask 생성
        organization_task = FileOrganizationTask(
            organization_id=organization_id,
            grouped_items=grouped_items,
            destination_directory=destination_directory,
            event_bus=self.event_bus,
            dry_run=dry_run,
        )

        # 백그라운드 작업 제출
        background_task_id = self.background_task_service.submit_task(organization_task)
        self._active_organizations[organization_id] = background_task_id

        self.logger.info(
            f"파일 정리 작업 제출됨: {organization_id} (백그라운드 태스크 ID: {background_task_id})"
        )
        return organization_id

    def cancel_organization(self, organization_id: UUID) -> bool:
        """파일 정리 취소"""
        if organization_id not in self._active_organizations:
            self.logger.warning(f"취소할 파일 정리를 찾을 수 없음: {organization_id}")
            return False

        background_task_id = self._active_organizations[organization_id]
        success = self.background_task_service.cancel_task(background_task_id)

        if success:
            self.logger.info(f"파일 정리 취소 성공: {organization_id}")
            self._active_organizations.pop(organization_id)
        else:
            self.logger.warning(f"파일 정리 취소 실패: {organization_id}")

        return success

    def get_organization_status(self, organization_id: UUID) -> OrganizationStatus | None:
        """파일 정리 상태 조회"""
        if organization_id in self._active_organizations:
            return OrganizationStatus.ORGANIZATION_PROGRESS
        return None

    def dispose(self) -> None:
        """서비스 정리"""
        # 모든 활성 정리 작업 취소
        for organization_id in list(self._active_organizations.keys()):
            self.cancel_organization(organization_id)

        self.logger.info("FileOrganizationService 정리 완료")

    # ===== 헬퍼 메서드 =====

    def _estimate_total_size(self, grouped_items: dict[str, Any]) -> float:
        """전체 예상 크기 계산 (MB)"""
        total_size = 0.0
        for group_data in grouped_items.values():
            files = group_data.get("files", [])
            for file_data in files:
                source_path = Path(file_data.get("source_path", ""))
                try:
                    if source_path.exists():
                        total_size += source_path.stat().st_size
                except Exception:
                    pass  # 파일 크기를 가져올 수 없는 경우 무시

        return total_size / (1024 * 1024)  # 바이트를 MB로 변환

    def _get_available_disk_space(self, directory: Path) -> float:
        """사용 가능한 디스크 공간 (MB)"""
        try:
            stat = shutil.disk_usage(directory)
            return stat.free / (1024 * 1024)  # 바이트를 MB로 변환
        except Exception:
            return 0.0

    def _check_potential_conflicts(
        self, grouped_items: dict[str, Any], destination_directory: Path
    ) -> list[str]:
        """잠재적 충돌 검사"""
        conflicts = []

        for group_name in grouped_items:
            group_dir = destination_directory / self._sanitize_filename(group_name)
            if group_dir.exists() and any(group_dir.iterdir()):
                conflicts.append(f"그룹 디렉토리가 이미 존재하고 비어있지 않음: {group_name}")

        return conflicts

    def _sanitize_filename(self, filename: str) -> str:
        """파일명 정리 (금지 문자 제거)"""
        forbidden_chars = '<>:"/\\|?*'
        for char in forbidden_chars:
            filename = filename.replace(char, "_")
        return filename.strip()
