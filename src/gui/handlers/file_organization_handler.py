"""
파일 정리 관련 로직을 담당하는 핸들러
"""

from pathlib import Path

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QDialog, QMessageBox

from ..components.organize_preflight_dialog import OrganizePreflightDialog
from ..components.organize_progress_dialog import OrganizeProgressDialog


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

            # 프리플라이트 다이얼로그 표시
            dialog = OrganizePreflightDialog(
                grouped_items, self.main_window.destination_directory, self.main_window
            )
            dialog.proceed_requested.connect(self.on_organize_proceed)

            result = dialog.exec_()

            if result == QDialog.Accepted:
                print("✅ 프리플라이트 확인 완료 - 파일 정리 실행 준비")
            else:
                print("❌ 파일 정리 실행이 취소되었습니다")
                self.main_window.update_status_bar("파일 정리 실행이 취소되었습니다")

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

            # 진행률 다이얼로그 생성 및 실행
            progress_dialog = OrganizeProgressDialog(
                grouped_items, self.main_window.destination_directory, self.main_window
            )
            progress_dialog.start_organization()

            result = progress_dialog.exec_()

            if result == QDialog.Accepted:
                # 결과 가져오기
                organize_result = progress_dialog.get_result()
                if organize_result:
                    self.on_organization_completed(organize_result)
                else:
                    print("⚠️ 파일 정리 결과를 가져올 수 없습니다")
                    self.main_window.update_status_bar("파일 정리 완료 (결과 확인 불가)")
            else:
                print("❌ 파일 정리가 취소되었습니다")
                self.main_window.update_status_bar("파일 정리가 취소되었습니다")

        except Exception as e:
            print(f"❌ 파일 정리 실행 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"파일 정리 실행 중 오류가 발생했습니다:\n{str(e)}"
            )
            self.main_window.update_status_bar(f"파일 정리 실행 실패: {str(e)}")

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

            # 결과 다이얼로그 표시
            QMessageBox.information(self.main_window, "파일 정리 완료", message)

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

        except Exception as e:
            print(f"❌ 파일 정리 완료 처리 실패: {e}")
            self.main_window.update_status_bar(f"파일 정리 완료 처리 실패: {str(e)}")

    def commit_organization(self):
        """정리 실행"""
        self.start_file_organization()

    def simulate_organization(self):
        """정리 시뮬레이션"""
        QMessageBox.information(
            self.main_window, "시뮬레이션", "파일 이동을 시뮬레이션합니다. (구현 예정)"
        )

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
