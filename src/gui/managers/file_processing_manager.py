"""
파일 처리 관리자
파일 스캔, 파싱, 정리 계획 수립 등을 관리합니다.
리팩토링: 통합된 파일 조직화 서비스를 사용하여 중복 코드 제거
"""

import os
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

sys.path.append(str(Path(__file__).parent.parent.parent))

# Legacy FileManager import removed - using UnifiedFileOrganizationService instead
from src.app.file_processing_events import (FileOperationType,
                                            FileProcessingCompletedEvent,
                                            FileProcessingFailedEvent,
                                            FileProcessingProgressEvent,
                                            FileProcessingStartedEvent,
                                            calculate_progress_percentage)
from src.core.file_parser import FileParser
from src.core.interfaces.file_organization_interface import \
    FileConflictResolution
from src.core.services.unified_file_organization_service import (
    FileOperationPlan, FileOperationType, FileOrganizationConfig,
    UnifiedFileOrganizationService)
from src.core.video_metadata_extractor import VideoMetadataExtractor
from src.gui.managers.anime_data_manager import ParsedItem


@dataclass
class FileProcessingPlan:
    """파일 처리 계획"""

    source_path: str
    target_path: str
    action: str  # 'move', 'copy', 'rename'
    backup_path: str | None = None
    estimated_size: int | None = None
    conflicts: list[str] = None

    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


@dataclass
class ProcessingStats:
    """처리 통계"""

    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    total_size_mb: int = 0
    estimated_time_seconds: int = 0


class FileProcessingManager:
    """파일 처리 관리자 - 리팩토링된 버전"""

    def __init__(self, destination_root: str = "", safe_mode: bool = True, event_bus=None):
        """초기화"""
        self.destination_root = destination_root
        self.safe_mode = safe_mode
        self.event_bus = event_bus
        self.current_operation_id = None

        # 기존 컴포넌트들 (하위 호환성을 위해 유지)
        self.file_parser = FileParser()
        # Legacy FileManager removed - using UnifiedFileOrganizationService instead
        self.video_metadata_extractor = VideoMetadataExtractor()

        # 통합된 파일 조직화 서비스 초기화
        config = FileOrganizationConfig(
            safe_mode=safe_mode, backup_before_operation=safe_mode, overwrite_existing=not safe_mode
        )
        self.unified_service = UnifiedFileOrganizationService(config)

        # 처리 계획 저장 (기존 호환성 유지)
        self.processing_plans: list[FileProcessingPlan] = []
        self.processing_stats = ProcessingStats()

        print("✅ FileProcessingManager 초기화 완료 (리팩토링된 버전)")

    def scan_directory(self, directory_path: str, recursive: bool = True) -> list[str]:
        """디렉토리 스캔하여 비디오 파일 찾기 - 리팩토링된 버전"""
        try:
            # 통합된 서비스를 사용하여 스캔
            scan_result = self.unified_service.scanner.scan_directory(
                Path(directory_path), recursive=recursive
            )

            # 결과를 문자열 리스트로 변환 (기존 API 호환성 유지)
            video_files = [str(file_path) for file_path in scan_result.files_found]

            print(f"🔍 디렉토리 스캔 완료: {len(video_files)}개 비디오 파일 발견")
            if scan_result.errors:
                print(f"⚠️ 스캔 중 {len(scan_result.errors)}개 오류 발생")

            return video_files

        except Exception as e:
            print(f"❌ 디렉토리 스캔 오류: {e}")
            return []

    def parse_files(self, file_paths: list[str]) -> list[ParsedItem]:
        """파일들을 파싱하여 ParsedItem 리스트 생성"""
        if not file_paths:
            return []

        print(f"🔍 파일 파싱 시작: {len(file_paths)}개 파일")

        # Emit processing started event
        self.current_operation_id = uuid4()
        if self.event_bus:
            started_event = FileProcessingStartedEvent(
                operation_id=self.current_operation_id,
                operation_type="file_parsing",
                total_files=len(file_paths),
                total_size_bytes=sum(
                    Path(fp).stat().st_size for fp in file_paths if Path(fp).exists()
                ),
                processing_mode="normal",
            )
            self.event_bus.publish(started_event)

        parsed_items = []
        for i, file_path in enumerate(file_paths):
            try:
                # 진행률 표시
                progress = int((i / len(file_paths)) * 100)
                print(f"진행률: {progress}% - {Path(file_path).name}")

                # Emit progress event
                if self.event_bus:
                    progress_event = FileProcessingProgressEvent(
                        operation_id=self.current_operation_id,
                        current_file_index=i,
                        total_files=len(file_paths),
                        current_file_path=Path(file_path),
                        current_file_size=(
                            Path(file_path).stat().st_size if Path(file_path).exists() else 0
                        ),
                        progress_percentage=calculate_progress_percentage(i, len(file_paths)),
                        current_operation=FileOperationType.PARSE,
                        current_step=f"Parsing {Path(file_path).name}",
                        success_count=len(
                            [item for item in parsed_items if item.status != "error"]
                        ),
                        error_count=len([item for item in parsed_items if item.status == "error"]),
                    )
                    self.event_bus.publish(progress_event)

                # 파일 파싱
                parsed_metadata = self.file_parser.parse_filename(file_path)

                if parsed_metadata and parsed_metadata.title:
                    # 파일 크기 계산
                    file_size = Path(file_path).stat().st_size
                    size_mb = file_size // (1024 * 1024)

                    # 해상도 정보 사용 (TMDB에서 이미 가져온 정보가 있다면 그것을 사용)
                    resolution = parsed_metadata.resolution or "Unknown"

                    # ParsedItem 생성
                    parsed_item = ParsedItem(
                        sourcePath=file_path,
                        detectedTitle=parsed_metadata.title,
                        title=parsed_metadata.title,
                        season=parsed_metadata.season or 1,
                        episode=parsed_metadata.episode or 1,
                        resolution=resolution,
                        container=parsed_metadata.container or "Unknown",
                        codec=parsed_metadata.codec or "Unknown",
                        year=parsed_metadata.year,
                        group=parsed_metadata.group or "Unknown",
                        sizeMB=size_mb,
                        status="pending",
                        parsingConfidence=parsed_metadata.confidence or 0.0,
                    )
                    parsed_items.append(parsed_item)

                    print(
                        f"✅ 파싱 성공: {parsed_metadata.title} S{parsed_item.season:02d}E{parsed_item.episode:02d}"
                    )
                else:
                    # 파싱 실패
                    parsed_item = ParsedItem(
                        sourcePath=file_path,
                        detectedTitle="Unknown",
                        title="Unknown",
                        status="error",
                        parsingConfidence=0.0,
                    )
                    parsed_items.append(parsed_item)
                    print(f"❌ 파싱 실패: {Path(file_path).name}")

            except Exception as e:
                print(f"❌ 파일 처리 오류: {file_path} - {e}")
                # 에러 발생 시
                parsed_item = ParsedItem(
                    sourcePath=file_path,
                    detectedTitle="Error",
                    title="Error",
                    status="error",
                    parsingConfidence=0.0,
                )
                parsed_items.append(parsed_item)

        print(f"✅ 파일 파싱 완료: {len(parsed_items)}개 아이템 생성")

        # Emit processing completed event
        if self.event_bus:
            completed_event = FileProcessingCompletedEvent(
                operation_id=self.current_operation_id,
                total_files=len(file_paths),
                successful_files=len([item for item in parsed_items if item.status != "error"]),
                failed_files=len([item for item in parsed_items if item.status == "error"]),
                skipped_files=0,
                total_size_bytes=sum(
                    Path(fp).stat().st_size for fp in file_paths if Path(fp).exists()
                ),
                processed_size_bytes=sum(
                    Path(fp).stat().st_size for fp in file_paths if Path(fp).exists()
                ),
                total_processing_time_seconds=0.0,  # Could be calculated if needed
                errors=[item.sourcePath for item in parsed_items if item.status == "error"],
            )
            self.event_bus.publish(completed_event)

        return parsed_items

    def create_processing_plans(
        self, parsed_items: list[ParsedItem], naming_scheme: str = "standard"
    ) -> list[FileProcessingPlan]:
        """파일 처리 계획 생성 - 리팩토링된 버전"""
        if not parsed_items:
            return []

        print(f"📋 처리 계획 생성 시작: {len(parsed_items)}개 아이템")

        try:
            # 통합된 서비스를 사용하여 계획 생성
            source_paths = [
                Path(item.sourcePath) for item in parsed_items if item.status != "error"
            ]

            if not source_paths:
                print("⚠️ 처리 가능한 파일이 없습니다")
                return []

            # 통합된 서비스로 조직화 계획 생성
            unified_plans = self.unified_service.scan_and_plan_organization(
                source_paths[0].parent,  # 소스 디렉토리
                Path(self.destination_root),
                naming_scheme,
                FileOperationType.COPY if self.safe_mode else FileOperationType.MOVE,
            )

            # 기존 FileProcessingPlan 형식으로 변환 (하위 호환성)
            self.processing_plans = []
            total_size = 0

            for unified_plan in unified_plans:
                # ParsedItem에서 해당 파일 찾기
                matching_item = None
                for item in parsed_items:
                    if Path(item.sourcePath) == unified_plan.source_path:
                        matching_item = item
                        break

                if not matching_item:
                    continue

                # 충돌 확인
                conflicts = self._check_conflicts(str(unified_plan.target_path))

                # 기존 형식으로 변환
                plan = FileProcessingPlan(
                    source_path=str(unified_plan.source_path),
                    target_path=str(unified_plan.target_path),
                    action="copy" if self.safe_mode else "move",
                    backup_path=str(unified_plan.backup_path) if unified_plan.backup_path else None,
                    estimated_size=unified_plan.estimated_size // (1024 * 1024),  # MB로 변환
                    conflicts=conflicts,
                )

                self.processing_plans.append(plan)
                total_size += unified_plan.estimated_size

            # 통계 업데이트
            self.processing_stats.total_files = len(self.processing_plans)
            self.processing_stats.total_size_mb = total_size // (1024 * 1024)
            self.processing_stats.estimated_time_seconds = self._estimate_processing_time(
                total_size // (1024 * 1024)
            )

            print(f"✅ 처리 계획 생성 완료: {len(self.processing_plans)}개 계획")
            return self.processing_plans

        except Exception as e:
            print(f"❌ 처리 계획 생성 실패: {e}")
            return []

    def _generate_target_path(self, item: ParsedItem, naming_scheme: str) -> str:
        """대상 경로 생성"""
        if not self.destination_root:
            return item.sourcePath

        # 기본 디렉토리 구조
        base_dir = (
            Path(self.destination_root)
            / (item.title or "Unknown")
            / (f"Season {item.season:02d}" if item.season else "Unknown")
        )

        # 파일명 생성
        if naming_scheme == "standard":
            filename = f"{item.title} - S{item.season:02d}E{item.episode:02d}"
        elif naming_scheme == "compact":
            filename = f"S{item.season:02d}E{item.episode:02d}"
        else:
            filename = Path(item.sourcePath).stem

        # 해상도 정보 추가
        if item.resolution and item.resolution != "Unknown":
            filename += f" [{item.resolution}]"

        # 확장자 추가
        extension = Path(item.sourcePath).suffix
        filename += extension

        # 전체 경로 생성
        return str(base_dir / filename)

    def _generate_backup_path(self, original_path: str) -> str:
        """백업 경로 생성"""
        path = Path(original_path)
        backup_name = f"{path.stem}_backup_{int(time.time())}{path.suffix}"
        backup_path = path.parent / backup_name
        return str(backup_path)

    def _check_conflicts(self, target_path: str) -> list[str]:
        """파일 충돌 확인"""
        conflicts = []

        if Path(target_path).exists():
            conflicts.append("파일이 이미 존재함")

        # 디렉토리 권한 확인
        target_dir = Path(target_path).parent
        if not target_dir.exists() or not os.access(str(target_dir), os.W_OK):
            conflicts.append("디렉토리 쓰기 권한 없음")

        return conflicts

    def _estimate_processing_time(self, total_size_mb: int) -> int:
        """처리 시간 추정 (초 단위)"""
        # 평균 처리 속도: 100MB/초 (복사 기준)
        estimated_seconds = total_size_mb // 100

        # 최소 1초
        return max(1, estimated_seconds)

    def simulate_processing(self) -> dict[str, any]:
        """파일 처리 시뮬레이션"""
        if not self.processing_plans:
            return {"error": "처리 계획이 없습니다"}

        print("🎭 파일 처리 시뮬레이션 시작")

        simulation_results = {
            "total_files": len(self.processing_plans),
            "total_size_mb": self.processing_stats.total_size_mb,
            "estimated_time": self.processing_stats.estimated_time_seconds,
            "conflicts": [],
            "success_count": 0,
            "error_count": 0,
        }

        for plan in self.processing_plans:
            if plan.conflicts:
                simulation_results["conflicts"].append(
                    {
                        "source": plan.source_path,
                        "target": plan.target_path,
                        "conflicts": plan.conflicts,
                    }
                )
                simulation_results["error_count"] += 1
            else:
                simulation_results["success_count"] += 1

        print(
            f"✅ 시뮬레이션 완료: {simulation_results['success_count']}개 성공, {simulation_results['error_count']}개 충돌"
        )
        return simulation_results

    def execute_processing(
        self,
        dry_run: bool = True,
        progress_callback: Callable[[int], None] | None = None,
        max_workers: int = 4,
    ) -> dict[str, any]:
        """파일 처리 실행 - 리팩토링된 버전"""
        if not self.processing_plans:
            return {"error": "처리 계획이 없습니다"}

        try:
            # Emit processing started event
            self.current_operation_id = uuid4()
            if self.event_bus:
                started_event = FileProcessingStartedEvent(
                    operation_id=self.current_operation_id,
                    operation_type="file_organization",
                    total_files=len(self.processing_plans),
                    total_size_bytes=sum(
                        plan.estimated_size * 1024 * 1024
                        for plan in self.processing_plans
                        if plan.estimated_size
                    ),
                    processing_mode="dry_run" if dry_run else "normal",
                )
                self.event_bus.publish(started_event)

            # FileProcessingPlan을 FileOperationPlan으로 변환
            unified_plans = []
            for plan in self.processing_plans:
                if plan.conflicts:
                    continue  # 충돌이 있는 계획은 건너뜀

                operation_type = (
                    FileOperationType.COPY if plan.action == "copy" else FileOperationType.MOVE
                )

                unified_plan = FileOperationPlan(
                    source_path=Path(plan.source_path),
                    target_path=Path(plan.target_path),
                    operation_type=operation_type,
                    backup_path=Path(plan.backup_path) if plan.backup_path else None,
                    estimated_size=plan.estimated_size * 1024 * 1024,  # MB를 바이트로 변환
                    conflict_resolution=FileConflictResolution.RENAME,
                )
                unified_plans.append(unified_plan)

            # Create detailed progress callback
            def detailed_progress_callback(progress_event: FileProcessingProgressEvent):
                if self.event_bus:
                    self.event_bus.publish(progress_event)
                # Also call simple callback for backward compatibility
                if progress_callback:
                    progress_callback(int(progress_event.progress_percentage))

            # 통합된 서비스를 사용하여 실행
            if dry_run:
                print("🎭 드라이 런 모드로 파일 처리 실행")
                results = self.unified_service.execute_organization_plan(
                    unified_plans,
                    dry_run=True,
                    progress_callback=progress_callback,
                    detailed_progress_callback=detailed_progress_callback,
                )
            else:
                print("🚀 실제 파일 처리 실행")
                results = self.unified_service.execute_organization_plan(
                    unified_plans,
                    dry_run=False,
                    progress_callback=progress_callback,
                    detailed_progress_callback=detailed_progress_callback,
                )

            # 결과를 기존 형식으로 변환 (하위 호환성)
            processed = []
            errors = []
            total_processed = 0
            total_errors = 0

            for result in results:
                if result.success:
                    processed.append(
                        {
                            "source": str(result.source_path),
                            "target": str(result.target_path),
                            "operation": result.operation_type.value,
                        }
                    )
                    total_processed += 1
                else:
                    errors.append(
                        {
                            "source": str(result.source_path),
                            "target": str(result.target_path),
                            "error": result.error_message or "알 수 없는 오류",
                        }
                    )
                    total_errors += 1

            # 통계 업데이트
            if not dry_run:
                self.processing_stats.processed_files = total_processed
                self.processing_stats.error_files = total_errors

            print(f"✅ 파일 처리 완료: {total_processed}개 성공, {total_errors}개 오류")

            # Emit processing completed event
            if self.event_bus:
                completed_event = FileProcessingCompletedEvent(
                    operation_id=self.current_operation_id,
                    total_files=len(unified_plans),
                    successful_files=total_processed,
                    failed_files=total_errors,
                    skipped_files=0,
                    total_size_bytes=sum(
                        plan.estimated_size for plan in self.processing_plans if plan.estimated_size
                    )
                    * 1024
                    * 1024,
                    processed_size_bytes=sum(
                        plan.estimated_size for plan in self.processing_plans if plan.estimated_size
                    )
                    * 1024
                    * 1024,
                    total_processing_time_seconds=0.0,  # Could be calculated if needed
                    errors=[error.get("error", "Unknown error") for error in errors],
                )
                self.event_bus.publish(completed_event)

            return {
                "processed": processed,
                "errors": errors,
                "total_processed": total_processed,
                "total_errors": total_errors,
            }

        except Exception as e:
            print(f"❌ 파일 처리 실행 실패: {e}")

            # Emit processing failed event
            if self.event_bus:
                failed_event = FileProcessingFailedEvent(
                    operation_id=self.current_operation_id,
                    error_message=str(e),
                    error_type="execution_error",
                    failed_at_step="file_processing_execution",
                    processed_files_before_failure=0,
                    total_files=len(self.processing_plans),
                    can_retry=True,
                )
                self.event_bus.publish(failed_event)

            return {"error": f"파일 처리 실행 실패: {str(e)}"}

    def _execute_single_plan(self, plan: FileProcessingPlan) -> bool:
        """단일 처리 계획 실행"""
        try:
            # 대상 디렉토리 생성
            target_dir = Path(plan.target_path).parent
            target_dir.mkdir(parents=True, exist_ok=True)

            # 백업 생성 (필요한 경우)
            if plan.backup_path and Path(plan.target_path).exists():
                shutil.copy2(plan.target_path, plan.backup_path)
                print(f"💾 백업 생성: {plan.backup_path}")

            # 파일 처리
            if plan.action == "copy":
                shutil.copy2(plan.source_path, plan.target_path)
            elif plan.action == "move":
                shutil.move(plan.source_path, plan.target_path)

            print(
                f"✅ 파일 처리 완료: {Path(plan.source_path).name} → {Path(plan.target_path).name}"
            )
            return True

        except Exception as e:
            print(f"❌ 파일 처리 실패: {plan.source_path} - {e}")
            return False

    def get_processing_stats(self) -> ProcessingStats:
        """처리 통계 반환"""
        return self.processing_stats

    def clear_plans(self):
        """처리 계획 초기화"""
        self.processing_plans.clear()
        self.processing_stats = ProcessingStats()
        print("🗑️ 처리 계획 초기화 완료")

    def export_processing_report(self, filepath: str):
        """처리 계획을 파일로 내보내기"""
        try:
            report = {
                "stats": {
                    "total_files": self.processing_stats.total_files,
                    "total_size_mb": self.processing_stats.total_size_mb,
                    "estimated_time_seconds": self.processing_stats.estimated_time_seconds,
                },
                "plans": [],
            }

            for plan in self.processing_plans:
                plan_dict = {
                    "source_path": plan.source_path,
                    "target_path": plan.target_path,
                    "action": plan.action,
                    "backup_path": plan.backup_path,
                    "estimated_size": plan.estimated_size,
                    "conflicts": plan.conflicts,
                }
                report["plans"].append(plan_dict)

            import json

            with Path(filepath).open("w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print(f"✅ 처리 계획 내보내기 완료: {filepath}")

        except Exception as e:
            print(f"❌ 처리 계획 내보내기 실패: {e}")

    def create_processing_plan(
        self, parsed_items: list[ParsedItem], organize_mode: str = "move"
    ) -> list[FileProcessingPlan]:
        """파싱된 아이템들을 기반으로 처리 계획 생성"""
        if not parsed_items:
            return []

        print(f"📋 처리 계획 생성 시작: {len(parsed_items)}개 아이템")

        plans = []
        for item in parsed_items:
            try:
                # 대상 경로 생성
                target_path = self._generate_target_path(item)

                # 처리 계획 생성
                plan = FileProcessingPlan(
                    source_path=item.sourcePath or item.path,
                    target_path=target_path,
                    action=organize_mode,
                    estimated_size=(
                        Path(item.sourcePath or item.path).stat().st_size
                        if Path(item.sourcePath or item.path).exists()
                        else None
                    ),
                )

                # 충돌 검사
                if Path(target_path).exists():
                    plan.conflicts.append(f"대상 파일이 이미 존재함: {target_path}")

                plans.append(plan)

            except Exception as e:
                print(f"⚠️ 처리 계획 생성 실패 ({item.sourcePath or item.path}): {e}")

        self.processing_plans = plans
        self.processing_stats.total_files = len(plans)

        print(f"✅ 처리 계획 생성 완료: {len(plans)}개 계획")
        return plans

    def simulate_organization(
        self, parsed_items: list[ParsedItem], organize_mode: str = "move"
    ) -> dict:
        """파일 정리 시뮬레이션 실행"""
        print("🎭 파일 처리 시뮬레이션 시작")

        # 처리 계획 생성
        plans = self.create_processing_plan(parsed_items, organize_mode)

        # 시뮬레이션 결과
        simulation_results = {
            "total_files": len(plans),
            "successful": 0,
            "conflicts": 0,
            "errors": 0,
            "details": [],
        }

        for plan in plans:
            detail = {
                "source": plan.source_path,
                "target": plan.target_path,
                "action": plan.action,
                "status": "success" if not plan.conflicts else "conflict",
                "conflicts": plan.conflicts,
            }

            if plan.conflicts:
                simulation_results["conflicts"] += 1
            else:
                simulation_results["successful"] += 1

            simulation_results["details"].append(detail)

        print(
            f"✅ 시뮬레이션 완료: {simulation_results['successful']}개 성공, {simulation_results['conflicts']}개 충돌"
        )
        return simulation_results

    def _generate_target_path(self, item: ParsedItem) -> str:
        """대상 경로 생성"""
        if not self.destination_root:
            return item.sourcePath or item.path

        # 파일명 생성 (기본적으로 원본 파일명 사용)
        filename = Path(item.sourcePath or item.path).name

        # 대상 경로 조합
        return str(Path(self.destination_root) / filename)
