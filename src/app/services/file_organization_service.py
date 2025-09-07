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

from src.core.file_parser import FileParser

from src.app.background_task import BaseTask, TaskResult, TaskStatus
from src.app.events import TypedEventBus
from src.app.organization_events import (OrganizationCancelledEvent,
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
                                   OrganizationValidationStartedEvent)
from src.app.services.background_task_service import IBackgroundTaskService


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
        super().__init__(event_bus, f"파일 정리: {destination_directory.name}")
        self.organization_id = organization_id
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.event_bus = event_bus
        self.dry_run = dry_run
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{organization_id}")
        self._cancelled = False
        self.file_parser = FileParser()

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

            # 디버깅: 초기 상태 로깅
            self.logger.info(
                f"🚀 파일 정리 작업 시작 - 총 파일: {total_files}개, 총 그룹: {total_groups}개"
            )

            # _processed_sources 초기화 (중요!)
            if not hasattr(result, "_processed_sources"):
                result._processed_sources = set()
            else:
                # 이전 실행의 잔재가 남아있을 수 있으므로 초기화
                result._processed_sources.clear()

            self.logger.info(
                f"📊 초기화된 _processed_sources 상태: {len(result._processed_sources)}개"
            )
            print(f"🔍 DEBUG: 초기화된 _processed_sources 상태: {len(result._processed_sources)}개")
            print("=" * 50)
            print("🔍 DEBUG: 파일 정리 시작!")
            print(f"🔍 DEBUG: 총 파일 수: {total_files}")
            print(f"🔍 DEBUG: 총 그룹 수: {total_groups}")
            print(f"🔍 DEBUG: _processed_sources 초기화됨: {len(result._processed_sources)}")
            print("=" * 50)

            # 디버깅: 그룹 간 파일 중복 검사
            self._check_file_duplicates_across_groups()

            # 각 그룹별로 파일 정리 (최적화된 처리)
            for _group_index, (group_name, group_data) in enumerate(self.grouped_items.items()):
                if self._cancelled:
                    break

                try:
                    self.logger.info(f"📁 그룹 처리 중: {group_name}")

                    # 그룹 내 파일들 화질별 분류
                    files = group_data.get("files", [])
                    if not files:
                        continue

                    # 디버깅: 그룹 내 파일 목록 로깅
                    self.logger.debug(f"📋 그룹 '{group_name}' 파일 목록:")
                    for file_data in files:
                        source_path = file_data.get("source_path", "")
                        self.logger.debug(f"   - {source_path}")

                    # 유효한 파일만 필터링 (이미 처리된 파일 제외)
                    valid_files = []
                    skipped_in_group = []
                    for file_data in files:
                        source_path = file_data.get("source_path", "")
                        if not source_path:
                            continue

                        # 경로 정규화 (Windows 경로 문제 해결)
                        normalized_path = str(Path(source_path))

                        if normalized_path in result._processed_sources:
                            self.logger.warning(
                                f"⚠️ 그룹 '{group_name}'에서 이미 처리된 파일 건너뜀: {source_path}"
                            )
                            skipped_in_group.append(source_path)
                        else:
                            valid_files.append(file_data)

                    # 디버깅: 필터링 결과 로깅
                    self.logger.info(
                        f"📊 그룹 '{group_name}' 필터링 결과: 원본 {len(files)}개 → 유효 {len(valid_files)}개 → 건너뜀 {len(skipped_in_group)}개"
                    )
                    if skipped_in_group:
                        self.logger.info(f"⏭️ 건너뜀 파일들: {skipped_in_group}")

                    if not valid_files:
                        self.logger.info(f"⏭️ 그룹 '{group_name}'의 모든 파일이 이미 처리됨")
                        continue

                    # 디버깅: 그룹 처리 전 상태 상세 로깅
                    self.logger.info(f"📊 그룹 '{group_name}' 처리 전 상태:")
                    self.logger.info(f"   - _processed_sources: {len(result._processed_sources)}개")
                    self.logger.info(f"   - valid_files: {len(valid_files)}개")
                    print(
                        f"🔍 DEBUG: 그룹 '{group_name}' 처리 전 - _processed_sources: {len(result._processed_sources)}개, valid_files: {len(valid_files)}개"
                    )

                    # 실제 파일 존재 여부 검증
                    existing_files = 0
                    missing_files = 0
                    for file_data in valid_files:
                        source_path = file_data.get("source_path", "")
                        if Path(source_path).exists():
                            existing_files += 1
                        else:
                            missing_files += 1
                            self.logger.warning(
                                f"⚠️ 그룹 '{group_name}' 파일 존재하지 않음: {source_path}"
                            )
                            print(f"🔍 DEBUG: 파일 존재하지 않음: {source_path}")

                    self.logger.info(
                        f"   - 실제 존재 파일: {existing_files}개, 누락 파일: {missing_files}개"
                    )
                    print(
                        f"🔍 DEBUG: 그룹 '{group_name}' - 존재: {existing_files}개, 누락: {missing_files}개"
                    )

                    if missing_files > 0:
                        self.logger.warning(
                            f"🚨 그룹 '{group_name}'에 {missing_files}개 파일이 디스크에 존재하지 않음"
                        )
                        print(f"🔍 DEBUG: 그룹 '{group_name}'에 {missing_files}개 파일 누락됨")

                    # 화질별로 파일 분류 및 시즌별 정리 (스마트 분류)
                    high_quality_files = []
                    low_quality_files = []

                    # 파일명을 기준으로 그룹화하여 가장 높은 해상도를 고화질로 처리
                    file_groups = self._group_files_by_name(valid_files)

                    for base_name, files_in_group in file_groups.items():
                        if len(files_in_group) == 1:
                            # 같은 이름의 파일이 하나만 있으면 고화질로 취급
                            high_quality_files.append(files_in_group[0])
                            self.logger.debug(f"단일 파일 고화질 처리: {base_name}")
                        else:
                            # 같은 이름의 파일이 여러 개 있으면 가장 높은 해상도를 고화질로, 나머지는 저화질로
                            best_file = self._find_best_quality_file(files_in_group)
                            high_quality_files.append(best_file)

                            # 나머지 파일들은 저화질로
                            for file_data in files_in_group:
                                if file_data != best_file:
                                    low_quality_files.append(file_data)

                            self.logger.debug(
                                f"다중 파일 분류 완료: {base_name} - 고화질: {Path(best_file['source_path']).name}, 저화질: {len(files_in_group) - 1}개"
                            )

                    self.logger.info(
                        f"🔍 그룹 '{group_name}' 화질별 분류: 고화질 {len(high_quality_files)}개, 저화질 {len(low_quality_files)}개 (총 {len(valid_files)}개 유효)"
                    )
                    self.logger.debug(
                        f"📊 _processed_sources 상태: {len(result._processed_sources)}개 파일 처리됨"
                    )

                    # 고화질 파일들을 시즌별로 분류하여 배치
                    if high_quality_files:
                        self.logger.info(f"🎯 고화질 파일들 처리 시작: {len(high_quality_files)}개")
                        # 시즌별로 파일 분류 (직관적이고 효율적인 처리)
                        season_files = {}
                        for file_data in high_quality_files:
                            season = file_data.get("season", 1)

                            if season not in season_files:
                                season_files[season] = []
                            season_files[season].append(file_data)

                        # 각 시즌별로 디렉토리 생성 및 파일 처리
                        for season, season_file_list in season_files.items():
                            season_dir = (
                                self.destination_directory
                                / self._sanitize_filename(group_name)
                                / f"Season{season:02d}"
                            )
                            if not self.dry_run:
                                season_dir.mkdir(parents=True, exist_ok=True)
                                result.created_directories.append(season_dir)

                            # 해당 시즌의 파일들 처리
                            for file_data in season_file_list:
                                source_path = file_data.get("source_path", "")
                                self.logger.debug(f"🔄 고화질 파일 처리 시도: {source_path}")
                                success = self._organize_single_file(file_data, season_dir, result)
                                if success:
                                    result.success_count += 1
                                    self.logger.info(f"✅ 고화질 파일 이동 완료: {source_path}")
                                else:
                                    result.error_count += 1
                                    self.logger.warning(f"❌ 고화질 파일 이동 실패: {source_path}")
                                processed_files += 1

                    # 저화질 파일들을 시즌별로 분류하여 '_low res/' 서브디렉토리에 배치
                    if low_quality_files:
                        self.logger.info(f"🎯 저화질 파일들 처리 시작: {len(low_quality_files)}개")
                        # 시즌별로 파일 분류 (직관적이고 효율적인 처리)
                        season_files = {}
                        for file_data in low_quality_files:
                            season = file_data.get("season", 1)

                            if season not in season_files:
                                season_files[season] = []
                            season_files[season].append(file_data)

                        # 각 시즌별로 디렉토리 생성 및 파일 처리
                        for season, season_file_list in season_files.items():
                                season_dir = (
                                    self.destination_directory
                                    / self._sanitize_filename(group_name)
                                    / "_low res"
                                    / f"Season{season:02d}"
                                )
                                if not self.dry_run:
                                    season_dir.mkdir(parents=True, exist_ok=True)
                                    result.created_directories.append(season_dir)

                                # 해당 시즌의 파일들 처리
                                for file_data in season_file_list:
                                    source_path = file_data.get("source_path", "")
                                    self.logger.debug(f"🔄 저화질 파일 처리 시도: {source_path}")
                                    success = self._organize_single_file(
                                        file_data, season_dir, result
                                    )
                                    if success:
                                        result.success_count += 1
                                        self.logger.info(f"✅ 저화질 파일 이동 완료: {source_path}")
                                    else:
                                        result.error_count += 1
                                        self.logger.warning(
                                            f"❌ 저화질 파일 이동 실패: {source_path}"
                                        )
                                    processed_files += 1
                    else:
                        # 파일이 없는 경우 기본 그룹 디렉토리만 생성
                        group_dir = self.destination_directory / self._sanitize_filename(group_name)
                        if not self.dry_run:
                            group_dir.mkdir(parents=True, exist_ok=True)
                            result.created_directories.append(group_dir)

                    # 진행률 이벤트 발행
                    progress_percent = int((processed_files / total_files) * 100)
                    self.event_bus.publish(
                        OrganizationProgressEvent(
                            organization_id=self.organization_id,
                            current_file=processed_files,
                            total_files=total_files,
                            current_group=group_name,
                            operation_type="copy" if not self.dry_run else "validate",
                            current_file_path=Path(),  # 그룹 단위 진행률이므로 파일 경로는 비움
                            progress_percent=progress_percent,
                        )
                    )

                    # 디버깅: 그룹 처리 후 _processed_sources 상태
                    self.logger.debug(
                        f"📊 그룹 '{group_name}' 처리 후 _processed_sources: {len(result._processed_sources)}개"
                    )

                except Exception as e:
                    self.logger.error(f"그룹 처리 실패: {group_name}: {e}")
                    result.errors.append(f"그룹 '{group_name}' 처리 실패: {str(e)}")

            # 완료 처리
            result.operation_duration_seconds = time.time() - start_time

            # 최종 결과 요약 로그
            total_processed = result.success_count + result.error_count + result.skip_count
            success_rate = (
                (result.success_count / total_processed * 100) if total_processed > 0 else 0
            )

            self.logger.info("📊 파일 정리 최종 결과:")
            self.logger.info(f"   ✅ 성공: {result.success_count}개")
            self.logger.info(f"   ❌ 실패: {result.error_count}개")
            self.logger.info(f"   ⏭️  건너뜀: {result.skip_count}개")
            self.logger.info(f"   📈 성공률: {success_rate:.1f}% ({total_processed}개 처리)")
            self.logger.info(f"   📁 생성된 디렉토리: {len(result.created_directories)}개")
            self.logger.info(f"   ⏱️  소요시간: {result.operation_duration_seconds:.2f}초")
            self.logger.info(
                f"   📋 _processed_sources 최종 상태: {len(result._processed_sources)}개 파일"
            )
            self.logger.info(f"   📊 총 파일 수: {result.total_count}개")

            # 디버깅: 결과 검증
            if result.total_count != total_processed:
                self.logger.warning(
                    f"⚠️ 파일 수 불일치: 총 파일 {result.total_count}개 vs 처리된 파일 {total_processed}개"
                )
            else:
                self.logger.info(f"✅ 파일 수 일치: 총 {total_processed}개 파일 처리 완료")

            if self._cancelled:
                self.event_bus.publish(
                    OrganizationCancelledEvent(
                        organization_id=self.organization_id,
                        cancellation_reason="사용자 요청",
                        partial_result=result,
                    )
                )
                return TaskResult(
                    task_id=self.task_id,
                    status=TaskStatus.CANCELLED,
                    success=False,
                    result_data={"result": result},
                )
            self.event_bus.publish(
                OrganizationCompletedEvent(
                    organization_id=self.organization_id,
                    result=result,
                    status=OrganizationStatus.ORGANIZATION_COMPLETED,
                )
            )
            return TaskResult(
                task_id=self.task_id,
                status=TaskStatus.COMPLETED,
                success=True,
                result_data={"result": result},
            )

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
            return TaskResult(
                task_id=self.task_id,
                status=TaskStatus.FAILED,
                success=False,
                result_data={"error": str(e)},
            )

    def cancel(self, reason: str = "사용자 요청") -> None:
        """작업 취소"""
        self._cancelled = True
        self.logger.info(f"파일 정리 작업 취소 요청: {self.organization_id} (사유: {reason})")

    def _count_total_files(self, grouped_items: dict[str, Any]) -> int:
        """전체 파일 수 계산"""
        total = 0
        for group_data in grouped_items.values():
            files = group_data.get("files", [])
            total += len(files)
        return total

    def _check_file_duplicates_across_groups(self) -> None:
        """그룹 간 파일 중복 검사"""
        file_to_groups = {}
        total_duplicates = 0

        for group_name, group_data in self.grouped_items.items():
            files = group_data.get("files", [])
            for file_data in files:
                source_path = file_data.get("source_path", "")
                if source_path:
                    if source_path not in file_to_groups:
                        file_to_groups[source_path] = []
                    file_to_groups[source_path].append(group_name)

        # 중복 파일 찾기
        for source_path, groups in file_to_groups.items():
            if len(groups) > 1:
                self.logger.warning(f"⚠️ 파일 중복 발견: {source_path}")
                self.logger.warning(f"   속한 그룹들: {groups}")
                total_duplicates += 1

        if total_duplicates > 0:
            self.logger.warning(f"🚨 총 {total_duplicates}개 파일이 여러 그룹에 중복으로 속함")
        else:
            self.logger.info("✅ 그룹 간 파일 중복 없음")

    def _organize_single_file(
        self, file_data: dict[str, Any], group_dir: Path, result: OrganizationResult
    ) -> bool:
        """단일 파일 정리"""
        try:
            source_path = Path(file_data.get("source_path", ""))
            normalized_path = str(source_path)

            # 이미 처리된 파일인지 확인 (중복 처리 방지)
            if (
                hasattr(result, "_processed_sources")
                and normalized_path in result._processed_sources
            ):
                self.logger.warning(f"🛑 이미 처리된 파일 건너뜀: {source_path}")
                self.logger.debug(
                    f"📊 현재 _processed_sources 크기: {len(result._processed_sources)}"
                )
                result.skip_count += 1
                result.skipped_files.append(str(source_path))
                return True

            # 파일 존재 여부 확인 (캐시된 결과 활용)
            if not source_path.exists():
                # 파일이 이미 이동되었거나 존재하지 않는 경우
                self.logger.debug(f"🛑 파일이 이미 이동되었거나 존재하지 않음: {source_path}")
                print(f"🔍 DEBUG: 파일 존재하지 않음 - {source_path}")
                result.skip_count += 1
                result.skipped_files.append(str(source_path))
                # 처리된 파일 목록에 추가하여 재처리 방지
                if not hasattr(result, "_processed_sources"):
                    result._processed_sources = set()
                result._processed_sources.add(normalized_path)
                print(f"🔍 DEBUG: _processed_sources에 추가됨: {normalized_path}")
                return True

            # 대상 파일명 생성
            target_filename = self._generate_target_filename(file_data)
            target_path = group_dir / target_filename

            # 파일 복사/이동 (dry_run이 아닌 경우)
            if not self.dry_run:
                if target_path.exists():
                    # 파일이 이미 존재하는 경우 처리
                    target_path = self._generate_unique_filename(target_path)

                # 파일 복사
                shutil.copy2(source_path, target_path)
                result.processed_files.append(target_path)

                # 원본 파일 삭제 (복사 성공 후)
                try:
                    source_path.unlink()
                    self.logger.debug(f"원본 파일 삭제 완료: {source_path}")
                except Exception as e:
                    self.logger.warning(f"원본 파일 삭제 실패: {source_path} - {e}")

                # 처리된 파일 목록에 추가 (중복 처리 방지)
                if not hasattr(result, "_processed_sources"):
                    result._processed_sources = set()
                result._processed_sources.add(normalized_path)

            else:
                result.processed_files.append(target_path)
                # dry_run 모드에서도 처리된 파일 목록에 추가
                if not hasattr(result, "_processed_sources"):
                    result._processed_sources = set()
                result._processed_sources.add(normalized_path)

            return True

        except Exception as e:
            self.logger.error(f"단일 파일 정리 실패: {file_data}: {e}")
            result.errors.append(f"파일 정리 실패: {str(e)}")
            return False

    def _generate_target_filename(self, file_data: dict[str, Any]) -> str:
        """대상 파일명 생성"""
        # 파일 데이터에서 제목, 에피소드, 시즌 등 정보 추출하여 파일명 생성
        title = file_data.get("title", "Unknown")
        episode = file_data.get("episode", "")
        season = file_data.get("season", 1)  # 시즌 정보 추가
        source_path = Path(file_data.get("source_path", ""))

        if episode:
            filename = f"{title} - S{season:02d}E{episode:02d}{source_path.suffix}"
        else:
            filename = f"{title} - S{season:02d}{source_path.suffix}"

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

    def _sanitize_filename(self, filename: str) -> str:
        """파일명 정리 (금지 문자 제거)"""
        forbidden_chars = '<>:"/\\|?*'
        for char in forbidden_chars:
            filename = filename.replace(char, "_")
        return filename.strip()


class FileOrganizationService(IFileOrganizationService):
    """파일 정리 서비스 구현"""

    def __init__(self, event_bus: TypedEventBus, background_task_service: IBackgroundTaskService):
        self.event_bus = event_bus
        self.background_task_service = background_task_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self._active_organizations: dict[UUID, str] = {}  # organization_id -> background_task_id

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

    def _group_files_by_name(self, files: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        """파일명을 기준으로 파일들을 그룹화"""
        file_groups = {}

        for file_data in files:
            source_path = file_data.get("source_path", "")
            if not source_path:
                continue

            # 파일명에서 확장자를 제외한 기본 이름 추출
            path_obj = Path(source_path)
            base_name = path_obj.stem  # 확장자 제외한 파일명

            # 그룹에 추가
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_data)

        return file_groups

    def _find_best_quality_file(self, files: list[dict[str, Any]]) -> dict[str, Any]:
        """그룹 내에서 가장 높은 해상도의 파일을 찾음"""
        if not files:
            return None

        if len(files) == 1:
            return files[0]

        # 해상도 우선순위로 정렬 (높은 우선순위가 먼저)
        sorted_files = sorted(
            files,
            key=lambda f: self._get_resolution_priority(f.get("resolution", "")),
            reverse=True  # 내림차순 (높은 우선순위가 먼저)
        )

        return sorted_files[0]  # 가장 높은 우선순위의 파일 반환

    def _get_resolution_priority(self, resolution: str) -> int:
        """해상도의 우선순위를 반환 (높을수록 우선순위 높음)"""
        resolution_priority = {
            "4K": 100,
            "1440p": 90,
            "1080p": 80,
            "2K": 70,
            "720p": 60,
            "480p": 50,
        }

        # 대소문자 무시하고 우선순위 반환
        resolution_upper = resolution.upper() if resolution else ""
        return resolution_priority.get(resolution_upper, 0)  # 기본값 0 (알 수 없는 해상도)

    def _sanitize_filename(self, filename: str) -> str:
        """파일명 정리 (금지 문자 제거)"""
        forbidden_chars = '<>:"/\\|?*'
        for char in forbidden_chars:
            filename = filename.replace(char, "_")
        return filename.strip()
