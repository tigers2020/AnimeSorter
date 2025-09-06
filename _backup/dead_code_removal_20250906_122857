"""
전역 예외 핸들러

애플리케이션 전체에서 처리되지 않은 예외를 안전하게 처리하는 시스템입니다.
Qt 예외 핸들러, Python 예외 핸들러 설정, 크래시 리포트 생성을 포함합니다.
"""

import contextlib
import sys
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMessageBox

from .error_bus import (ErrorCategory, ErrorRecoveryStrategy, ErrorSeverity,
                        error_bus)


class CrashReport:
    """크래시 리포트 클래스"""

    def __init__(self, exception: Exception, traceback_str: str):
        self.timestamp = datetime.now()
        self.exception_type = type(exception).__name__
        self.exception_message = str(exception)
        self.traceback = traceback_str
        self.system_info = self._collect_system_info()
        self.app_info = self._collect_app_info()

    def _collect_system_info(self) -> dict:
        """시스템 정보 수집"""
        import platform

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "system": platform.system(),
            "release": platform.release(),
        }

    def _collect_app_info(self) -> dict:
        """애플리케이션 정보 수집"""
        app = QApplication.instance()
        if app:
            return {
                "app_name": app.applicationName(),
                "app_version": app.applicationVersion(),
                "app_pid": app.applicationPid(),
                "qt_version": app.property("qt_version") or "Unknown",
            }
        return {"app_name": "Unknown", "app_version": "Unknown"}

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "traceback": self.traceback,
            "system_info": self.system_info,
            "app_info": self.app_info,
        }

    def to_text(self) -> str:
        """텍스트 형식으로 변환"""
        lines = [
            "=== 크래시 리포트 ===",
            f"시간: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"예외 타입: {self.exception_type}",
            f"예외 메시지: {self.exception_message}",
            "",
            "=== 시스템 정보 ===",
            f"플랫폼: {self.system_info['platform']}",
            f"Python 버전: {self.system_info['python_version']}",
            f"Python 구현: {self.system_info['python_implementation']}",
            f"시스템: {self.system_info['system']} {self.system_info['release']}",
            f"머신: {self.system_info['machine']}",
            "",
            "=== 애플리케이션 정보 ===",
            f"앱 이름: {self.app_info['app_name']}",
            f"앱 버전: {self.app_info['app_version']}",
            f"프로세스 ID: {self.app_info.get('app_pid', 'Unknown')}",
            f"Qt 버전: {self.app_info.get('qt_version', 'Unknown')}",
            "",
            "=== 스택 트레이스 ===",
            self.traceback,
        ]
        return "\n".join(lines)


class GlobalExceptionHandler(QObject):
    """전역 예외 핸들러"""

    # 시그널 정의
    unhandled_exception = pyqtSignal(object)  # Exception
    crash_report_generated = pyqtSignal(object)  # CrashReport

    def __init__(self, app: QApplication | None = None):
        super().__init__()
        self.app = app or QApplication.instance()
        self.original_excepthook = sys.excepthook
        self.original_qt_exception_handler = None
        self.crash_report_dir = Path.home() / ".animesorter" / "crash_reports"
        self.crash_report_dir.mkdir(parents=True, exist_ok=True)

        # 예외 처리 콜백
        self.exception_callbacks: list[Callable] = []

        # 크래시 리포트 설정
        self.max_crash_reports = 10
        self.auto_save_crash_reports = True

        # 초기화
        self._setup_exception_handling()

    def _setup_exception_handling(self):
        """예외 처리 설정"""
        try:
            # Python 전역 예외 핸들러 설정
            sys.excepthook = self._python_exception_handler

            # Qt 예외 핸들러 설정
            self._setup_qt_exception_handler()

            # 기존 핸들러 백업
            self._backup_existing_handlers()

            print("✅ 전역 예외 핸들러 설정 완료")

        except Exception as e:
            print(f"❌ 전역 예외 핸들러 설정 실패: {e}")

    def _setup_qt_exception_handler(self):
        """Qt 예외 핸들러 설정"""
        try:
            # Qt의 예외 처리 설정
            if hasattr(self.app, "setAttribute"):
                # Qt::AA_EnableHighDpiScaling 등과 함께 사용
                pass

            # Qt 메시지 핸들러 설정 (Qt 5.5+)
            if hasattr(self.app, "installEventFilter"):
                # 이벤트 필터를 통한 예외 처리
                pass

        except Exception as e:
            print(f"⚠️ Qt 예외 핸들러 설정 실패: {e}")

    def _backup_existing_handlers(self):
        """기존 핸들러 백업"""
        try:
            # sys.excepthook 백업
            if hasattr(sys, "excepthook") and sys.excepthook != self._python_exception_handler:
                self.original_excepthook = sys.excepthook

            # Qt 예외 핸들러 백업 (가능한 경우)
            if hasattr(self.app, "_qt_exception_handler"):
                self.original_qt_exception_handler = self.app._qt_exception_handler

        except Exception as e:
            print(f"⚠️ 기존 핸들러 백업 실패: {e}")

    def _python_exception_handler(
        self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any
    ):
        """Python 전역 예외 핸들러"""
        try:
            # 예외 정보 수집
            exception = exc_value if exc_value else exc_type()
            traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

            print("🚨 처리되지 않은 예외 발생:")
            print(f"  타입: {exc_type.__name__}")
            print(f"  메시지: {str(exception)}")

            # ErrorBus를 통한 에러 처리 (BaseException을 Exception으로 캐스팅)
            if isinstance(exception, Exception):
                error_bus.handle_exception(
                    exception,
                    severity=ErrorSeverity.CRITICAL,
                    category=ErrorCategory.SYSTEM,
                    title="처리되지 않은 예외",
                    user_message="애플리케이션에서 예상치 못한 오류가 발생했습니다",
                    developer_message=f"예외 타입: {exc_type.__name__}, 메시지: {str(exception)}",
                    recovery_strategy=ErrorRecoveryStrategy.TERMINATE,
                )

            # 크래시 리포트 생성 (BaseException을 Exception으로 캐스팅)
            if isinstance(exception, Exception):
                crash_report = CrashReport(exception, traceback_str)
            else:
                # BaseException의 경우 기본 정보로 CrashReport 생성
                crash_report = CrashReport(
                    Exception(f"BaseException: {type(exception).__name__}: {str(exception)}"),
                    traceback_str,
                )
            self._save_crash_report(crash_report)

            # 시그널 발생
            self.unhandled_exception.emit(exception)
            self.crash_report_generated.emit(crash_report)

            # 사용자에게 알림
            self._show_crash_dialog(crash_report)

            # 예외 콜백 실행 (BaseException을 Exception으로 캐스팅)
            if isinstance(exception, Exception):
                self._execute_exception_callbacks(exception, crash_report)
            else:
                # BaseException의 경우 기본 Exception으로 변환하여 콜백 실행
                self._execute_exception_callbacks(
                    Exception(f"BaseException: {type(exception).__name__}: {str(exception)}"),
                    crash_report,
                )

            # 기존 핸들러 호출 (백업된 경우)
            if (
                self.original_excepthook is not None
                and self.original_excepthook != self._python_exception_handler
            ):
                with contextlib.suppress(Exception):
                    self.original_excepthook(exc_type, exc_value, exc_traceback)

        except Exception as e:
            print(f"❌ Python 예외 핸들러에서 오류 발생: {e}")
            # 최후의 수단: 원래 핸들러 호출
            if (
                self.original_excepthook is not None
                and self.original_excepthook != self._python_exception_handler
            ):
                with contextlib.suppress(Exception):
                    self.original_excepthook(exc_type, exc_value, exc_traceback)

    def _show_crash_dialog(self, crash_report: CrashReport):
        """크래시 다이얼로그 표시"""
        try:
            if self.app and hasattr(self.app, "activeWindow") and self.app.activeWindow():
                # 메인 윈도우가 있는 경우에만 다이얼로그 표시
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("애플리케이션 오류")
                msg_box.setText("예상치 못한 오류가 발생했습니다.")
                msg_box.setInformativeText(
                    f"오류 타입: {crash_report.exception_type}\n"
                    f"오류 메시지: {crash_report.exception_message}\n\n"
                    f"크래시 리포트가 저장되었습니다: {crash_report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                msg_box.setDetailedText(crash_report.to_text())
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.exec_()
            else:
                # GUI가 없는 경우 콘솔 출력
                print("\n" + "=" * 50)
                print("🚨 애플리케이션 크래시 발생!")
                print("=" * 50)
                print(crash_report.to_text())
                print("=" * 50)

        except Exception as e:
            print(f"❌ 크래시 다이얼로그 표시 실패: {e}")

    def _save_crash_report(self, crash_report: CrashReport):
        """크래시 리포트 저장"""
        try:
            if not self.auto_save_crash_reports:
                return

            # 파일명 생성
            timestamp_str = crash_report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"crash_report_{timestamp_str}.txt"
            file_path = self.crash_report_dir / filename

            # 텍스트 파일로 저장
            with file_path.open("w", encoding="utf-8") as f:
                f.write(crash_report.to_text())

            # JSON 파일로도 저장
            json_filename = f"crash_report_{timestamp_str}.json"
            json_file_path = self.crash_report_dir / json_filename

            import json

            with json_file_path.open("w", encoding="utf-8") as f:
                json.dump(crash_report.to_dict(), f, ensure_ascii=False, indent=2)

            print("✅ 크래시 리포트 저장 완료:")
            print(f"  텍스트: {file_path}")
            print(f"  JSON: {json_file_path}")

            # 오래된 크래시 리포트 정리
            self._cleanup_old_crash_reports()

        except Exception as e:
            print(f"❌ 크래시 리포트 저장 실패: {e}")

    def _cleanup_old_crash_reports(self):
        """오래된 크래시 리포트 정리"""
        try:
            crash_files = list(self.crash_report_dir.glob("crash_report_*"))
            crash_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # 최대 개수 초과 시 오래된 파일 삭제
            if len(crash_files) > self.max_crash_reports:
                files_to_delete = crash_files[self.max_crash_reports :]
                for file_path in files_to_delete:
                    try:
                        file_path.unlink()
                        print(f"  삭제된 오래된 크래시 리포트: {file_path.name}")
                    except Exception as e:
                        print(f"  크래시 리포트 삭제 실패: {file_path.name} - {e}")

        except Exception as e:
            print(f"⚠️ 크래시 리포트 정리 실패: {e}")

    def _execute_exception_callbacks(self, exception: Exception, crash_report: CrashReport):
        """예외 콜백 실행"""
        for callback in self.exception_callbacks:
            try:
                callback(exception, crash_report)
            except Exception as e:
                print(f"⚠️ 예외 콜백 실행 실패: {e}")

    def add_exception_callback(self, callback: Callable[[Exception, CrashReport], None]):
        """예외 콜백 추가"""
        if callback not in self.exception_callbacks:
            self.exception_callbacks.append(callback)
            print(
                f"✅ 예외 콜백 추가: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}"
            )

    def remove_exception_callback(self, callback: Callable[[Exception, CrashReport], None]):
        """예외 콜백 제거"""
        if callback in self.exception_callbacks:
            self.exception_callbacks.remove(callback)
            print(
                f"✅ 예외 콜백 제거: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}"
            )

    def get_crash_report_list(self) -> list[Path]:
        """크래시 리포트 목록 반환"""
        try:
            crash_files = list(self.crash_report_dir.glob("crash_report_*.txt"))
            crash_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return crash_files
        except Exception as e:
            print(f"❌ 크래시 리포트 목록 조회 실패: {e}")
            return []

    def get_crash_report_content(self, file_path: Path) -> str | None:
        """크래시 리포트 내용 반환"""
        try:
            with file_path.open(encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"❌ 크래시 리포트 읽기 실패: {e}")
            return None

    def clear_crash_reports(self):
        """모든 크래시 리포트 삭제"""
        try:
            crash_files = list(self.crash_report_dir.glob("crash_report_*"))
            deleted_count = 0

            for file_path in crash_files:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"  크래시 리포트 삭제 실패: {file_path.name} - {e}")

            print(f"✅ 크래시 리포트 정리 완료: {deleted_count}개 파일 삭제")

        except Exception as e:
            print(f"❌ 크래시 리포트 정리 실패: {e}")

    def restore_original_handlers(self):
        """원래 핸들러 복원"""
        try:
            # Python 예외 핸들러 복원
            if self.original_excepthook:
                sys.excepthook = self.original_excepthook
                print("✅ Python 예외 핸들러 복원 완료")

            # Qt 예외 핸들러 복원 (가능한 경우)
            if self.original_qt_exception_handler and hasattr(self.app, "_qt_exception_handler"):
                self.app._qt_exception_handler = self.original_qt_exception_handler
                print("✅ Qt 예외 핸들러 복원 완료")

        except Exception as e:
            print(f"❌ 원래 핸들러 복원 실패: {e}")

    def __del__(self):
        """소멸자"""
        with contextlib.suppress(Exception):
            self.restore_original_handlers()


# 전역 예외 핸들러 인스턴스
global_exception_handler: GlobalExceptionHandler | None = None


def initialize_global_exception_handler(
    app: QApplication | None = None,
) -> GlobalExceptionHandler:
    """전역 예외 핸들러 초기화"""
    global global_exception_handler

    if global_exception_handler is None:
        global_exception_handler = GlobalExceptionHandler(app)
        print("✅ 전역 예외 핸들러 초기화 완료")

    return global_exception_handler


def get_global_exception_handler() -> GlobalExceptionHandler | None:
    """전역 예외 핸들러 인스턴스 반환"""
    return global_exception_handler


def add_exception_callback(callback: Callable[[Exception, "CrashReport"], None]):
    """전역 예외 콜백 추가"""
    if global_exception_handler:
        global_exception_handler.add_exception_callback(callback)


def remove_exception_callback(callback: Callable[[Exception, "CrashReport"], None]):
    """전역 예외 콜백 제거"""
    if global_exception_handler:
        global_exception_handler.remove_exception_callback(callback)


# 편의 함수들
def handle_unhandled_exception(
    exception: Exception, show_dialog: bool = True, save_report: bool = True
) -> Optional["CrashReport"]:
    """처리되지 않은 예외 수동 처리"""
    if global_exception_handler:
        # 크래시 리포트 생성
        traceback_str = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )
        crash_report = CrashReport(exception, traceback_str)

        if save_report:
            global_exception_handler._save_crash_report(crash_report)

        if show_dialog:
            global_exception_handler._show_crash_dialog(crash_report)

        return crash_report

    return None


def get_crash_report_list() -> list[Path]:
    """크래시 리포트 목록 반환"""
    if global_exception_handler:
        return global_exception_handler.get_crash_report_list()
    return []


def clear_all_crash_reports():
    """모든 크래시 리포트 삭제"""
    if global_exception_handler:
        global_exception_handler.clear_crash_reports()
