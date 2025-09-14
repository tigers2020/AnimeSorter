"""
고급 스플리터 컴포넌트 - Phase 4 UI/UX 리팩토링
마스터-디테일 스플리터의 고급 기능을 제공합니다.
"""

import logging

logger = logging.getLogger(__name__)
import json
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QSettings, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QSplitter, QStyle, QToolButton, QWidget


class AdvancedSplitter(QSplitter):
    """고급 기능을 가진 스플리터 위젯"""

    splitter_moved = pyqtSignal(int, int)
    splitter_double_clicked = pyqtSignal()
    splitter_state_changed = pyqtSignal(dict)

    def __init__(self, orientation=Qt.Vertical, parent=None):
        super().__init__(orientation, parent)
        self.init_ui()
        self.setup_advanced_features()

    def init_ui(self):
        """UI 초기화"""
        self.setChildrenCollapsible(False)
        self.setHandleWidth(8)
        self.setOpaqueResize(True)
        self.setStyleSheet(
            """
            QSplitter::handle {
                background-color: #bdc3c7;
                border: 1px solid #95a5a6;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #3498db;
                border-color: #2980b9;
            }
            QSplitter::handle:pressed {
                background-color: #2980b9;
                border-color: #1f4e79;
            }
        """
        )

    def setup_advanced_features(self):
        """고급 기능 설정"""
        self.splitterMoved.connect(self.on_splitter_moved)
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_splitter_state)
        self._min_sizes = [200, 150]
        self._preferred_ratios = [0.6, 0.4]
        self._auto_adjust_enabled = True

    def setup_handle_events(self):
        """핸들 이벤트 설정 (위젯 추가 후 호출)"""
        if self.count() > 1:
            handle = self.handle(1)
            if handle:
                handle.mouseDoubleClickEvent = self.on_handle_double_clicked

    def addWidget(self, widget):
        """위젯 추가 후 핸들 이벤트 설정"""
        super().addWidget(widget)
        QTimer.singleShot(0, self.setup_handle_events)

    def on_splitter_moved(self, pos, index):
        """스플리터 이동 시 호출"""
        self.splitter_moved.emit(pos, index)
        self.emit_state_changed()
        self.save_timer.start(1000)

    def on_handle_double_clicked(self, event):
        """핸들 더블클릭 시 호출"""
        self.restore_preferred_ratio()
        self.splitter_double_clicked.emit()
        event.accept()

    def set_minimum_sizes(self, sizes):
        """최소 크기 설정"""
        self._min_sizes = sizes
        for i, size in enumerate(sizes):
            if i < self.count():
                try:
                    size_int = int(size) if isinstance(size, str) else size
                    self.widget(i).setMinimumSize(size_int, size_int)
                except (ValueError, TypeError):
                    self.widget(i).setMinimumSize(150, 150)

    def set_preferred_ratios(self, ratios):
        """선호 비율 설정"""
        self._preferred_ratios = ratios
        self.restore_preferred_ratio()

    def restore_preferred_ratio(self):
        """선호 비율로 복원"""
        if not self._preferred_ratios or len(self._preferred_ratios) != self.count():
            return
        total_height = self.height()
        new_sizes = []
        for ratio in self._preferred_ratios:
            size = int(total_height * ratio)
            new_sizes.append(size)
        self.setSizes(new_sizes)

    def auto_adjust_sizes(self):
        """자동 크기 조정"""
        if not self._auto_adjust_enabled:
            return
        total_height = self.height()
        widget_heights = []
        for i in range(self.count()):
            widget = self.widget(i)
            if hasattr(widget, "sizeHint"):
                hint = widget.sizeHint()
                widget_heights.append(hint.height())
            else:
                widget_heights.append(total_height // self.count())
        total_hint = sum(widget_heights)
        if total_hint > 0:
            ratios = [(h / total_hint) for h in widget_heights]
            self.set_preferred_ratios(ratios)

    def enable_auto_adjust(self, enabled=True):
        """자동 조정 활성화/비활성화"""
        self._auto_adjust_enabled = enabled

    def get_splitter_state(self):
        """스플리터 상태 반환"""
        return {
            "sizes": self.sizes(),
            "orientation": self.orientation(),
            "handle_width": self.handleWidth(),
            "children_collapsible": self.childrenCollapsible(),
            "opaque_resize": self.opaqueResize(),
            "preferred_ratios": self._preferred_ratios,
            "min_sizes": self._min_sizes,
            "auto_adjust": self._auto_adjust_enabled,
        }

    def set_splitter_state(self, state):
        """스플리터 상태 설정"""
        if "sizes" in state and state["sizes"]:
            self.setSizes(state["sizes"])
        if "handle_width" in state:
            self.setHandleWidth(state["handle_width"])
        if "children_collapsible" in state:
            self.setChildrenCollapsible(state["children_collapsible"])
        if "opaque_resize" in state:
            self.setOpaqueResize(state["opaque_resize"])
        if "preferred_ratios" in state:
            self._preferred_ratios = state["preferred_ratios"]
        if "min_sizes" in state:
            self._min_sizes = state["min_sizes"]
            self.set_minimum_sizes(self._min_sizes)
        if "auto_adjust" in state:
            self._auto_adjust_enabled = state["auto_adjust"]

    def emit_state_changed(self):
        """상태 변경 시그널 발생"""
        state = self.get_splitter_state()
        self.splitter_state_changed.emit(state)

    def save_splitter_state(self):
        """스플리터 상태 저장"""
        try:
            settings = QSettings()
            settings.beginGroup("AdvancedSplitter")
            settings.setValue("sizes", self.sizes())
            settings.setValue("preferred_ratios", self._preferred_ratios)
            settings.setValue("min_sizes", self._min_sizes)
            settings.setValue("auto_adjust", self._auto_adjust_enabled)
            settings.setValue("handle_width", self.handleWidth())
            settings.setValue("children_collapsible", self.childrenCollapsible())
            settings.setValue("opaque_resize", self.opaqueResize())
            settings.setValue("last_saved", datetime.now().isoformat())
            settings.endGroup()
            logger.info("💾 스플리터 상태 저장 완료: %s", self.sizes())
        except Exception as e:
            logger.info("❌ 스플리터 상태 저장 실패: %s", e)

    def load_splitter_state(self):
        """스플리터 상태 로드"""
        try:
            settings = QSettings()
            settings.beginGroup("AdvancedSplitter")
            saved_sizes = settings.value("sizes", [])
            if saved_sizes and len(saved_sizes) == self.count():
                validated_sizes = []
                for i, size in enumerate(saved_sizes):
                    min_size = self._min_sizes[i] if i < len(self._min_sizes) else 150
                    try:
                        size_int = int(size) if isinstance(size, str) else size
                        min_size_int = int(min_size) if isinstance(min_size, str) else min_size
                        validated_sizes.append(max(size_int, min_size_int))
                    except (ValueError, TypeError):
                        validated_sizes.append(
                            min_size_int if isinstance(min_size, str) else min_size
                        )
                self.setSizes(validated_sizes)
                logger.info("📂 저장된 크기 로드: %s", validated_sizes)
            saved_ratios = settings.value("preferred_ratios", [])
            if saved_ratios and len(saved_ratios) == self.count():
                self._preferred_ratios = saved_ratios
                logger.info("📂 저장된 비율 로드: %s", saved_ratios)
            saved_min_sizes = settings.value("min_sizes", [])
            if saved_min_sizes and len(saved_min_sizes) == self.count():
                self._min_sizes = saved_min_sizes
                self.set_minimum_sizes(self._min_sizes)
                logger.info("📂 저장된 최소 크기 로드: %s", saved_min_sizes)
            saved_auto_adjust = settings.value("auto_adjust", True)
            self._auto_adjust_enabled = saved_auto_adjust
            saved_handle_width = settings.value("handle_width", 8)
            try:
                handle_width_int = (
                    int(saved_handle_width)
                    if isinstance(saved_handle_width, str)
                    else saved_handle_width
                )
                self.setHandleWidth(handle_width_int)
            except (ValueError, TypeError):
                self.setHandleWidth(8)
            saved_children_collapsible = settings.value("children_collapsible", False)
            try:
                if isinstance(saved_children_collapsible, str):
                    children_collapsible_bool = saved_children_collapsible.lower() in (
                        "true",
                        "1",
                        "yes",
                    )
                else:
                    children_collapsible_bool = bool(saved_children_collapsible)
                self.setChildrenCollapsible(children_collapsible_bool)
            except (ValueError, TypeError):
                self.setChildrenCollapsible(False)
            saved_opaque_resize = settings.value("opaque_resize", True)
            try:
                if isinstance(saved_opaque_resize, str):
                    opaque_resize_bool = saved_opaque_resize.lower() in ("true", "1", "yes")
                else:
                    opaque_resize_bool = bool(saved_opaque_resize)
                self.setOpaqueResize(opaque_resize_bool)
            except (ValueError, TypeError):
                self.setOpaqueResize(True)
            last_saved = settings.value("last_saved", "")
            if last_saved:
                logger.info("📂 마지막 저장 시간: %s", last_saved)
            settings.endGroup()
        except Exception as e:
            logger.info("❌ 스플리터 상태 로드 실패: %s", e)
            self.reset_to_defaults()

    def save_splitter_state_to_file(self, file_path):
        """스플리터 상태를 파일로 저장"""
        try:
            state = self.get_splitter_state()
            state["exported_at"] = datetime.now().isoformat()
            state["version"] = "1.0"
            with Path(file_path).open("w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            logger.info("💾 스플리터 상태를 파일로 저장 완료: %s", file_path)
            return True
        except Exception as e:
            logger.info("❌ 스플리터 상태 파일 저장 실패: %s", e)
            return False

    def load_splitter_state_from_file(self, file_path):
        """파일에서 스플리터 상태 로드"""
        try:
            with Path(file_path).open(encoding="utf-8") as f:
                state = json.load(f)
            if "version" in state:
                logger.info("📂 스플리터 상태 파일 버전: %s", state["version"])
            self.set_splitter_state(state)
            if "exported_at" in state:
                logger.info("📂 내보낸 시간: %s", state["exported_at"])
            logger.info("📂 스플리터 상태를 파일에서 로드 완료: %s", file_path)
            return True
        except Exception as e:
            logger.info("❌ 스플리터 상태 파일 로드 실패: %s", e)
            return False

    def export_splitter_config(self, file_path):
        """스플리터 설정 내보내기 (사용자 정의 가능)"""
        try:
            config = {
                "name": "AdvancedSplitter Configuration",
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "description": "사용자 정의 스플리터 설정",
                "settings": {
                    "preferred_ratios": self._preferred_ratios,
                    "min_sizes": self._min_sizes,
                    "auto_adjust": self._auto_adjust_enabled,
                    "handle_width": self.handleWidth(),
                    "children_collapsible": self.childrenCollapsible(),
                    "opaque_resize": self.opaqueResize(),
                },
                "current_state": self.get_splitter_state(),
            }
            with Path(file_path).open("w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("📤 스플리터 설정 내보내기 완료: %s", file_path)
            return True
        except Exception as e:
            logger.info("❌ 스플리터 설정 내보내기 실패: %s", e)
            return False

    def import_splitter_config(self, file_path):
        """스플리터 설정 가져오기"""
        try:
            with Path(file_path).open(encoding="utf-8") as f:
                config = json.load(f)
            if "settings" in config:
                settings = config["settings"]
                if "preferred_ratios" in settings:
                    self._preferred_ratios = settings["preferred_ratios"]
                if "min_sizes" in settings:
                    self._min_sizes = settings["min_sizes"]
                    self.set_minimum_sizes(self._min_sizes)
                if "auto_adjust" in settings:
                    self._auto_adjust_enabled = settings["auto_adjust"]
                if "handle_width" in settings:
                    self.setHandleWidth(settings["handle_width"])
                if "children_collapsible" in settings:
                    self.setChildrenCollapsible(settings["children_collapsible"])
                if "opaque_resize" in settings:
                    self.setOpaqueResize(settings["opaque_resize"])
                self.restore_preferred_ratio()
                logger.info("📥 스플리터 설정 가져오기 완료: %s", file_path)
                return True
            return False
        except Exception as e:
            logger.info("❌ 스플리터 설정 가져오기 실패: %s", e)
            return False

    def get_splitter_info(self):
        """스플리터 정보 반환 (디버깅 및 모니터링용)"""
        info = {
            "widget_count": self.count(),
            "current_sizes": self.sizes(),
            "total_size": sum(self.sizes()),
            "preferred_ratios": self._preferred_ratios,
            "min_sizes": self._min_sizes,
            "auto_adjust_enabled": self._auto_adjust_enabled,
            "handle_width": self.handleWidth(),
            "children_collapsible": self.childrenCollapsible(),
            "opaque_resize": self.opaqueResize(),
            "orientation": "Vertical" if self.orientation() == Qt.Vertical else "Horizontal",
        }
        widget_info = []
        for i in range(self.count()):
            widget = self.widget(i)
            widget_info.append(
                {
                    "index": i,
                    "class_name": widget.__class__.__name__,
                    "size": self.sizes()[i],
                    "min_size": (
                        widget.minimumSize().height()
                        if self.orientation() == Qt.Vertical
                        else widget.minimumSize().width()
                    ),
                    "visible": widget.isVisible(),
                }
            )
        info["widgets"] = widget_info
        return info

    def validate_splitter_state(self, state):
        """스플리터 상태 유효성 검사"""
        if not isinstance(state, dict):
            return False, "상태가 딕셔너리가 아닙니다"
        required_keys = ["sizes", "preferred_ratios", "min_sizes"]
        for key in required_keys:
            if key not in state:
                return False, f"필수 키 '{key}'가 없습니다"
        if not isinstance(state["sizes"], list) or len(state["sizes"]) != self.count():
            return (
                False,
                f"크기 목록이 유효하지 않습니다 (예상: {self.count()}, 실제: {len(state['sizes'])})",
            )
        if (
            not isinstance(state["preferred_ratios"], list)
            or len(state["preferred_ratios"]) != self.count()
        ):
            return (
                False,
                f"비율 목록이 유효하지 않습니다 (예상: {self.count()}, 실제: {len(state['preferred_ratios'])})",
            )
        ratio_sum = sum(state["preferred_ratios"])
        if abs(ratio_sum - 1.0) > 0.01:
            return False, f"비율 합계가 1.0이 아닙니다 (실제: {ratio_sum})"
        return True, "유효한 상태입니다"

    def reset_to_defaults(self):
        """기본값으로 리셋"""
        self._preferred_ratios = [0.6, 0.4]
        self._min_sizes = [200, 150]
        self.restore_preferred_ratio()


class SplitterControlPanel(QWidget):
    """스플리터 제어 패널"""

    def __init__(self, splitter, parent=None):
        super().__init__(parent)
        self.splitter = splitter
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        self.btn_auto_adjust = QToolButton()
        self.btn_auto_adjust.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.btn_auto_adjust.setToolTip("자동 크기 조정")
        self.btn_auto_adjust.setCheckable(True)
        self.btn_auto_adjust.setChecked(True)
        layout.addWidget(self.btn_auto_adjust)
        self.btn_restore_ratio = QToolButton()
        self.btn_restore_ratio.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_restore_ratio.setToolTip("선호 비율 복원")
        layout.addWidget(self.btn_restore_ratio)
        self.btn_reset = QToolButton()
        self.btn_reset.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.btn_reset.setToolTip("기본값으로 리셋")
        layout.addWidget(self.btn_reset)
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        self.ratio_label = QLabel("비율: 60% / 40%")
        self.ratio_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        layout.addWidget(self.ratio_label)
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        self.btn_export = QToolButton()
        self.btn_export.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export.setToolTip("설정 내보내기")
        layout.addWidget(self.btn_export)
        self.btn_import = QToolButton()
        self.btn_import.setIcon(self.style().standardIcon(QStyle.SP_FileDialogStart))
        self.btn_import.setToolTip("설정 가져오기")
        layout.addWidget(self.btn_import)
        self.btn_info = QToolButton()
        self.btn_info.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.btn_info.setToolTip("스플리터 정보")
        layout.addWidget(self.btn_info)
        layout.addStretch(1)

    def setup_connections(self):
        """시그널 연결"""
        self.btn_auto_adjust.toggled.connect(self.splitter.enable_auto_adjust)
        self.btn_restore_ratio.clicked.connect(self.splitter.restore_preferred_ratio)
        self.btn_reset.clicked.connect(self.splitter.reset_to_defaults)
        self.btn_export.clicked.connect(self.export_config)
        self.btn_import.clicked.connect(self.import_config)
        self.btn_info.clicked.connect(self.show_splitter_info)
        self.splitter.splitter_state_changed.connect(self.update_ratio_label)

    def update_ratio_label(self, state):
        """비율 라벨 업데이트"""
        sizes = state.get("sizes", [])
        if len(sizes) >= 2 and sum(sizes) > 0:
            ratio1 = int(sizes[0] / sum(sizes) * 100)
            ratio2 = int(sizes[1] / sum(sizes) * 100)
            self.ratio_label.setText(f"비율: {ratio1}% / {ratio2}%")

    def export_config(self):
        """설정 내보내기"""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self, "스플리터 설정 내보내기", "", "JSON 파일 (*.json)"
        )
        if file_path:
            success = self.splitter.export_splitter_config(file_path)
            if success:
                self.show_status_message("✅ 설정 내보내기 완료")
            else:
                self.show_status_message("❌ 설정 내보내기 실패")

    def import_config(self):
        """설정 가져오기"""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "스플리터 설정 가져오기", "", "JSON 파일 (*.json)"
        )
        if file_path:
            success = self.splitter.import_splitter_config(file_path)
            if success:
                self.show_status_message("✅ 설정 가져오기 완료")
            else:
                self.show_status_message("❌ 설정 가져오기 실패")

    def show_splitter_info(self):
        """스플리터 정보 표시"""
        info = self.splitter.get_splitter_info()
        from PyQt5.QtWidgets import QMessageBox

        msg = QMessageBox(self)
        msg.setWindowTitle("스플리터 정보")
        msg.setIcon(QMessageBox.Information)
        info_text = f"""
        📊 스플리터 정보

        🏗️ 기본 정보:
        - 위젯 수: {info["widget_count"]}
        - 방향: {info["orientation"]}
        - 핸들 너비: {info["handle_width"]}px

        📏 크기 정보:
        - 현재 크기: {info["current_sizes"]}
        - 총 크기: {info["total_size"]}px
        - 선호 비율: {info["preferred_ratios"]}
        - 최소 크기: {info["min_sizes"]}

        ⚙️ 설정:
        - 자동 조정: {"활성화" if info["auto_adjust_enabled"] else "비활성화"}
        - 자식 접기: {"허용" if info["children_collapsible"] else "금지"}
        - 불투명 리사이즈: {"활성화" if info["opaque_resize"] else "비활성화"}

        🧩 위젯 상세:
        """
        for widget in info["widgets"]:
            info_text += f"\n  {widget['index']}: {widget['class_name']}"
            info_text += f" (크기: {widget['size']}px, 최소: {widget['min_size']}px)"
            info_text += f" {'[보임]' if widget['visible'] else '[숨김]'}"
        msg.setText(info_text)
        msg.exec_()

    def show_status_message(self, message):
        """상태 메시지 표시 (간단한 토스트 형태)"""
        original_text = self.ratio_label.text()
        self.ratio_label.setText(message)
        self.ratio_label.setStyleSheet("color: #e74c3c; font-size: 10px; font-weight: bold;")
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(2000, lambda: self.restore_ratio_label(original_text))

    def restore_ratio_label(self, text):
        """비율 라벨 복원"""
        self.ratio_label.setText(text)
        self.ratio_label.setStyleSheet("color: #7f8c8d; font-size: 10px;")
