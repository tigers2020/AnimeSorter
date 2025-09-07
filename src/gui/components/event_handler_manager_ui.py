"""
이벤트 핸들러 관리 로직을 담당하는 클래스
MainWindow의 이벤트 핸들러 관련 로직을 분리하여 가독성과 유지보수성을 향상시킵니다.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from src.gui.components.settings_dialog import SettingsDialog


class EventHandlerManagerUI:
    """이벤트 핸들러 관리를 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window

    # ==================== 툴바 시그널 핸들러 메서드들 ====================

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
        """툴바에서 정리 실행 요청 처리"""
        try:
            import traceback

            print("🚀 툴바에서 정리 실행 요청됨")
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

            # 기존 정리 실행 로직 호출
            if hasattr(self.main_window, "file_organization_handler"):
                self.main_window.file_organization_handler.start_file_organization()
            else:
                print("⚠️ file_organization_handler가 초기화되지 않음")
        except Exception as e:
            print(f"❌ 정리 실행 요청 처리 실패: {e}")

    def on_search_text_changed(self, text: str):
        """툴바에서 검색 텍스트 변경 처리"""
        try:
            print(f"🔍 검색 텍스트 변경: {text}")
            # 검색 로직 구현 (나중에 구현)
            # 현재는 로그만 출력
        except Exception as e:
            print(f"❌ 검색 텍스트 변경 처리 실패: {e}")

    def on_settings_requested(self):
        """툴바에서 설정 요청 처리"""
        try:
            print("⚙️ 툴바에서 설정 요청됨")
            # 설정 다이얼로그 직접 호출
            self.show_settings_dialog()
        except Exception as e:
            print(f"❌ 설정 요청 처리 실패: {e}")

    # ==================== 패널 시그널 핸들러 메서드들 ====================

    def on_scan_started(self):
        """스캔 시작 처리"""
        try:
            print("🔍 스캔 시작됨")
            self.main_window.start_scan()
        except Exception as e:
            print(f"❌ 스캔 시작 처리 실패: {e}")

    def on_scan_paused(self):
        """스캔 일시정지 처리"""
        try:
            print("⏸️ 스캔 일시정지됨")
            self.main_window.stop_scan()
        except Exception as e:
            print(f"❌ 스캔 일시정지 처리 실패: {e}")

    def on_settings_opened(self):
        """설정 열기 처리"""
        try:
            print("⚙️ 설정 열기 요청됨")
            self.show_settings_dialog()
        except Exception as e:
            print(f"❌ 설정 열기 처리 실패: {e}")

    def on_completed_cleared(self):
        """완료된 항목 정리 처리"""
        try:
            print("🧹 완료된 항목 정리 요청됨")
            self.main_window.clear_completed()
        except Exception as e:
            print(f"❌ 완료된 항목 정리 처리 실패: {e}")

    def on_source_folder_selected(self, folder_path: str):
        """소스 폴더 선택 처리"""
        try:
            self.main_window.source_directory = folder_path
            self.main_window.update_scan_button_state()
            self.main_window.update_status_bar(f"소스 폴더가 선택되었습니다: {folder_path}")
        except Exception as e:
            print(f"❌ 소스 폴더 선택 처리 실패: {e}")

    def on_source_files_selected(self, file_paths: list[str]):
        """소스 파일 선택 처리"""
        try:
            self.main_window.source_files = file_paths
            self.main_window.update_scan_button_state()
            self.main_window.update_status_bar(f"{len(file_paths)}개 파일이 선택되었습니다")

            # 선택된 파일들을 처리
            self.main_window.process_selected_files(file_paths)
        except Exception as e:
            print(f"❌ 소스 파일 선택 처리 실패: {e}")

    def on_destination_folder_selected(self, folder_path: str):
        """대상 폴더 선택 처리"""
        try:
            self.main_window.destination_directory = folder_path
            self.main_window.update_status_bar(f"대상 폴더가 선택되었습니다: {folder_path}")

            # GroupedListModel의 대상 폴더 정보 업데이트
            if hasattr(self.main_window, "grouped_model"):
                self.main_window.grouped_model.destination_directory = folder_path
                # 모델 새로고침 (기존 데이터로 다시 설정)
                if hasattr(self.main_window, "anime_data_manager"):
                    grouped_items = self.main_window.anime_data_manager.get_grouped_items()
                    self.main_window.grouped_model.set_grouped_items(grouped_items)
        except Exception as e:
            print(f"❌ 대상 폴더 선택 처리 실패: {e}")

    # ==================== 메뉴바 시그널 핸들러 메서드들 ====================

    def choose_files(self):
        """파일 선택 (메뉴바용)"""
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self.main_window,
                "파일 선택",
                "",
                "Video Files (*.mkv *.mp4 *.avi *.mov);;All Files (*)",
            )
            if files:
                self.on_source_files_selected(files)
        except Exception as e:
            print(f"❌ 파일 선택 처리 실패: {e}")

    def choose_folder(self):
        """폴더 선택 (메뉴바용)"""
        try:
            folder = QFileDialog.getExistingDirectory(self.main_window, "폴더 선택")
            if folder:
                self.on_source_folder_selected(folder)
        except Exception as e:
            print(f"❌ 폴더 선택 처리 실패: {e}")

    def export_results(self):
        """결과 내보내기"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self.main_window,
                "결과 내보내기",
                "animesorter_results.csv",
                "CSV Files (*.csv);;All Files (*)",
            )
            if filename:
                self._export_results_to_csv(filename)
        except Exception as e:
            print(f"❌ 결과 내보내기 처리 실패: {e}")

    def _export_results_to_csv(self, filename: str):
        """결과를 CSV 파일로 내보내기"""
        try:
            import csv

            items = self.main_window.anime_data_manager.get_items()

            with Path(filename).open("w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "상태",
                    "제목",
                    "시즌",
                    "에피소드",
                    "년도",
                    "해상도",
                    "크기",
                    "TMDB ID",
                    "경로",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for item in items:
                    writer.writerow(
                        {
                            "상태": item.status,
                            "제목": item.detectedTitle,
                            "시즌": item.season or "",
                            "에피소드": item.episode or "",
                            "년도": item.year or "",
                            "해상도": item.resolution or "",
                            "크기": f"{item.sizeMB}MB" if item.sizeMB else "",
                            "TMDB ID": item.tmdbId or "",
                            "경로": item.sourcePath,
                        }
                    )

            self.main_window.update_status_bar(f"결과가 {filename}에 저장되었습니다")
            QMessageBox.information(
                self.main_window, "내보내기 완료", f"결과가 성공적으로 저장되었습니다:\n{filename}"
            )

        except Exception as e:
            QMessageBox.critical(
                self.main_window, "내보내기 오류", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}"
            )

    def show_about(self):
        """정보 다이얼로그 표시"""
        try:
            QMessageBox.about(
                self.main_window,
                "AnimeSorter 정보",
                """<h2>AnimeSorter v2.0.0</h2>
                <p><b>애니메이션 파일 정리 도구</b></p>
                <p>PyQt5 기반의 사용자 친화적인 GUI로 애니메이션 파일을 자동으로 정리하고
                TMDB API를 통해 메타데이터를 가져와 체계적으로 관리합니다.</p>
                <p><b>주요 기능:</b></p>
                <ul>
                    <li>파일명 자동 파싱</li>
                    <li>TMDB 메타데이터 검색</li>
                    <li>자동 파일 정리</li>
                    <li>배치 처리</li>
                    <li>안전 모드 및 백업</li>
                </ul>
                <p><b>개발:</b> AnimeSorter 개발팀</p>
                <p><b>라이선스:</b> MIT License</p>""",
            )
        except Exception as e:
            print(f"❌ 정보 다이얼로그 표시 실패: {e}")

    def show_help(self):
        """사용법 다이얼로그 표시"""
        try:
            help_text = """
            <h2>AnimeSorter 사용법</h2>

            <h3>1. 파일 선택</h3>
            <p>• <b>파일 선택</b>: 개별 애니메이션 파일들을 선택합니다 (Ctrl+O)</p>
            <p>• <b>폴더 선택</b>: 애니메이션 파일이 있는 폴더를 선택합니다 (Ctrl+Shift+O)</p>

            <h3>2. 스캔 및 파싱</h3>
            <p>• <b>스캔 시작</b>: 선택된 파일들을 분석하고 파싱합니다 (F5)</p>
            <p>• <b>스캔 중지</b>: 진행 중인 스캔을 중지합니다 (F6)</p>

            <h3>3. 메타데이터 매칭</h3>
            <p>• 자동으로 TMDB에서 애니메이션 정보를 검색합니다</p>
            <p>• 매칭되지 않은 항목은 수동으로 검색할 수 있습니다</p>

            <h3>4. 파일 정리</h3>
            <p>• <b>시뮬레이션</b>: 파일 이동을 미리 확인합니다 (F8)</p>
            <p>• <b>정리 실행</b>: 실제로 파일을 정리합니다 (F7)</p>

            <h3>5. 필터링 및 검색</h3>
            <p>• 상태, 해상도, 코덱 등으로 결과를 필터링할 수 있습니다</p>
            <p>• 제목이나 경로로 검색할 수 있습니다</p>

            <h3>단축키</h3>
            <p>• Ctrl+O: 파일 선택</p>
            <p>• Ctrl+Shift+O: 폴더 선택</p>
            <p>• F5: 스캔 시작</p>
            <p>• F6: 스캔 중지</p>
            <p>• F7: 정리 실행</p>
            <p>• F8: 시뮬레이션</p>
            <p>• Ctrl+R: 필터 초기화</p>
            <p>• Ctrl+E: 결과 내보내기</p>
            <p>• Ctrl+,: 설정</p>
            <p>• F1: 도움말</p>
            """

            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("사용법")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(help_text)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()

        except Exception as e:
            print(f"❌ 사용법 다이얼로그 표시 실패: {e}")

    # ==================== 설정 관련 메서드들 ====================

    def show_settings_dialog(self):
        """설정 다이얼로그 표시"""
        try:
            dialog = SettingsDialog(self.main_window.settings_manager, self.main_window)
            if dialog.exec_() == SettingsDialog.Accepted:
                # 설정이 변경되었을 때 처리
                self.main_window.settings_manager.save_settings()

                # 접근성 설정 적용
                self._apply_accessibility_settings()

                # 언어 설정 적용
                self._apply_language_settings()

                print("✅ 설정이 저장되고 적용되었습니다.")
        except Exception as e:
            print(f"❌ 설정 다이얼로그 표시 실패: {e}")
            QMessageBox.critical(
                self.main_window, "오류", f"설정 다이얼로그를 열 수 없습니다:\n{e}"
            )

    def _apply_accessibility_settings(self):
        """접근성 설정 적용"""
        try:
            if hasattr(self.main_window, "accessibility_manager"):
                high_contrast = self.main_window.settings_manager.settings.get(
                    "high_contrast_mode", False
                )
                if high_contrast != self.main_window.accessibility_manager.high_contrast_mode:
                    if high_contrast:
                        self.main_window.accessibility_manager.toggle_high_contrast_mode()
                    print(f"✅ 고대비 모드: {'활성화' if high_contrast else '비활성화'}")

                keyboard_nav = self.main_window.settings_manager.settings.get(
                    "keyboard_navigation", True
                )
                self.main_window.accessibility_manager.set_keyboard_navigation(keyboard_nav)

                screen_reader = self.main_window.settings_manager.settings.get(
                    "screen_reader_support", True
                )
                self.main_window.accessibility_manager.set_screen_reader_support(screen_reader)
        except Exception as e:
            print(f"⚠️ 접근성 설정 적용 실패: {e}")

    def _apply_language_settings(self):
        """언어 설정 적용"""
        try:
            if hasattr(self.main_window, "i18n_manager"):
                new_language = self.main_window.settings_manager.settings.get("language", "ko")
                if new_language != self.main_window.i18n_manager.get_current_language():
                    self.main_window.i18n_manager.set_language(new_language)
                    print(f"✅ 언어가 '{new_language}'로 변경되었습니다.")
        except Exception as e:
            print(f"⚠️ 언어 설정 적용 실패: {e}")

    def on_settings_changed(self):
        """설정 변경 시 호출되는 메서드"""
        try:
            # 설정 변경 시 필요한 컴포넌트 업데이트
            self.main_window.apply_settings_to_ui()

            # TMDB 클라이언트 재초기화 (API 키가 변경된 경우)
            self._reinitialize_tmdb_client()

            # FileManager 설정 업데이트
            self._update_file_manager_settings()

        except Exception as e:
            print(f"⚠️ 설정 변경 처리 실패: {e}")

    def _reinitialize_tmdb_client(self):
        """TMDB 클라이언트 재초기화"""
        try:
            if self.main_window.settings_manager:
                api_key = self.main_window.settings_manager.settings.tmdb_api_key
                if api_key and (
                    not self.main_window.tmdb_client
                    or self.main_window.tmdb_client.api_key != api_key
                ):
                    from src.core.tmdb_client import TMDBClient

                    self.main_window.tmdb_client = TMDBClient(api_key=api_key)
                    print("✅ TMDBClient 재초기화 완료")
        except Exception as e:
            print(f"⚠️ TMDB 클라이언트 재초기화 실패: {e}")

    def _update_file_manager_settings(self):
        """FileManager 설정 업데이트"""
        try:
            if self.main_window.settings_manager and self.main_window.file_manager:
                dest_root = self.main_window.settings_manager.settings.destination_root
                safe_mode = self.main_window.settings_manager.settings.safe_mode
                naming_scheme = self.main_window.settings_manager.settings.naming_scheme

                if dest_root:
                    self.main_window.file_manager.destination_root = dest_root
                self.main_window.file_manager.safe_mode = safe_mode
                self.main_window.file_manager.set_naming_scheme(naming_scheme)

                print("✅ FileManager 설정 업데이트 완료")
        except Exception as e:
            print(f"⚠️ FileManager 설정 업데이트 실패: {e}")

    # ==================== 접근성 및 국제화 관련 메서드들 ====================

    def toggle_accessibility_mode(self):
        """접근성 모드 토글"""
        try:
            if hasattr(self.main_window, "accessibility_manager"):
                features = ["screen_reader_support", "keyboard_navigation", "focus_indicators"]
                current_info = self.main_window.accessibility_manager.get_accessibility_info()

                if current_info["screen_reader_support"]:
                    self.main_window.accessibility_manager.disable_accessibility_features(features)
                    print("🔧 접근성 모드 비활성화")
                else:
                    self.main_window.accessibility_manager.enable_accessibility_features(features)
                    print("🔧 접근성 모드 활성화")
        except Exception as e:
            print(f"❌ 접근성 모드 토글 실패: {e}")

    def toggle_high_contrast_mode(self):
        """고대비 모드 토글"""
        try:
            if hasattr(self.main_window, "accessibility_manager"):
                self.main_window.accessibility_manager.toggle_high_contrast_mode()
        except Exception as e:
            print(f"❌ 고대비 모드 토글 실패: {e}")

    def get_accessibility_info(self) -> dict:
        """접근성 정보 반환"""
        try:
            if hasattr(self.main_window, "accessibility_manager"):
                return self.main_window.accessibility_manager.get_accessibility_info()
        except Exception as e:
            print(f"❌ 접근성 정보 반환 실패: {e}")
        return {}

    def on_language_changed(self, language_code: str):
        """언어 변경 이벤트 처리"""
        try:
            print(f"🌍 언어가 {language_code}로 변경되었습니다")

            # UI 텍스트 업데이트
            self._update_ui_texts()

            # 상태바에 언어 변경 정보 표시
            if (
                hasattr(self.main_window, "status_bar_manager")
                and self.main_window.status_bar_manager
            ):
                language_name = self.main_window.i18n_manager.get_language_name(language_code)
                self.main_window.status_bar_manager.update_status_bar(
                    f"언어가 {language_name}로 변경되었습니다"
                )
        except Exception as e:
            print(f"❌ 언어 변경 이벤트 처리 실패: {e}")

    def _update_ui_texts(self):
        """UI 텍스트 업데이트 (번역 적용)"""
        try:
            if not hasattr(self.main_window, "i18n_manager"):
                return

            tr = self.main_window.i18n_manager.tr

            # 메인 윈도우 제목 업데이트
            self.main_window.setWindowTitle(tr("main_window_title", "AnimeSorter"))

            # 툴바 액션 텍스트 업데이트
            self._update_toolbar_texts(tr)

            # 결과 뷰 탭 텍스트 업데이트
            self._update_tab_texts(tr)

            print("✅ UI 텍스트 업데이트 완료")

        except Exception as e:
            print(f"⚠️ UI 텍스트 업데이트 실패: {e}")

    def _update_toolbar_texts(self, tr):
        """툴바 텍스트 업데이트"""
        try:
            if hasattr(self.main_window, "main_toolbar"):
                toolbar = self.main_window.main_toolbar

                if hasattr(toolbar, "scan_action"):
                    toolbar.scan_action.setText(tr("scan_files", "파일 스캔"))
                    toolbar.scan_action.setToolTip(
                        tr("scan_files_desc", "선택된 폴더의 애니메이션 파일들을 스캔합니다")
                    )

                if hasattr(toolbar, "preview_action"):
                    toolbar.preview_action.setText(tr("preview_organization", "미리보기"))
                    toolbar.preview_action.setToolTip(
                        tr("preview_organization_desc", "정리 작업의 미리보기를 표시합니다")
                    )

                if hasattr(toolbar, "organize_action"):
                    toolbar.organize_action.setText(tr("organize_files", "파일 정리"))
                    toolbar.organize_action.setToolTip(
                        tr("organize_organization_desc", "스캔된 파일들을 정리된 구조로 이동합니다")
                    )

                if hasattr(toolbar, "settings_action"):
                    toolbar.settings_action.setText(tr("settings", "설정"))
                    toolbar.settings_action.setToolTip(
                        tr("settings_desc", "애플리케이션 설정을 엽니다")
                    )
        except Exception as e:
            print(f"⚠️ 툴바 텍스트 업데이트 실패: {e}")

    def _update_tab_texts(self, tr):
        """탭 텍스트 업데이트"""
        try:
            if hasattr(self.main_window, "results_view") and hasattr(
                self.main_window.results_view, "tab_widget"
            ):
                tab_widget = self.main_window.results_view.tab_widget

                tab_texts = [
                    tr("tab_all", "전체"),
                    tr("tab_unmatched", "미매칭"),
                    tr("tab_conflict", "충돌"),
                    tr("tab_duplicate", "중복"),
                    tr("tab_completed", "완료"),
                ]

                for i, text in enumerate(tab_texts):
                    if i < tab_widget.count():
                        tab_widget.setTabText(i, text)
        except Exception as e:
            print(f"⚠️ 탭 텍스트 업데이트 실패: {e}")

    def change_language(self, language_code: str):
        """언어 변경"""
        try:
            if hasattr(self.main_window, "i18n_manager"):
                return self.main_window.i18n_manager.set_language(language_code)
        except Exception as e:
            print(f"❌ 언어 변경 실패: {e}")
        return False

    def get_current_language(self) -> str:
        """현재 언어 반환"""
        try:
            if hasattr(self.main_window, "i18n_manager"):
                return self.main_window.i18n_manager.get_current_language()
        except Exception as e:
            print(f"❌ 현재 언어 반환 실패: {e}")
        return "ko"

    def get_supported_languages(self) -> dict:
        """지원 언어 목록 반환"""
        try:
            if hasattr(self.main_window, "i18n_manager"):
                return self.main_window.i18n_manager.get_supported_languages()
        except Exception as e:
            print(f"❌ 지원 언어 목록 반환 실패: {e}")
        return {"ko": "한국어", "en": "English"}

    def tr(self, key: str, fallback: str = None) -> str:
        """번역 함수"""
        try:
            if hasattr(self.main_window, "i18n_manager"):
                return self.main_window.i18n_manager.tr(key, fallback)
        except Exception as e:
            print(f"❌ 번역 함수 실행 실패: {e}")
        return fallback if fallback else key
