"""
파일 정리 진행률 다이얼로그 및 백그라운드 Worker
파일 이동 작업을 QThread로 수행하고 진행률을 표시합니다.
"""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import QMutex, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


@dataclass
class OrganizeResult:
    """파일 정리 결과"""

    success_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    subtitle_count: int = 0
    cleaned_directories: int = 0  # 정리된 빈 디렉토리 수
    errors: list[str] = None
    skipped_files: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.skipped_files is None:
            self.skipped_files = []


class FileOrganizeWorker(QThread):
    """파일 정리 백그라운드 Worker"""

    # 시그널 정의
    progress_updated = pyqtSignal(int, str)  # 진행률, 현재 파일
    file_processed = pyqtSignal(str, str, bool)  # 파일명, 결과 메시지, 성공 여부
    completed = pyqtSignal(object)  # OrganizeResult

    def __init__(self, grouped_items: dict[str, list], destination_directory: str):
        super().__init__()
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.cancelled = False
        self.mutex = QMutex()

        # 자막 파일 확장자 정의
        self.subtitle_extensions = {
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

    def run(self):
        """Worker 실행"""
        try:
            result = OrganizeResult()
            total_files = 0
            processed_files = 0
            source_directories = set()  # 소스 디렉토리 추적

            # 전체 파일 수 계산 (비디오 파일만)
            for group_id, group_items in self.grouped_items.items():
                if group_id == "ungrouped":
                    continue
                total_files += len(group_items)

            if total_files == 0:
                self.completed.emit(result)
                return

            # 각 그룹별로 파일 처리
            for group_id, group_items in self.grouped_items.items():
                if group_id == "ungrouped":
                    continue

                # 취소 확인
                self.mutex.lock()
                if self.cancelled:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()

                # 그룹 대표 파일에서 정보 추출
                if not group_items:
                    continue

                representative = group_items[0]

                # 제목 정제 및 경로 길이 검증
                safe_title = self._sanitize_title(representative)
                if not safe_title:
                    error_msg = f"제목 정제 실패: 그룹 {group_id}"
                    result.errors.append(error_msg)
                    result.error_count += len(group_items)
                    processed_files += len(group_items)
                    continue

                # 시즌 정보
                season = representative.season or 1
                season_folder = f"Season{season:02d}"

                # 대상 디렉토리 경로 생성 및 검증
                target_base_dir = str(Path(self.destination_directory) / safe_title / season_folder)

                # 경로 길이 검증 (Windows 260자 제한, 여유분 20자)
                if len(target_base_dir) > 240:
                    error_msg = f"경로가 너무 깁니다 ({len(target_base_dir)}자): {target_base_dir}"
                    result.errors.append(error_msg)
                    result.error_count += len(group_items)
                    processed_files += len(group_items)
                    continue

                # 대상 디렉토리 생성
                try:
                    Path(target_base_dir).mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    error_msg = f"권한 오류: 디렉토리 생성 실패 - {target_base_dir}"
                    result.errors.append(error_msg)
                    result.error_count += len(group_items)
                    processed_files += len(group_items)
                    continue
                except OSError as e:
                    error_msg = f"디렉토리 생성 실패: {target_base_dir} - {str(e)}"
                    result.errors.append(error_msg)
                    result.error_count += len(group_items)
                    processed_files += len(group_items)
                    continue

                # 그룹 내 각 파일 처리
                for item in group_items:
                    # 취소 확인
                    self.mutex.lock()
                    if self.cancelled:
                        self.mutex.unlock()
                        break
                    self.mutex.unlock()

                    # 소스 파일 경로 확인
                    if not hasattr(item, "sourcePath") or not item.sourcePath:
                        result.skip_count += 1
                        result.skipped_files.append(f"Unknown file in {group_id}")
                        processed_files += 1
                        continue

                    source_path = item.sourcePath
                    if not Path(source_path).exists():
                        error_msg = f"소스 파일이 존재하지 않음: {source_path}"
                        result.errors.append(error_msg)
                        result.error_count += 1
                        self.file_processed.emit(Path(source_path).name, error_msg, False)
                        processed_files += 1
                        continue

                    # 소스 디렉토리 추적
                    source_dir = str(Path(source_path).parent)
                    source_directories.add(source_dir)

                    filename = Path(source_path).name
                    target_path = str(Path(target_base_dir) / filename)

                    try:
                        # 파일 이동
                        self._safe_move_file(source_path, target_path)
                        result.success_count += 1
                        self.file_processed.emit(filename, f"이동 완료: {target_path}", True)

                        # 자막 파일 찾기 및 이동
                        subtitle_files = self._find_subtitle_files(source_path)

                        for subtitle_path in subtitle_files:
                            try:
                                subtitle_filename = Path(subtitle_path).name
                                subtitle_target_path = self._resolve_target_path(
                                    target_base_dir, subtitle_filename
                                )

                                # 자막 파일 경로 길이 검증
                                if len(subtitle_target_path) > 260:
                                    error_msg = (
                                        f"자막 파일 경로가 너무 깁니다: {subtitle_target_path}"
                                    )
                                    result.errors.append(error_msg)
                                    continue

                                # 자막 파일 이동
                                self._safe_move_file(subtitle_path, subtitle_target_path)
                                result.subtitle_count += 1
                                self.file_processed.emit(
                                    subtitle_filename,
                                    f"자막 이동 완료: {subtitle_target_path}",
                                    True,
                                )

                            except Exception as e:
                                error_msg = f"자막 파일 이동 실패: {subtitle_path} - {str(e)}"
                                result.errors.append(error_msg)
                                self.file_processed.emit(Path(subtitle_path).name, error_msg, False)

                        if not subtitle_files:
                            pass  # Removed debug print

                    except PermissionError:
                        error_msg = f"권한 오류: 파일 이동 실패 - {source_path}"
                        result.errors.append(error_msg)
                        result.error_count += 1
                        self.file_processed.emit(filename, error_msg, False)
                    except OSError as e:
                        error_msg = f"파일 이동 실패: {source_path} -> {target_path} - {str(e)}"
                        result.errors.append(error_msg)
                        result.error_count += 1
                        self.file_processed.emit(filename, error_msg, False)
                    except Exception as e:
                        error_msg = f"예상치 못한 오류: {source_path} - {str(e)}"
                        result.errors.append(error_msg)
                        result.error_count += 1
                        self.file_processed.emit(filename, error_msg, False)

                    processed_files += 1
                    progress = int((processed_files / total_files) * 100)
                    self.progress_updated.emit(progress, f"처리 중: {filename}")

                # 취소 확인
                self.mutex.lock()
                if self.cancelled:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()

            # 파일 이동 완료 후 빈 디렉토리 정리
            if not self.cancelled and source_directories:
                print("🧹 빈 디렉토리 정리를 시작합니다...")
                cleaned_dirs = self._cleanup_empty_directories(source_directories)
                result.cleaned_directories = cleaned_dirs
                print(f"✅ 빈 디렉토리 정리 완료: {cleaned_dirs}개 디렉토리 삭제")

            # 완료 시그널 발생
            self.completed.emit(result)

        except Exception as e:
            error_msg = f"Worker 실행 중 오류: {str(e)}"
            result = OrganizeResult()
            result.errors.append(error_msg)
            result.error_count = 1
            self.completed.emit(result)

    def cancel(self):
        """작업 취소"""
        self.mutex.lock()
        self.cancelled = True
        self.mutex.unlock()

    def _find_subtitle_files(self, video_path: str) -> list[str]:
        """비디오 파일과 연관된 자막 파일들을 찾습니다"""
        subtitle_files = []

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
                if file_ext not in self.subtitle_extensions:
                    continue

                # 파일명이 비디오 파일과 연관된 자막인지 확인
                subtitle_basename = file_path_obj.stem

                # 이미 추가된 파일인지 확인 (중복 방지)
                if str(file_path_obj) in subtitle_files:
                    continue

                # 정확히 일치하는 경우
                if subtitle_basename == video_basename:
                    subtitle_files.append(str(file_path_obj))
                    continue

                # 부분 일치하는 경우 (예: video.mkv와 video.ko.srt)
                if subtitle_basename.startswith(video_basename + "."):
                    subtitle_files.append(str(file_path_obj))
                    continue

                # 특수 패턴 매칭 (예: video.mkv와 video.ass)
                # 자막 파일명에서 비디오 파일명을 포함하는 경우
                if video_basename in subtitle_basename and subtitle_basename != video_basename:
                    subtitle_files.append(str(file_path_obj))
                    continue

            return subtitle_files

        except Exception as e:
            print(f"⚠️ 자막 파일 검색 중 오류: {e}")
            return []

    def _sanitize_title(self, representative):
        """제목 정제 및 검증"""
        try:
            # 제목 추출
            if (
                hasattr(representative, "tmdbMatch")
                and representative.tmdbMatch
                and representative.tmdbMatch.name
            ):
                raw_title = representative.tmdbMatch.name
            else:
                raw_title = representative.title or representative.detectedTitle or "Unknown"

            # 특수문자 제거 및 정제 (알파벳, 숫자, 한글, 공백만 허용)
            safe_title = re.sub(r"[^a-zA-Z0-9가-힣\s]", "", raw_title)
            # 연속된 공백을 하나로 치환
            safe_title = re.sub(r"\s+", " ", safe_title)
            # 앞뒤 공백 제거
            safe_title = safe_title.strip()

            if not safe_title:
                safe_title = "Unknown"

            # 제목 길이 제한 (폴더명이 너무 길면 문제가 될 수 있음)
            if len(safe_title) > 100:
                safe_title = safe_title[:100].strip()

            return safe_title

        except Exception as e:
            print(f"⚠️ 제목 정제 실패: {e}")
            return None

    def _resolve_target_path(self, target_base_dir, filename):
        """대상 경로 결정 및 충돌 처리"""
        target_path = str(Path(target_base_dir) / filename)

        # 파일명 충돌 처리
        counter = 1
        original_target_path = target_path
        while Path(target_path).exists():
            name, ext = Path(original_target_path).stem, Path(original_target_path).suffix
            target_path = f"{name} ({counter}){ext}"
            counter += 1

            # 무한 루프 방지
            if counter > 1000:
                break

        return target_path

    def _safe_move_file(self, source_path, target_path):
        """안전한 파일 이동"""
        try:
            # 기본 이동 시도
            shutil.move(source_path, target_path)
        except OSError as e:
            # 네트워크 드라이브나 교차 디스크 이동의 경우
            if "cross-device" in str(e).lower() or "invalid cross-device" in str(e).lower():
                # 복사 후 삭제 방식으로 처리
                shutil.copy2(source_path, target_path)
                Path(source_path).unlink()
            else:
                raise

    def _cleanup_empty_directories(self, source_directories: set[str]) -> int:
        """파일 이동 후 빈 디렉토리들을 정리합니다"""
        cleaned_count = 0

        for source_dir in source_directories:
            try:
                # 디렉토리가 존재하는지 확인
                if not Path(source_dir).exists():
                    continue

                # 재귀적으로 빈 디렉토리 삭제
                cleaned_count += self._remove_empty_dirs_recursive(source_dir)

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


class OrganizeProgressDialog(QDialog):
    """파일 정리 진행률 다이얼로그"""

    def __init__(self, grouped_items: dict[str, list], destination_directory: str, parent=None):
        super().__init__(parent)
        self.grouped_items = grouped_items
        self.destination_directory = destination_directory
        self.worker = None
        self.result = None
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("📁 파일 정리 진행 중")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 제목
        title_label = QLabel("파일 정리 중...")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("진행률: %p%")
        layout.addWidget(self.progress_bar)

        # 현재 파일 정보
        self.current_file_label = QLabel("대기 중...")
        self.current_file_label.setWordWrap(True)
        self.current_file_label.setStyleSheet(
            """
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """
        )
        layout.addWidget(self.current_file_label)

        # 로그 영역
        log_label = QLabel("처리 로그:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9px;
            }
        """
        )
        layout.addWidget(self.log_text)

        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 취소 버튼
        self.cancel_button = QPushButton("❌ 취소")
        self.cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """
        )
        self.cancel_button.clicked.connect(self.cancel_operation)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def start_organization(self):
        """파일 정리 시작"""
        try:
            # Worker 생성 및 시작
            self.worker = FileOrganizeWorker(self.grouped_items, self.destination_directory)
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.file_processed.connect(self.log_file_processed)
            self.worker.completed.connect(self.on_organization_completed)

            self.worker.start()

        except Exception as e:
            self.log_text.append(f"❌ 오류: {str(e)}")
            self.cancel_button.setText("닫기")

    def update_progress(self, progress: int, current_file: str):
        """진행률 업데이트"""
        self.progress_bar.setValue(progress)
        self.current_file_label.setText(current_file)

    def log_file_processed(self, filename: str, message: str, success: bool):
        """파일 처리 로그"""
        if success:
            self.log_text.append(f"✅ {filename}: {message}")
        else:
            self.log_text.append(f"❌ {filename}: {message}")

        # 스크롤을 맨 아래로
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def cancel_operation(self):
        """작업 취소"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("취소 중...")
            self.log_text.append("🔄 작업 취소 중...")
        else:
            self.accept()

    def on_organization_completed(self, result: OrganizeResult):
        """정리 작업 완료"""
        self.result = result

        # 완료 메시지 표시
        if result.success_count > 0:
            self.log_text.append(f"✅ 정리 완료: {result.success_count}개 파일 이동 성공")

        if result.subtitle_count > 0:
            self.log_text.append(f"📝 자막 파일: {result.subtitle_count}개 자막 파일 이동 성공")

        if result.cleaned_directories > 0:
            self.log_text.append(
                f"🗑️ 빈 디렉토리: {result.cleaned_directories}개 디렉토리 정리 완료"
            )

        if result.error_count > 0:
            self.log_text.append(f"❌ 오류: {result.error_count}개 파일 처리 실패")

        if result.skip_count > 0:
            self.log_text.append(f"⏭️ 건너뜀: {result.skip_count}개 파일")

        # 버튼 변경
        self.cancel_button.setText("확인")
        self.cancel_button.setEnabled(True)
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)

        # 진행률 100%로 설정
        self.progress_bar.setValue(100)
        self.current_file_label.setText("정리 작업이 완료되었습니다")

    def get_result(self) -> OrganizeResult | None:
        """결과 반환"""
        return self.result
