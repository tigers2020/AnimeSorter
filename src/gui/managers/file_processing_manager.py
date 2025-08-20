"""
파일 처리 관리자
파일 스캔, 파싱, 정리 계획 수립 등을 관리합니다.
"""

import os
import shutil

# 상대 경로로 수정
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from core.file_manager import FileManager
from core.file_parser import FileParser

from .anime_data_manager import ParsedItem


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
    """파일 처리 관리자"""

    def __init__(self, destination_root: str = "", safe_mode: bool = True):
        """초기화"""
        self.destination_root = destination_root
        self.safe_mode = safe_mode
        self.file_parser = FileParser()
        self.file_manager = FileManager(destination_root=destination_root, safe_mode=safe_mode)

        # 처리 계획 저장
        self.processing_plans: list[FileProcessingPlan] = []
        self.processing_stats = ProcessingStats()

        print("✅ FileProcessingManager 초기화 완료")

    def scan_directory(self, directory_path: str, recursive: bool = True) -> list[str]:
        """디렉토리 스캔하여 비디오 파일 찾기"""
        if not os.path.exists(directory_path):
            print(f"❌ 디렉토리가 존재하지 않습니다: {directory_path}")
            return []

        video_extensions = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
        video_files = []

        try:
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    for file in files:
                        if Path(file).suffix.lower() in video_extensions:
                            full_path = os.path.join(root, file)
                            video_files.append(full_path)
            else:
                for file in os.listdir(directory_path):
                    if Path(file).suffix.lower() in video_extensions:
                        full_path = os.path.join(directory_path, file)
                        video_files.append(full_path)

            print(f"🔍 디렉토리 스캔 완료: {len(video_files)}개 비디오 파일 발견")
            return video_files

        except Exception as e:
            print(f"❌ 디렉토리 스캔 오류: {e}")
            return []

    def parse_files(self, file_paths: list[str]) -> list[ParsedItem]:
        """파일들을 파싱하여 ParsedItem 리스트 생성"""
        if not file_paths:
            return []

        print(f"🔍 파일 파싱 시작: {len(file_paths)}개 파일")

        parsed_items = []
        for i, file_path in enumerate(file_paths):
            try:
                # 진행률 표시
                progress = int((i / len(file_paths)) * 100)
                print(f"진행률: {progress}% - {os.path.basename(file_path)}")

                # 파일 파싱
                parsed_metadata = self.file_parser.parse_filename(file_path)

                if parsed_metadata and parsed_metadata.title:
                    # 파일 크기 계산
                    file_size = os.path.getsize(file_path)
                    size_mb = file_size // (1024 * 1024)

                    # ParsedItem 생성
                    parsed_item = ParsedItem(
                        sourcePath=file_path,
                        detectedTitle=parsed_metadata.title,
                        title=parsed_metadata.title,
                        season=parsed_metadata.season or 1,
                        episode=parsed_metadata.episode or 1,
                        resolution=parsed_metadata.resolution or "Unknown",
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
                    print(f"❌ 파싱 실패: {os.path.basename(file_path)}")

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
        return parsed_items

    def create_processing_plans(
        self, parsed_items: list[ParsedItem], naming_scheme: str = "standard"
    ) -> list[FileProcessingPlan]:
        """파일 처리 계획 생성"""
        if not parsed_items:
            return []

        print(f"📋 처리 계획 생성 시작: {len(parsed_items)}개 아이템")

        self.processing_plans = []
        total_size = 0

        for item in parsed_items:
            if item.status == "error":
                continue

            try:
                # 대상 경로 생성
                target_path = self._generate_target_path(item, naming_scheme)

                # 백업 경로 생성 (안전 모드인 경우)
                backup_path = None
                if self.safe_mode and os.path.exists(target_path):
                    backup_path = self._generate_backup_path(target_path)

                # 파일 크기 계산
                file_size = (
                    os.path.getsize(item.sourcePath) if os.path.exists(item.sourcePath) else 0
                )
                size_mb = file_size // (1024 * 1024)
                total_size += size_mb

                # 충돌 확인
                conflicts = self._check_conflicts(target_path)

                # 처리 계획 생성
                plan = FileProcessingPlan(
                    source_path=item.sourcePath,
                    target_path=target_path,
                    action="copy" if self.safe_mode else "move",
                    backup_path=backup_path,
                    estimated_size=size_mb,
                    conflicts=conflicts,
                )

                self.processing_plans.append(plan)

            except Exception as e:
                print(f"❌ 계획 생성 오류: {item.sourcePath} - {e}")

        # 통계 업데이트
        self.processing_stats.total_files = len(self.processing_plans)
        self.processing_stats.total_size_mb = total_size
        self.processing_stats.estimated_time_seconds = self._estimate_processing_time(total_size)

        print(f"✅ 처리 계획 생성 완료: {len(self.processing_plans)}개 계획")
        return self.processing_plans

    def _generate_target_path(self, item: ParsedItem, naming_scheme: str) -> str:
        """대상 경로 생성"""
        if not self.destination_root:
            return item.sourcePath

        # 기본 디렉토리 구조
        base_dir = os.path.join(
            self.destination_root,
            item.title or "Unknown",
            f"Season {item.season:02d}" if item.season else "Unknown",
        )

        # 파일명 생성
        if naming_scheme == "standard":
            filename = f"{item.title} - S{item.season:02d}E{item.episode:02d}"
        elif naming_scheme == "compact":
            filename = f"S{item.season:02d}E{item.episode:02d}"
        else:
            filename = os.path.splitext(os.path.basename(item.sourcePath))[0]

        # 해상도 정보 추가
        if item.resolution and item.resolution != "Unknown":
            filename += f" [{item.resolution}]"

        # 확장자 추가
        extension = Path(item.sourcePath).suffix
        filename += extension

        # 전체 경로 생성
        target_path = os.path.join(base_dir, filename)

        return target_path

    def _generate_backup_path(self, original_path: str) -> str:
        """백업 경로 생성"""
        path = Path(original_path)
        backup_name = f"{path.stem}_backup_{int(os.time.time())}{path.suffix}"
        backup_path = path.parent / backup_name
        return str(backup_path)

    def _check_conflicts(self, target_path: str) -> list[str]:
        """파일 충돌 확인"""
        conflicts = []

        if os.path.exists(target_path):
            conflicts.append("파일이 이미 존재함")

        # 디렉토리 권한 확인
        target_dir = os.path.dirname(target_path)
        if not os.access(target_dir, os.W_OK):
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
        """파일 처리 실행 (병렬 처리 및 진행 콜백 지원)"""
        if not self.processing_plans:
            return {"error": "처리 계획이 없습니다"}

        if dry_run:
            print("🎭 드라이 런 모드로 파일 처리 실행")
        else:
            print("🚀 실제 파일 처리 실행")

        results = {"processed": [], "errors": [], "total_processed": 0, "total_errors": 0}

        total = len(self.processing_plans)
        processed_counter = 0
        lock = threading.Lock()

        def process_one(plan: FileProcessingPlan) -> tuple[bool, FileProcessingPlan, str | None]:
            try:
                if plan.conflicts:
                    return (False, plan, "충돌이 발생했습니다")
                if dry_run:
                    return (True, plan, None)
                ok = self._execute_single_plan(plan)
                return (ok, plan, None if ok else "파일 처리 실패")
            except Exception as e:
                return (False, plan, str(e))

        # 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_plan = {
                executor.submit(process_one, plan): plan for plan in self.processing_plans
            }
            for future in as_completed(future_to_plan):
                success, plan, error = future.result()
                with lock:
                    processed_counter += 1
                    progress = int((processed_counter / total) * 100)
                    if progress_callback:
                        progress_callback(progress)
                if success:
                    results["processed"].append(plan)
                    results["total_processed"] += 1
                else:
                    results["errors"].append(
                        {
                            "source": plan.source_path,
                            "target": plan.target_path,
                            "error": error or "알 수 없는 오류",
                        }
                    )
                    results["total_errors"] += 1

        # 통계 업데이트
        if not dry_run:
            self.processing_stats.processed_files = results["total_processed"]
            self.processing_stats.error_files = results["total_errors"]

        print(
            f"✅ 파일 처리 완료: {results['total_processed']}개 성공, {results['total_errors']}개 오류"
        )
        return results

    def _execute_single_plan(self, plan: FileProcessingPlan) -> bool:
        """단일 처리 계획 실행"""
        try:
            # 대상 디렉토리 생성
            target_dir = os.path.dirname(plan.target_path)
            os.makedirs(target_dir, exist_ok=True)

            # 백업 생성 (필요한 경우)
            if plan.backup_path and os.path.exists(plan.target_path):
                shutil.copy2(plan.target_path, plan.backup_path)
                print(f"💾 백업 생성: {plan.backup_path}")

            # 파일 처리
            if plan.action == "copy":
                shutil.copy2(plan.source_path, plan.target_path)
            elif plan.action == "move":
                shutil.move(plan.source_path, plan.target_path)

            print(
                f"✅ 파일 처리 완료: {os.path.basename(plan.source_path)} → {os.path.basename(plan.target_path)}"
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

            with open(filepath, "w", encoding="utf-8") as f:
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
                        os.path.getsize(item.sourcePath or item.path)
                        if os.path.exists(item.sourcePath or item.path)
                        else None
                    ),
                )

                # 충돌 검사
                if os.path.exists(target_path):
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
        filename = os.path.basename(item.sourcePath or item.path)

        # 대상 경로 조합
        target_path = os.path.join(self.destination_root, filename)

        return target_path
