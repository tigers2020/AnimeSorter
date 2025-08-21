#!/usr/bin/env python3
"""
Menu Builder for MainWindow

MainWindow의 메뉴바 생성을 담당하는 클래스입니다.
메뉴 구조와 액션들을 체계적으로 관리합니다.
"""

import logging

from PyQt5.QtWidgets import QMainWindow


class MenuBuilder:
    """MainWindow의 메뉴바 생성을 담당하는 클래스"""

    def __init__(self, main_window: QMainWindow):
        """MenuBuilder 초기화"""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def create_menu_bar(self):
        """메뉴바 생성"""
        try:
            menubar = self.main_window.menuBar()

            # 파일 메뉴
            self.create_file_menu(menubar)

            # 편집 메뉴
            self.create_edit_menu(menubar)

            # 도구 메뉴
            self.create_tools_menu(menubar)

            # 도움말 메뉴
            self.create_help_menu(menubar)

            self.logger.debug("메뉴바 생성 완료")

        except Exception as e:
            self.logger.error(f"메뉴바 생성 실패: {e}")
            raise

    def create_file_menu(self, menubar):
        """파일 메뉴 생성"""
        file_menu = menubar.addMenu("파일(&F)")

        # 파일 선택 액션
        open_files_action = file_menu.addAction("파일 선택(&O)")
        open_files_action.setShortcut("Ctrl+O")
        open_files_action.setStatusTip("애니메이션 파일을 선택합니다")
        open_files_action.triggered.connect(self.main_window.choose_files)

        open_folder_action = file_menu.addAction("폴더 선택(&F)")
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.setStatusTip("애니메이션 파일이 있는 폴더를 선택합니다")
        open_folder_action.triggered.connect(self.main_window.choose_folder)

        file_menu.addSeparator()

        # 내보내기 액션
        export_action = file_menu.addAction("결과 내보내기(&E)")
        export_action.setShortcut("Ctrl+E")
        export_action.setStatusTip("스캔 결과를 CSV 파일로 내보냅니다")
        export_action.triggered.connect(self.main_window.export_results)

        file_menu.addSeparator()

        # 종료 액션
        exit_action = file_menu.addAction("종료(&X)")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("애플리케이션을 종료합니다")
        exit_action.triggered.connect(self.main_window.close)

    def create_edit_menu(self, menubar):
        """편집 메뉴 생성"""
        edit_menu = menubar.addMenu("편집(&E)")

        # Undo/Redo 액션들
        self.main_window.undo_action = edit_menu.addAction("실행 취소(&U)")
        self.main_window.undo_action.setShortcut("Ctrl+Z")
        self.main_window.undo_action.setStatusTip("마지막 작업을 실행 취소합니다")
        self.main_window.undo_action.setEnabled(False)  # 초기에는 비활성화
        self.main_window.undo_action.triggered.connect(
            lambda: self.main_window.command_system_manager.undo_last_operation()
            if self.main_window.command_system_manager
            else None
        )

        self.main_window.redo_action = edit_menu.addAction("재실행(&R)")
        self.main_window.redo_action.setShortcut("Ctrl+Y")
        self.main_window.redo_action.setStatusTip("실행 취소된 작업을 재실행합니다")
        self.main_window.redo_action.setEnabled(False)  # 초기에는 비활성화
        self.main_window.redo_action.triggered.connect(
            lambda: self.main_window.command_system_manager.redo_last_operation()
            if self.main_window.command_system_manager
            else None
        )

        edit_menu.addSeparator()

        # 설정 액션
        settings_action = edit_menu.addAction("설정(&S)")
        settings_action.setShortcut("Ctrl+,")
        settings_action.setStatusTip("애플리케이션 설정을 변경합니다")
        settings_action.triggered.connect(self.main_window.open_settings)

        edit_menu.addSeparator()

        # 필터 초기화 액션
        reset_filters_action = edit_menu.addAction("필터 초기화(&R)")
        reset_filters_action.setShortcut("Ctrl+R")
        reset_filters_action.setStatusTip("모든 필터를 초기화합니다")
        reset_filters_action.triggered.connect(self.main_window.reset_filters)

    def create_tools_menu(self, menubar):
        """도구 메뉴 생성"""
        tools_menu = menubar.addMenu("도구(&T)")

        # 스캔 시작/중지 액션
        start_scan_action = tools_menu.addAction("스캔 시작(&S)")
        start_scan_action.setShortcut("F5")
        start_scan_action.setStatusTip("파일 스캔을 시작합니다")
        start_scan_action.triggered.connect(self.main_window.start_scan)

        stop_scan_action = tools_menu.addAction("스캔 중지(&P)")
        stop_scan_action.setShortcut("F6")
        stop_scan_action.setStatusTip("파일 스캔을 중지합니다")
        stop_scan_action.triggered.connect(self.main_window.stop_scan)

        tools_menu.addSeparator()

        # 정리 실행 액션
        commit_action = tools_menu.addAction("정리 실행(&C)")
        commit_action.setShortcut("F7")
        commit_action.setStatusTip("파일 정리를 실행합니다")
        commit_action.triggered.connect(
            lambda: self.main_window.file_organization_handler.commit_organization()
            if hasattr(self.main_window, "file_organization_handler")
            else None
        )

        # 시뮬레이션 액션
        simulate_action = tools_menu.addAction("시뮬레이션(&M)")
        simulate_action.setShortcut("F8")
        simulate_action.setStatusTip("파일 정리를 시뮬레이션합니다")
        simulate_action.triggered.connect(
            lambda: self.main_window.file_organization_handler.simulate_organization()
            if hasattr(self.main_window, "file_organization_handler")
            else None
        )

        tools_menu.addSeparator()

        # Safety System 액션들
        self.create_safety_menu(tools_menu)

    def create_safety_menu(self, tools_menu):
        """안전장치 서브메뉴 생성"""
        safety_menu = tools_menu.addMenu("안전장치(&S)")

        # 안전 모드 변경 액션들
        normal_mode_action = safety_menu.addAction("일반 모드(&N)")
        normal_mode_action.setStatusTip("일반 안전 모드로 전환합니다")
        normal_mode_action.triggered.connect(
            lambda: self.main_window.safety_system_manager.change_safety_mode("normal")
        )

        safe_mode_action = safety_menu.addAction("안전 모드(&S)")
        safe_mode_action.setStatusTip("높은 안전 모드로 전환합니다")
        safe_mode_action.triggered.connect(
            lambda: self.main_window.safety_system_manager.change_safety_mode("safe")
        )

        test_mode_action = safety_menu.addAction("테스트 모드(&T)")
        test_mode_action.setStatusTip("테스트 모드로 전환합니다 (파일 수정 없음)")
        test_mode_action.triggered.connect(
            lambda: self.main_window.safety_system_manager.change_safety_mode("test")
        )

        simulation_mode_action = safety_menu.addAction("시뮬레이션 모드(&M)")
        simulation_mode_action.setStatusTip("시뮬레이션 모드로 전환합니다")
        simulation_mode_action.triggered.connect(
            lambda: self.main_window.safety_system_manager.change_safety_mode("simulation")
        )

        emergency_mode_action = safety_menu.addAction("비상 모드(&E)")
        emergency_mode_action.setStatusTip("비상 모드로 전환합니다 (최소한의 작업만)")
        emergency_mode_action.triggered.connect(
            lambda: self.main_window.safety_system_manager.change_safety_mode("emergency")
        )

        safety_menu.addSeparator()

        # 백업 관련 액션들
        backup_action = safety_menu.addAction("백업 생성(&B)")
        backup_action.setStatusTip("현재 작업 디렉토리를 백업합니다")
        backup_action.triggered.connect(self.main_window.safety_system_manager.create_backup)

        restore_backup_action = safety_menu.addAction("백업 복원(&R)")
        restore_backup_action.setStatusTip("백업에서 파일을 복원합니다")
        restore_backup_action.triggered.connect(
            self.main_window.safety_system_manager.restore_backup
        )

        # 안전 상태 확인 액션
        safety_status_action = safety_menu.addAction("안전 상태 확인(&C)")
        safety_status_action.setStatusTip("현재 안전 상태를 확인합니다")
        safety_status_action.triggered.connect(
            self.main_window.safety_system_manager.show_safety_status
        )

    def create_help_menu(self, menubar):
        """도움말 메뉴 생성"""
        help_menu = menubar.addMenu("도움말(&H)")

        # 정보 액션
        about_action = help_menu.addAction("정보(&A)")
        about_action.setStatusTip("AnimeSorter에 대한 정보를 표시합니다")
        about_action.triggered.connect(self.main_window.show_about)

        # 사용법 액션
        help_action = help_menu.addAction("사용법(&H)")
        help_action.setShortcut("F1")
        help_action.setStatusTip("사용법을 표시합니다")
        help_action.triggered.connect(self.main_window.show_help)
