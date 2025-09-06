"""
파일 정리 관련 로직을 담당하는 핸들러
"""

import os
from pathlib import Path

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog, QMessageBox

from ..components.organize_preflight_dialog import OrganizePreflightDialog


class FileOrganizationHandler(QObject):
    """파일 정리 관련 로직을 담당하는 핸들러"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def init_preflight_system(self):
        """Preflight System 초기화"""
        try:
            from app import IPreflightCoordinator, get_service

            # Preflight Coordinator 가져오기
            self.preflight_coordinator = get_service(IPreflightCoordinator)
            print(f"✅ PreflightCoordinator 연결됨: {id(self.preflight_coordinator)}")

        except Exception as e:
            print(f"⚠️ Preflight System 초기화 실패: {e}")
            self.preflight_coordinator = None

    def start_file_organization(self):
        """파일 정리 실행 시작"""
        try:
            import time

            # 중복 실행 방지 (강화된 보호)
            if hasattr(self, "_is_organizing") and self._is_organizing:
                print("⚠️ 파일 정리 작업이 이미 진행 중입니다")
                self.main_window.update_status_bar("파일 정리 작업이 이미 진행 중입니다")
                return

            if hasattr(self, "_last_organization_time"):
                current_time = time.time()
                time_diff = current_time - self._last_organization_time
                if time_diff < 2.0:  # 2초 이내 중복 요청 방지
                    print(f"⚠️ 너무 빠른 연속 요청 감지 ({time_diff:.1f}초)")
                    return

            self._is_organizing = True
            self._last_organization_time = time.time()

            # 기본 검증
            if not hasattr(self.main_window, "anime_data_manager"):
                QMessageBox.warning(
                    self.main_window, "경고", "스캔된 데이터가 없습니다. 먼저 파일을 스캔해주세요."
                )
                return

            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            if not grouped_items:
                QMessageBox.warning(
                    self.main_window, "경고", "정리할 그룹이 없습니다. 먼저 파일을 스캔해주세요."
                )
                return

            # 대상 폴더 확인
            if (
                not self.main_window.destination_directory
                or not Path(self.main_window.destination_directory).exists()
            ):
                QMessageBox.warning(
                    self.main_window, "경고", "대상 폴더가 설정되지 않았거나 존재하지 않습니다."
                )
                return

            # 간단한 확인
            reply = QMessageBox.question(
                self.main_window,
                "확인",
                f"{len(grouped_items)}개 그룹의 파일들을 정리하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.on_organize_proceed()

        except Exception as e:
            print(f"❌ 파일 정리 실행 시작 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

    def on_organize_proceed(self):
        """프리플라이트 확인 후 실제 정리 실행"""
        try:
            print("🚀 파일 정리 실행 시작")
            self.main_window.update_status_bar("파일 정리 실행 중...")

            # 그룹화된 아이템 가져오기
            grouped_items = self.main_window.anime_data_manager.get_grouped_items()

            # FileOrganizationService의 로직을 직접 사용하여 실행

            # 간단한 방식으로 FileOrganizationTask의 execute 로직을 직접 구현
            result = self._execute_file_organization_simple(grouped_items)

            self.on_organization_completed(result)

        except Exception as e:
            print(f"❌ 파일 정리 실행 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

    def _execute_file_organization_simple(self, grouped_items):
        """FileOrganizationService의 로직을 간단하게 구현"""
        from pathlib import Path

        from app.organization_events import OrganizationResult

        result = OrganizationResult()
        # 안전 가드: 누락 필드 초기화
        for name, default in [
            ("success_count", 0),
            ("error_count", 0),
            ("skip_count", 0),
            ("errors", []),
            ("skipped_files", []),
            ("cleaned_directories", 0),
            ("subtitle_count", 0),
        ]:
            if not hasattr(result, name):
                setattr(result, name, default)
        result._processed_sources = set()  # 중복 처리용 집합
        source_directories = set()  # 빈 디렉토리 정리용
        group_qualities = {}  # 그룹별 화질 정보 수집용

        print("=" * 50)
        print("🔍 DEBUG: 간단한 파일 정리 시작!")
        print(f"🔍 DEBUG: 총 그룹 수: {len(grouped_items)}")
        print(f"🔍 DEBUG: _processed_sources 초기화됨: {len(result._processed_sources)}")
        print("=" * 50)

        total_files = 0
        for group_data in grouped_items.values():
            if isinstance(group_data, list):
                total_files += len(group_data)
        result.total_count = total_files

        # 각 그룹별로 파일 처리
        for group_id, group_items in grouped_items.items():
            if group_id == "ungrouped":
                continue

            print(f"🔍 DEBUG: 그룹 '{group_id}' 처리 시작 - 파일 수: {len(group_items)}")

            # 그룹 내 파일들을 처리
            for item in group_items:
                try:
                    # 파일 경로 추출
                    if hasattr(item, "sourcePath"):
                        source_path = item.sourcePath
                    else:
                        continue

                    # 그룹 수집 시 전역 dedup 강제
                    norm = self._norm(source_path)  # 위와 동일한 _norm 함수 재사용
                    if norm in result._processed_sources:
                        print(f"⏭️ [중복파일] pre-collect skip: {norm}")
                        result.skip_count += 1
                        result.skipped_files.append(norm)
                        continue

                    # 파일 존재 확인
                    if not Path(source_path).exists():
                        print(f"🛑 [파일없음] 파일 존재하지 않음: {source_path}")
                        result.skip_count += 1
                        result.skipped_files.append(source_path)
                        result._processed_sources.add(norm)
                        continue

                    # 그룹 내 화질 분석 및 분류
                    import re
                    from pathlib import Path

                    # TMDB 매치 정보에서 제목 추출
                    safe_title = "Unknown"
                    season = 1

                    if hasattr(item, "tmdbMatch") and item.tmdbMatch and item.tmdbMatch.name:
                        raw_title = item.tmdbMatch.name
                    else:
                        raw_title = item.title or item.detectedTitle or "Unknown"

                    # 제목 정제 (특수문자 제거)
                    safe_title = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", raw_title)
                    safe_title = re.sub(r"\s+", " ", safe_title).strip()

                    if not safe_title:
                        safe_title = "Unknown"

                    # 시즌 정보 추출
                    if hasattr(item, "season") and item.season:
                        season = item.season

                    # 그룹 내 화질 분석 및 분류
                    group_key = f"{safe_title}_S{season}"
                    if group_key not in group_qualities:
                        group_qualities[group_key] = []

                    # 그룹 내부 dedup도 정규화 경로로
                    seen_in_group = {
                        self._norm(fi["normalized_path"])
                        for fi in group_qualities.get(group_key, [])
                    }
                    if norm in seen_in_group:
                        print(f"⏭️ [그룹중복] group-dup skip: {norm}")
                        result.skip_count += 1
                        result.skipped_files.append(norm)
                        continue

                    resolution = (
                        getattr(item, "resolution", "") or getattr(item, "fileResolution", "") or ""
                    )
                    resolution = resolution.lower()

                    # 그룹 내 파일들의 화질 정보 수집
                    group_qualities[group_key].append(
                        {
                            "item": item,
                            "resolution": resolution,
                            "source_path": source_path,
                            "normalized_path": norm,
                        }
                    )

                    # 이 파일은 나중에 그룹별로 처리하므로 여기서는 건너뜀
                    continue

                except Exception as e:
                    print(f"❌ 파일 처리 실패: {source_path} - {e}")
                    result.error_count += 1
                    result.errors.append(f"{source_path}: {e}")
                    result._processed_sources.add(norm)

        print("=" * 50)
        print("🔍 DEBUG: 파일 정리 최종 결과")
        print(f"   ✅ 성공: {result.success_count}개")
        print(f"   ❌ 실패: {result.error_count}개")
        print(f"   ⏭️  건너뜀: {result.skip_count}개")
        print(f"   📊 _processed_sources 최종 크기: {len(result._processed_sources)}개")
        print("=" * 50)

        # 그룹별 화질 분석 및 분류
        print("🎬 그룹별 화질 분석 시작...")
        self._process_groups_by_quality(group_qualities, result, source_directories)

        # 빈 디렉토리 정리
        if source_directories:
            print("🧹 빈 디렉토리 정리를 시작합니다...")
            cleaned_dirs = self._cleanup_empty_directories(source_directories)
            result.cleaned_directories = cleaned_dirs
            print(f"✅ 빈 디렉토리 정리 완료: {cleaned_dirs}개 디렉토리 삭제")

        # 애니 폴더 전체 정리 (추가)
        print("🗂️ 애니 폴더 전체 빈 디렉토리 정리를 시작합니다...")
        anime_cleaned = self._cleanup_anime_directories()
        print(f"🗑️ 애니 폴더 빈 디렉토리 정리 완료: {anime_cleaned}개 디렉토리 삭제")
        result.cleaned_directories += anime_cleaned

        return result

    def _process_subtitle_files(self, video_path: str, target_dir: Path, result):
        """비디오 파일과 연관된 자막 파일들을 처리합니다"""
        try:
            # 자막 카운터 초기화 보장
            if not hasattr(result, "subtitle_count"):
                result.subtitle_count = 0

            subtitle_files = self._find_subtitle_files(video_path)
            for subtitle_path in subtitle_files:
                try:
                    subtitle_filename = Path(subtitle_path).name
                    subtitle_target_path = target_dir / subtitle_filename
                    import shutil

                    shutil.move(subtitle_path, subtitle_target_path)
                    result.subtitle_count += 1
                    print(f"✅ 자막 이동 성공: {subtitle_filename}")
                except Exception as e:
                    print(f"❌ 자막 이동 실패: {subtitle_path} - {e}")
        except Exception as e:
            print(f"⚠️ 자막 파일 처리 중 오류: {e}")

    def _find_subtitle_files(self, video_path: str) -> list[str]:
        """비디오 파일과 연관된 자막 파일들을 찾습니다"""
        subtitle_files = []
        subtitle_extensions = {
            ".srt",
            ".ass",
            ".ssa",
            ".sub",
            ".vtt",
            ".idx",
            ".smi",
            ".sami",
            ".txt",
        }

        try:
            # 비디오 파일의 디렉토리와 기본명 추출
            video_dir = str(Path(video_path).parent)
            video_basename = Path(video_path).stem

            # 디렉토리 내 모든 파일 검사
            for file_path_obj in Path(video_dir).iterdir():
                if not file_path_obj.is_file():
                    continue

                # 자막 파일 확장자인지 확인
                file_ext = file_path_obj.suffix.lower()
                if file_ext not in subtitle_extensions:
                    continue

                # 파일명이 비디오 파일과 연관된 자막인지 확인
                subtitle_basename = file_path_obj.stem

                # 정확히 일치하는 경우
                if subtitle_basename == video_basename:
                    subtitle_files.append(str(file_path_obj))
                    continue

                # 비디오 파일명이 자막 파일명의 일부인 경우
                if video_basename in subtitle_basename:
                    subtitle_files.append(str(file_path_obj))
                    continue

        except Exception as e:
            print(f"⚠️ 자막 파일 검색 중 오류: {e}")

        return subtitle_files

    def _norm(self, path: str) -> str:
        """경로 정규화: 대소문자/유니코드/중복공백 통일"""
        import re
        import unicodedata
        from pathlib import Path

        s = str(Path(path))
        s = unicodedata.normalize("NFKC", s)  # 한글/기호 정규화
        s = re.sub(r"[ \t]+", " ", s)  # 중복 공백 축약
        return s.lower()  # Windows 대응(문자열 비교용)

    def _process_groups_by_quality(self, group_qualities: dict, result, source_directories: set):
        """그룹별로 화질을 분석하여 파일들을 분류하고 이동"""
        import shutil
        from pathlib import Path

        for group_key, files in group_qualities.items():
            if not files:
                continue

            print(f"🎬 그룹 '{group_key}' 화질 분석 시작 ({len(files)}개 파일)")
            print(f"🧪 plan: {len(files)} items in {group_key}")

            # 화질 우선순위 정의 (높은 숫자가 더 높은 화질)
            quality_priority = {
                "4k": 5,
                "2k": 4,
                "1440p": 3,
                "1080p": 2,
                "720p": 1,
                "480p": 0,
                "": -1,  # 해상도 미확인
            }

            # 그룹 내 파일들의 화질 분석
            file_qualities = []
            for file_info in files:
                resolution = file_info["resolution"]
                priority = quality_priority.get(resolution, -1)
                file_qualities.append({**file_info, "priority": priority})

            # 가장 높은 화질 찾기
            if file_qualities:
                highest_priority = max(fq["priority"] for fq in file_qualities)
                print(f"🎯 그룹 '{group_key}' 최고 화질 우선순위: {highest_priority}")

                # 화질별 분류
                for file_info in file_qualities:
                    try:
                        item = file_info["item"]
                        source_path = file_info["source_path"]
                        normalized_path = self._norm(source_path)  # 강화된 정규화
                        priority = file_info["priority"]
                        resolution = file_info["resolution"]

                        print(f"➡️ trying: {normalized_path}")

                        # 1) 이미 처리된 파일이면 즉시 스킵
                        if normalized_path in result._processed_sources:
                            print(f"⏭️ [중복처리] skip-duplicate(before-move): {normalized_path}")
                            result.skip_count += 1
                            result.skipped_files.append(normalized_path)
                            continue

                        # 2) 원본이 이미 사라졌으면(이전 move) 에러 대신 스킵
                        if not Path(source_path).exists():
                            print(
                                f"⏭️ [이동후소실] skip-missing(post-move-ghost): {normalized_path}"
                            )
                            result.skip_count += 1
                            result.skipped_files.append(normalized_path)
                            continue

                        # 3) optimistic mark: move 전에 '처리중'으로 잠금
                        result._processed_sources.add(normalized_path)

                        # 소스 디렉토리 추적 (빈 디렉토리 정리용)
                        source_dir = str(Path(source_path).parent)
                        source_directories.add(source_dir)

                        # 제목과 시즌 정보 추출
                        safe_title = "Unknown"
                        season = 1

                        if hasattr(item, "tmdbMatch") and item.tmdbMatch and item.tmdbMatch.name:
                            raw_title = item.tmdbMatch.name
                        else:
                            raw_title = item.title or item.detectedTitle or "Unknown"

                        # 제목 정제
                        import re

                        safe_title = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", raw_title)
                        safe_title = re.sub(r"\s+", " ", safe_title).strip()

                        if hasattr(item, "season") and item.season:
                            season = item.season

                        # 화질 분류
                        if priority == highest_priority:
                            # 고화질: 정상 폴더
                            season_folder = f"Season{season:02d}"
                            target_base_dir = (
                                Path(self.main_window.destination_directory)
                                / safe_title
                                / season_folder
                            )
                            quality_type = "고화질"
                        else:
                            # 저화질: _low res 폴더
                            season_folder = f"Season{season:02d}"
                            target_base_dir = (
                                Path(self.main_window.destination_directory)
                                / "_low res"
                                / safe_title
                                / season_folder
                            )
                            quality_type = "저화질"

                        target_base_dir.mkdir(parents=True, exist_ok=True)

                        # 파일 이동
                        filename = Path(source_path).name
                        target_path = target_base_dir / filename

                        try:
                            print(f"🚚 [{quality_type}] 파일 이동 시도: {Path(source_path).name}")
                            shutil.move(source_path, target_path)

                            print(
                                f"✅ [{quality_type}] 이동 성공: {Path(source_path).name} → {target_base_dir.name}/"
                            )
                            result.success_count += 1

                            # 자막 파일 처리
                            self._process_subtitle_files(source_path, target_base_dir, result)

                        except Exception as e:
                            # 실패 시 잠금 해제 (재시도 가능하도록)
                            result._processed_sources.discard(normalized_path)
                            result.error_count += 1
                            result.errors.append(f"{source_path}: {e}")
                            print(f"❌ [{quality_type}] 이동 실패: {Path(source_path).name} - {e}")

                    except Exception as e:
                        print(f"❌ 그룹 파일 이동 실패: {file_info['source_path']} - {e}")
                        result.error_count += 1
                        result.errors.append(f"{file_info['source_path']}: {e}")
                        result._processed_sources.add(file_info["normalized_path"])

    def _cleanup_empty_directories(self, source_directories: set[str]) -> int:
        """파일 이동 후 빈 디렉토리들을 정리합니다"""
        cleaned_count = 0

        for source_dir in source_directories:
            try:
                # 디렉토리가 존재하는지 확인
                if not Path(source_dir).exists():
                    continue

                # 재귀적으로 빈 디렉토리 삭제 (하위부터)
                cleaned_count += self._remove_empty_dirs_recursive(source_dir)

                # 상위 디렉토리까지 올라가면서 빈 디렉토리 삭제 (안전 경계선 적용)
                cleaned_count += self._cleanup_parent_directories(source_dir)

            except Exception as e:
                print(f"⚠️ 디렉토리 정리 중 오류 ({source_dir}): {e}")

        return cleaned_count

    def _remove_empty_dirs_recursive(self, directory: str) -> int:
        """재귀적으로 빈 디렉토리를 삭제합니다 (하위부터 상위로)"""
        cleaned_count = 0

        try:
            # 디렉토리 내 모든 항목 확인
            directory_path = Path(directory)
            items = list(directory_path.iterdir())

            # 하위 디렉토리들을 먼저 처리 (재귀)
            for item_path in items:
                if item_path.is_dir():
                    cleaned_count += self._remove_empty_dirs_recursive(str(item_path))

            # 현재 디렉토리가 비었는지 다시 확인 (하위 디렉토리 삭제 후)
            if not list(directory_path.iterdir()):
                try:
                    directory_path.rmdir()
                    cleaned_count += 1
                    print(f"🗑️ 빈 디렉토리 삭제: {directory}")
                except OSError as e:
                    # 권한 오류나 다른 이유로 삭제 실패
                    print(f"⚠️ 디렉토리 삭제 실패 ({directory}): {e}")

        except Exception as e:
            print(f"⚠️ 디렉토리 정리 중 오류 ({directory}): {e}")

        return cleaned_count

    def _cleanup_parent_directories(self, start_directory: str) -> int:
        """상위 디렉토리까지 올라가면서 빈 디렉토리를 삭제합니다 (안전 경계선 적용)"""
        cleaned_count = 0
        current_dir = Path(start_directory).parent

        # 안전 경계선: 시스템 드라이브 루트나 사용자 홈 디렉토리까지만 허용
        import os

        system_root = Path(os.path.abspath(os.sep))  # Windows: "C:\", Linux: "/"
        user_home = Path.home()

        while current_dir and current_dir != current_dir.parent:
            # 안전 경계선 체크: 시스템 루트나 사용자 홈을 넘지 않도록
            if (
                current_dir in [system_root, user_home]
                or system_root in current_dir.parents
                or user_home in current_dir.parents
            ):
                print(f"🛡️ 안전 경계선 도달, 상위 정리 중단: {current_dir}")
                break

            try:
                # 디렉토리가 존재하고 비어있는지 확인
                if current_dir.exists() and not list(current_dir.iterdir()):
                    current_dir.rmdir()
                    cleaned_count += 1
                    print(f"🗑️ 빈 상위 디렉토리 삭제: {current_dir}")
                    # 상위 디렉토리로 이동
                    current_dir = current_dir.parent
                else:
                    # 비어있지 않거나 존재하지 않으면 중단
                    break
            except OSError as e:
                print(f"⚠️ 상위 디렉토리 삭제 실패 ({current_dir}): {e}")
                break

        return cleaned_count

    def _cleanup_anime_directories(self) -> int:
        """애니 폴더 전체에서 빈 디렉토리들을 정리합니다"""
        cleaned_count = 0

        try:
            source_root = Path(self.main_window.source_directory)
            if not source_root.exists():
                print("⚠️ 소스 디렉토리가 존재하지 않습니다")
                return 0

            print(f"🗂️ 애니 폴더 스캔 시작: {source_root}")

            # 전체 폴더 트리를 재귀적으로 순회하며 빈 폴더 삭제
            for root, dirs, files in os.walk(str(source_root), topdown=False):
                # 하위 폴더부터 처리 (topdown=False)
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        # 디렉토리가 비어있는지 확인
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            print(f"🗑️ 빈 폴더 삭제: {dir_path}")
                            cleaned_count += 1
                    except Exception as e:
                        print(f"⚠️ 폴더 삭제 실패 ({dir_path}): {e}")

            print(f"🗑️ 애니 폴더 정리 완료: {cleaned_count}개 빈 디렉토리 삭제")

        except Exception as e:
            print(f"❌ 애니 폴더 정리 중 오류: {e}")

        return cleaned_count

    def on_organization_completed(self, result):
        """파일 정리 완료 처리"""
        try:
            # 결과 요약 메시지 생성
            message = "파일 정리가 완료되었습니다.\n\n"
            message += "📊 결과 요약:\n"
            message += f"• 성공: {result.success_count}개 파일\n"
            message += f"• 실패: {result.error_count}개 파일\n"
            message += f"• 건너뜀: {result.skip_count}개 파일\n\n"

            if result.errors:
                message += "❌ 오류 목록:\n"
                for i, error in enumerate(result.errors[:5], 1):  # 처음 5개만 표시
                    message += f"{i}. {error}\n"
                if len(result.errors) > 5:
                    message += f"... 및 {len(result.errors) - 5}개 더\n"
                message += "\n"

            if result.skipped_files:
                message += "⏭️ 건너뛴 파일:\n"
                for i, skipped in enumerate(result.skipped_files[:3], 1):  # 처음 3개만 표시
                    message += f"{i}. {skipped}\n"
                if len(result.skipped_files) > 3:
                    message += f"... 및 {len(result.skipped_files) - 3}개 더\n"
                message += "\n"

            # 결과 다이얼로그 표시 (theme 호환)
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("파일 정리 완료")
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Information)

            # Theme에 맞는 색상으로 stylesheet 설정
            palette = self.main_window.palette()
            bg_color = palette.color(palette.Window).name()
            text_color = palette.color(palette.WindowText).name()
            button_bg = palette.color(palette.Button).name()
            button_text = palette.color(palette.ButtonText).name()

            msg_box.setStyleSheet(
                f"""
                QMessageBox {{
                    background-color: {bg_color};
                    color: {text_color};
                }}
                QMessageBox QPushButton {{
                    background-color: {button_bg};
                    color: {button_text};
                    border: 1px solid {palette.color(palette.Mid).name()};
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 60px;
                }}
                QMessageBox QPushButton:hover {{
                    background-color: {palette.color(palette.Light).name()};
                }}
                QMessageBox QPushButton:pressed {{
                    background-color: {palette.color(palette.Dark).name()};
                }}
            """
            )

            msg_box.exec_()

            # 상태바 업데이트
            if result.success_count > 0:
                self.main_window.update_status_bar(
                    f"파일 정리 완료: {result.success_count}개 파일 이동 성공"
                )
            else:
                self.main_window.update_status_bar("파일 정리 완료 (성공한 파일 없음)")

            # 모델 리프레시 (필요한 경우)
            # TODO: 파일 이동 후 모델 업데이트 로직 구현

            print(
                f"✅ 파일 정리 완료: 성공 {result.success_count}, 실패 {result.error_count}, 건너뜀 {result.skip_count}"
            )

            # 작업 완료 플래그 해제
            self._is_organizing = False

        except Exception as e:
            print(f"❌ 파일 정리 완료 처리 실패: {e}")
            # 오류 발생 시에도 플래그 해제
            self._is_organizing = False
            self.main_window.update_status_bar(f"파일 정리 완료 처리 실패: {str(e)}")

    def commit_organization(self):
        """정리 실행"""
        self.start_file_organization()

    def simulate_organization(self):
        """정리 시뮬레이션"""
        QMessageBox.information(
            self.main_window, "시뮬레이션", "파일 이동을 시뮬레이션합니다. (구현 예정)"
        )

    def show_preview(self):
        """정리 미리보기 표시"""
        try:
            # 기본 검증
            if not hasattr(self.main_window, "anime_data_manager"):
                QMessageBox.warning(
                    self.main_window, "경고", "스캔된 데이터가 없습니다. 먼저 파일을 스캔해주세요."
                )
                return

            grouped_items = self.main_window.anime_data_manager.get_grouped_items()
            if not grouped_items:
                QMessageBox.warning(
                    self.main_window,
                    "경고",
                    "미리보기할 그룹이 없습니다. 먼저 파일을 스캔해주세요.",
                )
                return

            # 대상 폴더 확인
            if (
                not self.main_window.destination_directory
                or not Path(self.main_window.destination_directory).exists()
            ):
                QMessageBox.warning(
                    self.main_window, "경고", "대상 폴더가 설정되지 않았거나 존재하지 않습니다."
                )
                return

            # 미리보기 다이얼로그 표시
            dialog = OrganizePreflightDialog(
                grouped_items, self.main_window.destination_directory, self.main_window
            )
            dialog.setWindowTitle("정리 미리보기")

            # 미리보기 모드로 설정 (실제 정리 실행하지 않음)
            dialog.set_preview_mode(True)

            result = dialog.exec_()

            if result == QDialog.Accepted:
                print("✅ 미리보기 확인 완료")
                self.main_window.update_status_bar("미리보기 확인 완료")
            else:
                print("❌ 미리보기가 취소되었습니다")
                self.main_window.update_status_bar("미리보기가 취소되었습니다")

        except Exception as e:
            print(f"❌ 미리보기 표시 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"미리보기 표시 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"미리보기 표시 실패: {str(e)}")

    # 이벤트 핸들러 메서드들
    def handle_organization_started(self, event):
        """파일 정리 시작 이벤트 핸들러"""
        print(f"🚀 [FileOrganizationHandler] 파일 정리 시작: {event.organization_id}")
        self.main_window.update_status_bar("파일 정리 시작됨", 0)

    def handle_organization_progress(self, event):
        """파일 정리 진행률 이벤트 핸들러"""
        print(
            f"📊 [FileOrganizationHandler] 파일 정리 진행률: {event.progress_percent}% - {event.current_step}"
        )
        self.main_window.update_status_bar(
            f"파일 정리 중... {event.current_step}", event.progress_percent
        )

    def handle_organization_completed(self, event):
        """파일 정리 완료 이벤트 핸들러"""
        print(f"✅ [FileOrganizationHandler] 파일 정리 완료: {event.organization_id}")
        self.main_window.update_status_bar("파일 정리 완료됨", 100)
