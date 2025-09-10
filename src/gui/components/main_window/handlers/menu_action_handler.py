"""
MainWindow 메뉴 액션 핸들러

MainWindow의 메뉴 액션 관련 메서드들을 관리하는 핸들러 클래스입니다.
"""

import logging

logger = logging.getLogger(__name__)


class MainWindowMenuActionHandler:
    """MainWindow의 메뉴 액션 관련 메서드들을 관리하는 핸들러"""

    def __init__(self, main_window):
        """
        MainWindowMenuActionHandler 초기화

        Args:
            main_window: MainWindow 인스턴스
        """
        self.main_window = main_window

    def on_scan_requested(self):
        """툴바에서 스캔 요청 처리"""
        try:
            logger.info("🔍 툴바에서 스캔 요청됨")
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                self.main_window.left_panel.start_scan()
            else:
                logger.info("⚠️ left_panel이 초기화되지 않음")
        except Exception as e:
            logger.info("❌ 스캔 요청 처리 실패: %s", e)

    def on_preview_requested(self):
        """툴바에서 미리보기 요청 처리"""
        try:
            logger.info("👁️ 툴바에서 미리보기 요청됨")
            if hasattr(self.main_window, "file_organization_handler"):
                self.main_window.file_organization_handler.show_preview()
            else:
                logger.info("⚠️ file_organization_handler가 초기화되지 않음")
        except Exception as e:
            logger.info("❌ 미리보기 요청 처리 실패: %s", e)

    def on_organize_requested(self):
        """툴바에서 정리 요청 처리"""
        try:
            import traceback

            logger.info("🗂️ 툴바에서 정리 요청됨")
            logger.info("📍 호출 스택:")
            for line in traceback.format_stack()[-3:-1]:
                logger.info("   %s", line.strip())
            if (
                hasattr(self.main_window, "tmdb_search_handler")
                and self.main_window.tmdb_search_handler
                and self.main_window.tmdb_search_handler.is_search_in_progress()
            ):
                from PyQt5.QtWidgets import QMessageBox

                QMessageBox.warning(
                    self.main_window,
                    "파일 정리 불가",
                    """TMDB 검색 중에는 파일 정리를 할 수 없습니다.
TMDB 검색이 완료된 후 다시 시도해주세요.""",
                )
                logger.info("⚠️ TMDB 검색 중에는 파일 정리를 할 수 없습니다")
                return
            if (
                hasattr(self.main_window, "file_organization_handler")
                and self.main_window.file_organization_handler
            ):
                logger.info("✅ file_organization_handler 발견 - 파일 정리 시작")
                try:
                    self.main_window.file_organization_handler.start_file_organization()
                    logger.info("✅ 파일 정리 기능 실행 완료")
                except Exception as e:
                    logger.info("❌ 파일 정리 실행 중 오류: %s", e)
                    import traceback

                    traceback.print_exc()
            else:
                logger.info("⚠️ file_organization_handler가 아직 초기화되지 않았습니다")
                logger.info("   애플리케이션이 완전히 시작된 후 다시 시도해주세요")
                logger.info(
                    "   hasattr 체크: %s", hasattr(self.main_window, "file_organization_handler")
                )
                if hasattr(self.main_window, "file_organization_handler"):
                    logger.info("   핸들러 값: %s", self.main_window.file_organization_handler)
                self._show_message_to_user(
                    "파일 정리 기능이 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요."
                )
        except Exception as e:
            logger.info("❌ 정리 요청 처리 실패: %s", e)

    def _show_message_to_user(self, message: str, title: str = "알림", icon="information"):
        """사용자에게 메시지를 표시합니다"""
        try:
            from PyQt5.QtWidgets import QMessageBox

            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            if icon == "warning":
                msg_box.setIcon(QMessageBox.Warning)
            elif icon == "error":
                msg_box.setIcon(QMessageBox.Critical)
            else:
                msg_box.setIcon(QMessageBox.Information)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        except Exception as e:
            logger.info("❌ 메시지 표시 실패: %s", e)

    def on_settings_requested(self):
        """툴바에서 설정 요청 처리"""
        try:
            logger.info("⚙️ 툴바에서 설정 요청됨")
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                self.main_window.left_panel.open_settings()
            else:
                logger.info("⚠️ left_panel이 초기화되지 않음")
        except Exception as e:
            logger.info("❌ 설정 요청 처리 실패: %s", e)

    def on_settings_opened(self):
        """설정 창이 열렸을 때 처리"""
        try:
            logger.info("⚙️ 설정 창이 열렸습니다")
            if hasattr(self.main_window, "apply_settings_to_ui"):
                self.main_window.apply_settings_to_ui()
            else:
                logger.info("⚠️ apply_settings_to_ui 메서드가 없습니다")
        except Exception as e:
            logger.info("⚠️ 설정 창 열림 처리 실패: %s", e)

    def on_source_folder_selected(self, folder_path: str):
        """소스 폴더 선택 시 처리"""
        try:
            logger.info("📁 소스 폴더 선택됨: %s", folder_path)
            self.main_window.source_directory = folder_path
            if hasattr(self.main_window, "update_scan_button_state"):
                self.main_window.update_scan_button_state()
        except Exception as e:
            logger.info("⚠️ 소스 폴더 선택 처리 실패: %s", e)

    def on_source_files_selected(self, file_paths: list[str]):
        """소스 파일들 선택 시 처리"""
        try:
            logger.info("📄 소스 파일들 선택됨: %s개", len(file_paths))
            self.main_window.source_files = file_paths
            if hasattr(self.main_window, "update_scan_button_state"):
                self.main_window.update_scan_button_state()
        except Exception as e:
            logger.info("⚠️ 소스 파일 선택 처리 실패: %s", e)

    def on_destination_folder_selected(self, folder_path: str):
        """대상 폴더 선택 시 처리"""
        try:
            logger.info("📁 대상 폴더 선택됨: %s", folder_path)
            self.main_window.destination_directory = folder_path
            if hasattr(self.main_window, "update_scan_button_state"):
                self.main_window.update_scan_button_state()
        except Exception as e:
            logger.info("⚠️ 대상 폴더 선택 처리 실패: %s", e)

    def on_group_selected(self, group_info: dict):
        """그룹 선택 시 상세 파일 목록 업데이트"""
        try:
            if group_info and "items" in group_info:
                self.main_window.detail_model.set_items(group_info["items"])
                title = group_info.get("title", "Unknown")
                file_count = group_info.get("file_count", 0)
                if hasattr(self.main_window, "update_status_bar"):
                    self.main_window.update_status_bar(
                        f"선택된 그룹: {title} ({file_count}개 파일)"
                    )
                logger.info("✅ 그룹 '%s'의 %s개 파일을 상세 목록에 표시", title, file_count)
        except Exception as e:
            logger.info("⚠️ 그룹 선택 처리 실패: %s", e)

    def on_search_text_changed(self, text: str):
        """툴바에서 검색 텍스트 변경 처리"""
        try:
            logger.info("🔍 검색 텍스트 변경: %s", text)
        except Exception as e:
            logger.info("❌ 검색 텍스트 변경 처리 실패: %s", e)

    def on_scan_started(self):
        """스캔 시작 처리"""
        try:
            logger.info("🔍 스캔 시작됨")
            if hasattr(self.main_window, "start_scan"):
                self.main_window.start_scan()
            else:
                logger.info("⚠️ start_scan 메서드가 없습니다")
        except Exception as e:
            logger.info("❌ 스캔 시작 처리 실패: %s", e)

    def on_scan_paused(self):
        """스캔 일시정지 처리"""
        try:
            logger.info("⏸️ 스캔 일시정지됨")
            if hasattr(self.main_window, "stop_scan"):
                self.main_window.stop_scan()
            else:
                logger.info("⚠️ stop_scan 메서드가 없습니다")
        except Exception as e:
            logger.info("❌ 스캔 일시정지 처리 실패: %s", e)

    def on_completed_cleared(self):
        """완료된 항목 정리 처리"""
        try:
            logger.info("🧹 완료된 항목 정리 요청됨")
            if hasattr(self.main_window, "clear_completed"):
                self.main_window.clear_completed()
            else:
                logger.info("⚠️ clear_completed 메서드가 없습니다")
        except Exception as e:
            logger.info("❌ 완료된 항목 정리 처리 실패: %s", e)
