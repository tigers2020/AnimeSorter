"""
MainWindow 메뉴 액션 핸들러

MainWindow의 메뉴 액션 관련 메서드들을 관리하는 핸들러 클래스입니다.
"""


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
            print("🔍 툴바에서 스캔 요청됨")
            # 기존 스캔 로직 호출
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                self.main_window.left_panel.start_scan()
            else:
                print("⚠️ left_panel이 초기화되지 않음")
        except Exception as e:
            print(f"❌ 스캔 요청 처리 실패: {e}")

    def on_preview_requested(self):
        """툴바에서 미리보기 요청 처리"""
        try:
            print("👁️ 툴바에서 미리보기 요청됨")
            # 기존 미리보기 로직 호출
            if hasattr(self.main_window, "file_organization_handler"):
                self.main_window.file_organization_handler.show_preview()
            else:
                print("⚠️ file_organization_handler가 초기화되지 않음")
        except Exception as e:
            print(f"❌ 미리보기 요청 처리 실패: {e}")

    def on_organize_requested(self):
        """툴바에서 정리 요청 처리"""
        try:
            import traceback

            print("🗂️ 툴바에서 정리 요청됨")
            print("📍 호출 스택:")
            for line in traceback.format_stack()[-3:-1]:  # 마지막 2개의 스택 프레임
                print(f"   {line.strip()}")

            # TMDB 검색 중인지 확인
            if (
                hasattr(self.main_window, "tmdb_search_handler")
                and self.main_window.tmdb_search_handler
            ):
                if self.main_window.tmdb_search_handler.is_search_in_progress():
                    from PyQt5.QtWidgets import QMessageBox

                    QMessageBox.warning(
                        self.main_window,
                        "파일 정리 불가",
                        "TMDB 검색 중에는 파일 정리를 할 수 없습니다.\n"
                        "TMDB 검색이 완료된 후 다시 시도해주세요.",
                    )
                    print("⚠️ TMDB 검색 중에는 파일 정리를 할 수 없습니다")
                    return

            # 기존 정리 로직 호출
            if hasattr(self.main_window, "file_organization_handler") and self.main_window.file_organization_handler:
                print("✅ file_organization_handler 발견 - 파일 정리 시작")
                try:
                    self.main_window.file_organization_handler.start_file_organization()
                    print("✅ 파일 정리 기능 실행 완료")
                except Exception as e:
                    print(f"❌ 파일 정리 실행 중 오류: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⚠️ file_organization_handler가 아직 초기화되지 않았습니다")
                print("   애플리케이션이 완전히 시작된 후 다시 시도해주세요")
                print(f"   hasattr 체크: {hasattr(self.main_window, 'file_organization_handler')}")
                if hasattr(self.main_window, 'file_organization_handler'):
                    print(f"   핸들러 값: {self.main_window.file_organization_handler}")
                # 사용자에게 메시지 표시
                self._show_message_to_user("파일 정리 기능이 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요.")
        except Exception as e:
            print(f"❌ 정리 요청 처리 실패: {e}")

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
            print(f"❌ 메시지 표시 실패: {e}")

    def on_settings_requested(self):
        """툴바에서 설정 요청 처리"""
        try:
            print("⚙️ 툴바에서 설정 요청됨")
            # 기존 설정 로직 호출
            if hasattr(self.main_window, "left_panel") and self.main_window.left_panel:
                self.main_window.left_panel.open_settings()
            else:
                print("⚠️ left_panel이 초기화되지 않음")
        except Exception as e:
            print(f"❌ 설정 요청 처리 실패: {e}")

    def on_settings_opened(self):
        """설정 창이 열렸을 때 처리"""
        try:
            print("⚙️ 설정 창이 열렸습니다")
            # 설정 변경 시 UI 업데이트
            if hasattr(self.main_window, "apply_settings_to_ui"):
                self.main_window.apply_settings_to_ui()
            else:
                print("⚠️ apply_settings_to_ui 메서드가 없습니다")
        except Exception as e:
            print(f"⚠️ 설정 창 열림 처리 실패: {e}")

    def on_source_folder_selected(self, folder_path: str):
        """소스 폴더 선택 시 처리"""
        try:
            print(f"📁 소스 폴더 선택됨: {folder_path}")
            self.main_window.source_directory = folder_path
            # 소스 폴더 변경 시 관련 UI 업데이트
            if hasattr(self.main_window, "update_scan_button_state"):
                self.main_window.update_scan_button_state()
        except Exception as e:
            print(f"⚠️ 소스 폴더 선택 처리 실패: {e}")

    def on_source_files_selected(self, file_paths: list[str]):
        """소스 파일들 선택 시 처리"""
        try:
            print(f"📄 소스 파일들 선택됨: {len(file_paths)}개")
            self.main_window.source_files = file_paths
            # 소스 파일 변경 시 관련 UI 업데이트
            if hasattr(self.main_window, "update_scan_button_state"):
                self.main_window.update_scan_button_state()
        except Exception as e:
            print(f"⚠️ 소스 파일 선택 처리 실패: {e}")

    def on_destination_folder_selected(self, folder_path: str):
        """대상 폴더 선택 시 처리"""
        try:
            print(f"📁 대상 폴더 선택됨: {folder_path}")
            self.main_window.destination_directory = folder_path
            # 대상 폴더 변경 시 관련 UI 업데이트
            if hasattr(self.main_window, "update_scan_button_state"):
                self.main_window.update_scan_button_state()
        except Exception as e:
            print(f"⚠️ 대상 폴더 선택 처리 실패: {e}")

    def on_group_selected(self, group_info: dict):
        """그룹 선택 시 상세 파일 목록 업데이트"""
        try:
            if group_info and "items" in group_info:
                # 선택된 그룹의 파일들을 상세 모델에 설정
                self.main_window.detail_model.set_items(group_info["items"])

                # 상태바에 그룹 정보 표시
                title = group_info.get("title", "Unknown")
                file_count = group_info.get("file_count", 0)
                if hasattr(self.main_window, "update_status_bar"):
                    self.main_window.update_status_bar(
                        f"선택된 그룹: {title} ({file_count}개 파일)"
                    )

                print(f"✅ 그룹 '{title}'의 {file_count}개 파일을 상세 목록에 표시")
        except Exception as e:
            print(f"⚠️ 그룹 선택 처리 실패: {e}")

    def on_search_text_changed(self, text: str):
        """툴바에서 검색 텍스트 변경 처리"""
        try:
            print(f"🔍 검색 텍스트 변경: {text}")
            # 검색 로직 구현 (나중에 구현)
            # 현재는 로그만 출력
        except Exception as e:
            print(f"❌ 검색 텍스트 변경 처리 실패: {e}")

    def on_scan_started(self):
        """스캔 시작 처리"""
        try:
            print("🔍 스캔 시작됨")
            if hasattr(self.main_window, "start_scan"):
                self.main_window.start_scan()
            else:
                print("⚠️ start_scan 메서드가 없습니다")
        except Exception as e:
            print(f"❌ 스캔 시작 처리 실패: {e}")

    def on_scan_paused(self):
        """스캔 일시정지 처리"""
        try:
            print("⏸️ 스캔 일시정지됨")
            if hasattr(self.main_window, "stop_scan"):
                self.main_window.stop_scan()
            else:
                print("⚠️ stop_scan 메서드가 없습니다")
        except Exception as e:
            print(f"❌ 스캔 일시정지 처리 실패: {e}")

    def on_completed_cleared(self):
        """완료된 항목 정리 처리"""
        try:
            print("🧹 완료된 항목 정리 요청됨")
            if hasattr(self.main_window, "clear_completed"):
                self.main_window.clear_completed()
            else:
                print("⚠️ clear_completed 메서드가 없습니다")
        except Exception as e:
            print(f"❌ 완료된 항목 정리 처리 실패: {e}")
