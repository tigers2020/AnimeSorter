"""
UI 통합

Undo/Redo 기능을 PyQt5 UI에 통합하는 컴포넌트들
"""

import logging

logger = logging.getLogger(__name__)
from typing import Any, cast

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QAction, QMainWindow, QMenu, QMenuBar, QShortcut,
                             QToolBar, QWidget)

from src.app.undo_redo.undo_redo_manager import UndoRedoManager


class UndoRedoShortcutManager(QObject):
    """Undo/Redo 단축키 관리자"""

    def __init__(self, parent_widget: QWidget, undo_redo_manager: UndoRedoManager):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.undo_redo_manager = undo_redo_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self._shortcuts: dict[str, QShortcut] = {}
        self._setup_shortcuts()
        self.logger.info("Undo/Redo 단축키 설정 완료")

    def _setup_shortcuts(self) -> None:
        """단축키 설정"""
        undo_shortcut = QShortcut(QKeySequence.Undo, self.parent_widget)
        undo_shortcut.activated.connect(self._on_undo_shortcut)
        self._shortcuts["undo"] = undo_shortcut
        redo_shortcut1 = QShortcut(QKeySequence.Redo, self.parent_widget)
        redo_shortcut1.activated.connect(self._on_redo_shortcut)
        self._shortcuts["redo1"] = redo_shortcut1
        redo_shortcut2 = QShortcut(QKeySequence("Ctrl+Shift+Z"), self.parent_widget)
        redo_shortcut2.activated.connect(self._on_redo_shortcut)
        self._shortcuts["redo2"] = redo_shortcut2
        self.logger.debug("단축키 등록: Ctrl+Z (취소), Ctrl+Y/Ctrl+Shift+Z (재실행)")

    def _on_undo_shortcut(self) -> None:
        """취소 단축키 처리"""
        if self.undo_redo_manager.can_undo():
            self.undo_redo_manager.undo()
        else:
            self.logger.debug("취소할 작업이 없음")

    def _on_redo_shortcut(self) -> None:
        """재실행 단축키 처리"""
        if self.undo_redo_manager.can_redo():
            self.undo_redo_manager.redo()
        else:
            self.logger.debug("재실행할 작업이 없음")

    def set_enabled(self, enabled: bool) -> None:
        """단축키 활성화/비활성화"""
        for shortcut in self._shortcuts.values():
            shortcut.setEnabled(enabled)
        self.logger.debug(f"단축키 {'활성화' if enabled else '비활성화'}")


class UndoRedoMenuManager(QObject):
    """Undo/Redo 메뉴 관리자"""

    def __init__(self, menu_bar: QMenuBar, undo_redo_manager: UndoRedoManager):
        super().__init__(menu_bar)
        self.menu_bar = menu_bar
        self.undo_redo_manager = undo_redo_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.undo_action: QAction | None = None
        self.redo_action: QAction | None = None
        self.edit_menu: QMenu | None = None
        self._setup_menu()
        self._connect_signals()
        self.logger.info("Undo/Redo 메뉴 설정 완료")

    def _setup_menu(self) -> None:
        """메뉴 설정"""
        self.edit_menu = self._find_or_create_edit_menu()
        self.undo_action = QAction("실행 취소(&U)", self.menu_bar)
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.undo_action.setStatusTip("마지막 작업을 취소합니다")
        self.undo_action.triggered.connect(lambda: self.undo_redo_manager.undo() or None)
        self.redo_action = QAction("다시 실행(&R)", self.menu_bar)
        self.redo_action.setShortcut(QKeySequence.Redo)
        self.redo_action.setStatusTip("취소한 작업을 다시 실행합니다")
        self.redo_action.triggered.connect(lambda: self.undo_redo_manager.redo() or None)
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        self.logger.debug("메뉴 액션 추가 완료")

    def _find_or_create_edit_menu(self) -> QMenu:
        """편집 메뉴 찾기 또는 생성"""
        for action in self.menu_bar.actions():
            menu = action.menu()
            if menu is not None and menu.title().replace("&", "").lower() in ["편집", "edit"]:
                self.logger.debug("기존 편집 메뉴 발견")
                return menu
        edit_menu = cast("QMenu", self.menu_bar.addMenu("편집(&E)"))
        self.logger.debug("새 편집 메뉴 생성")
        return edit_menu

    def _connect_signals(self) -> None:
        """시그널 연결"""
        self.undo_redo_manager.can_undo_changed.connect(self._update_undo_action)
        self.undo_redo_manager.can_redo_changed.connect(self._update_redo_action)
        self.undo_redo_manager.stack_changed.connect(self._update_action_texts)

    def _update_undo_action(self, can_undo: bool) -> None:
        """취소 액션 업데이트"""
        if self.undo_action:
            self.undo_action.setEnabled(can_undo)
            if can_undo:
                undo_text = self.undo_redo_manager.undo_text()
                self.undo_action.setText(f"실행 취소: {undo_text}(&U)")
                self.undo_action.setStatusTip(f"'{undo_text}' 작업을 취소합니다")
            else:
                self.undo_action.setText("실행 취소(&U)")
                self.undo_action.setStatusTip("취소할 작업이 없습니다")

    def _update_redo_action(self, can_redo: bool) -> None:
        """재실행 액션 업데이트"""
        if self.redo_action:
            self.redo_action.setEnabled(can_redo)
            if can_redo:
                redo_text = self.undo_redo_manager.redo_text()
                self.redo_action.setText(f"다시 실행: {redo_text}(&R)")
                self.redo_action.setStatusTip(f"'{redo_text}' 작업을 다시 실행합니다")
            else:
                self.redo_action.setText("다시 실행(&R)")
                self.redo_action.setStatusTip("다시 실행할 작업이 없습니다")

    def _update_action_texts(self) -> None:
        """액션 텍스트 업데이트"""
        self._update_undo_action(self.undo_redo_manager.can_undo())
        self._update_redo_action(self.undo_redo_manager.can_redo())


class UndoRedoToolbarManager(QObject):
    """Undo/Redo 툴바 관리자"""

    def __init__(self, toolbar: QToolBar, undo_redo_manager: UndoRedoManager):
        super().__init__(toolbar)
        self.toolbar = toolbar
        self.undo_redo_manager = undo_redo_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.undo_action: QAction | None = None
        self.redo_action: QAction | None = None
        self._setup_toolbar()
        self._connect_signals()
        self.logger.info("Undo/Redo 툴바 설정 완료")

    def _setup_toolbar(self) -> None:
        """툴바 설정"""
        self.undo_action = cast("QAction", self.toolbar.addAction("↶"))
        self.undo_action.setText("취소")
        self.undo_action.setToolTip("마지막 작업을 취소합니다 (Ctrl+Z)")
        self.undo_action.triggered.connect(lambda: self.undo_redo_manager.undo() or None)
        self.redo_action = cast("QAction", self.toolbar.addAction("↷"))
        self.redo_action.setText("재실행")
        self.redo_action.setToolTip("취소한 작업을 다시 실행합니다 (Ctrl+Y)")
        self.redo_action.triggered.connect(lambda: self.undo_redo_manager.redo() or None)
        self.toolbar.addSeparator()
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)
        self.logger.debug("툴바 버튼 추가 완료")

    def _connect_signals(self) -> None:
        """시그널 연결"""
        self.undo_redo_manager.can_undo_changed.connect(self._update_undo_button)
        self.undo_redo_manager.can_redo_changed.connect(self._update_redo_button)
        self.undo_redo_manager.stack_changed.connect(self._update_tooltips)

    def _update_undo_button(self, can_undo: bool) -> None:
        """취소 버튼 업데이트"""
        if self.undo_action:
            self.undo_action.setEnabled(can_undo)

    def _update_redo_button(self, can_redo: bool) -> None:
        """재실행 버튼 업데이트"""
        if self.redo_action:
            self.redo_action.setEnabled(can_redo)

    def _update_tooltips(self) -> None:
        """툴팁 업데이트"""
        if self.undo_action:
            if self.undo_redo_manager.can_undo():
                undo_text = self.undo_redo_manager.undo_text()
                self.undo_action.setToolTip(f"'{undo_text}' 작업을 취소합니다 (Ctrl+Z)")
            else:
                self.undo_action.setToolTip("취소할 작업이 없습니다")
        if self.redo_action:
            if self.undo_redo_manager.can_redo():
                redo_text = self.undo_redo_manager.redo_text()
                self.redo_action.setToolTip(f"'{redo_text}' 작업을 다시 실행합니다 (Ctrl+Y)")
            else:
                self.redo_action.setToolTip("다시 실행할 작업이 없습니다")


class UndoRedoUIIntegration(QObject):
    """통합 UI 관리자"""

    def __init__(self, main_window: QMainWindow, undo_redo_manager: UndoRedoManager):
        super().__init__(main_window)
        self.main_window = main_window
        self.undo_redo_manager = undo_redo_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.shortcut_manager: UndoRedoShortcutManager | None = None
        self.menu_manager: UndoRedoMenuManager | None = None
        self.toolbar_manager: UndoRedoToolbarManager | None = None
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._periodic_update)
        self._update_timer.start(1000)
        self._setup_ui_integration()
        self.logger.info("Undo/Redo UI 통합 완료")

    def _setup_ui_integration(self) -> None:
        """UI 통합 설정"""
        self.shortcut_manager = UndoRedoShortcutManager(self.main_window, self.undo_redo_manager)
        menu_bar = self.main_window.menuBar()
        if menu_bar is not None:
            self.menu_manager = UndoRedoMenuManager(menu_bar, self.undo_redo_manager)
        toolbar = self._find_or_create_toolbar()
        if toolbar:
            self.toolbar_manager = UndoRedoToolbarManager(toolbar, self.undo_redo_manager)

    def _find_or_create_toolbar(self) -> QToolBar | None:
        """툴바 찾기 또는 생성"""
        toolbars = self.main_window.findChildren(QToolBar)
        for toolbar in toolbars:
            if "edit" in toolbar.objectName().lower() or "편집" in toolbar.windowTitle():
                self.logger.debug("기존 편집 툴바 발견")
                return toolbar
        if toolbars:
            self.logger.debug("첫 번째 툴바 사용")
            return toolbars[0]
        toolbar = cast("QToolBar", self.main_window.addToolBar("편집"))
        toolbar.setObjectName("editToolBar")
        self.logger.debug("새 편집 툴바 생성")
        return toolbar

    def _periodic_update(self) -> None:
        """주기적 UI 상태 업데이트"""
        if hasattr(self, "_last_stack_count"):
            current_count = self.undo_redo_manager.get_stack_count()
            current_index = self.undo_redo_manager.get_current_index()
            if current_count != self._last_stack_count or current_index != self._last_current_index:
                self._update_ui_state()
        else:
            self._update_ui_state()

    def _update_ui_state(self) -> None:
        """UI 상태 업데이트"""
        self._last_stack_count = self.undo_redo_manager.get_stack_count()
        self._last_current_index = self.undo_redo_manager.get_current_index()
        status_bar = self.main_window.statusBar()
        if status_bar is not None:
            stats = self.undo_redo_manager.get_statistics()
            if stats.total_commands_executed > 0:
                status_text = f"실행: {stats.total_commands_executed} | 취소: {stats.total_undos} | 재실행: {stats.total_redos}"
                status_bar.showMessage(status_text, 2000)

    def set_enabled(self, enabled: bool) -> None:
        """전체 UI 활성화/비활성화"""
        if self.shortcut_manager:
            self.shortcut_manager.set_enabled(enabled)
        if self.menu_manager:
            if self.menu_manager.undo_action:
                self.menu_manager.undo_action.setEnabled(
                    enabled and self.undo_redo_manager.can_undo()
                )
            if self.menu_manager.redo_action:
                self.menu_manager.redo_action.setEnabled(
                    enabled and self.undo_redo_manager.can_redo()
                )
        if self.toolbar_manager:
            if self.toolbar_manager.undo_action:
                self.toolbar_manager.undo_action.setEnabled(
                    enabled and self.undo_redo_manager.can_undo()
                )
            if self.toolbar_manager.redo_action:
                self.toolbar_manager.redo_action.setEnabled(
                    enabled and self.undo_redo_manager.can_redo()
                )
        self.logger.info(f"Undo/Redo UI {'활성화' if enabled else '비활성화'}")

    def get_status_info(self) -> dict[str, Any]:
        """상태 정보 조회"""
        stats = self.undo_redo_manager.get_statistics()
        return {
            "can_undo": self.undo_redo_manager.can_undo(),
            "can_redo": self.undo_redo_manager.can_redo(),
            "undo_text": self.undo_redo_manager.undo_text(),
            "redo_text": self.undo_redo_manager.redo_text(),
            "stack_count": self.undo_redo_manager.get_stack_count(),
            "current_index": self.undo_redo_manager.get_current_index(),
            "is_clean": self.undo_redo_manager.is_clean(),
            "statistics": stats,
            "command_history": self.undo_redo_manager.get_command_history(),
        }

    def shutdown(self) -> None:
        """UI 통합 종료"""
        self._update_timer.stop()
        self.logger.info("Undo/Redo UI 통합 종료")
