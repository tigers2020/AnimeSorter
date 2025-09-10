"""
BindingHelper - View와 ViewModel 간의 데이터 바인딩 헬퍼

Phase 2 MVVM 아키텍처의 일부로, View와 ViewModel 간의 데이터 바인딩을 쉽게 만들어줍니다.
"""

import logging

logger = logging.getLogger(__name__)
from collections.abc import Callable
from typing import Any

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QLabel,
                             QLineEdit, QListWidget, QProgressBar, QPushButton,
                             QSlider, QSpinBox, QTableWidget, QTreeWidget,
                             QWidget)


class BindingHelper(QObject):
    """View와 ViewModel 간의 데이터 바인딩을 관리하는 헬퍼 클래스"""

    binding_created = pyqtSignal(str, str)
    binding_removed = pyqtSignal(str, str)
    binding_error = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._bindings: dict[str, dict[str, Any]] = {}
        self._viewmodel: QObject | None = None
        self._view: QWidget | None = None
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_all_bindings)
        self._update_timer.start(100)
        self.logger.info("BindingHelper 초기화 완료")

    def set_viewmodel(self, viewmodel: QObject):
        """ViewModel 설정"""
        self._viewmodel = viewmodel
        self.logger.info(f"ViewModel 설정: {type(viewmodel).__name__}")

    def set_view(self, view: QWidget):
        """View 설정"""
        self._view = view
        self.logger.info(f"View 설정: {type(view).__name__}")

    def create_binding(
        self,
        view_property: str,
        viewmodel_property: str,
        binding_type: str = "two_way",
        converter: Callable | None = None,
        validator: Callable | None = None,
    ) -> bool:
        """바인딩 생성"""
        try:
            if not self._view or not self._viewmodel:
                self.logger.error("View 또는 ViewModel이 설정되지 않았습니다")
                return False
            binding_id = f"{view_property}_{viewmodel_property}"
            self._bindings[binding_id] = {
                "view_property": view_property,
                "viewmodel_property": viewmodel_property,
                "binding_type": binding_type,
                "converter": converter,
                "validator": validator,
                "active": True,
            }
            if binding_type == "one_way":
                self._setup_one_way_binding(binding_id)
            elif binding_type == "two_way":
                self._setup_two_way_binding(binding_id)
            elif binding_type == "one_way_to_source":
                self._setup_one_way_to_source_binding(binding_id)
            else:
                self.logger.error(f"지원하지 않는 바인딩 타입: {binding_type}")
                return False
            self.binding_created.emit(view_property, viewmodel_property)
            self.logger.info(f"바인딩 생성 완료: {view_property} <-> {viewmodel_property}")
            return True
        except Exception as e:
            self.logger.error(f"바인딩 생성 중 오류 발생: {e}")
            self.binding_error.emit("creation_error", str(e))
            return False

    def remove_binding(self, view_property: str, viewmodel_property: str) -> bool:
        """바인딩 제거"""
        try:
            binding_id = f"{view_property}_{viewmodel_property}"
            if binding_id in self._bindings:
                self._bindings[binding_id]["active"] = False
                del self._bindings[binding_id]
                self.binding_removed.emit(view_property, viewmodel_property)
                self.logger.info(f"바인딩 제거 완료: {view_property} <-> {viewmodel_property}")
                return True
            self.logger.warning(f"제거할 바인딩을 찾을 수 없음: {binding_id}")
            return False
        except Exception as e:
            self.logger.error(f"바인딩 제거 중 오류 발생: {e}")
            return False

    def remove_all_bindings(self):
        """모든 바인딩 제거"""
        try:
            binding_ids = list(self._bindings.keys())
            for binding_id in binding_ids:
                binding = self._bindings[binding_id]
                self.remove_binding(binding["view_property"], binding["viewmodel_property"])
            self.logger.info("모든 바인딩 제거 완료")
        except Exception as e:
            self.logger.error(f"모든 바인딩 제거 중 오류 발생: {e}")

    def get_binding_info(
        self, view_property: str, viewmodel_property: str
    ) -> dict[str, Any] | None:
        """바인딩 정보 반환"""
        binding_id = f"{view_property}_{viewmodel_property}"
        return self._bindings.get(binding_id)

    def get_all_bindings(self) -> list[dict[str, Any]]:
        """모든 바인딩 정보 반환"""
        return list(self._bindings.values())

    def is_binding_active(self, view_property: str, viewmodel_property: str) -> bool:
        """바인딩이 활성화되어 있는지 확인"""
        binding_id = f"{view_property}_{viewmodel_property}"
        binding = self._bindings.get(binding_id)
        return binding is not None and binding.get("active", False)

    def bind_text_input(
        self, _line_edit: QLineEdit, viewmodel_property: str, binding_type: str = "two_way"
    ) -> bool:
        """텍스트 입력 위젯 바인딩"""
        return self.create_binding("text", viewmodel_property, binding_type)

    def bind_checkbox(
        self, _checkbox: QCheckBox, viewmodel_property: str, binding_type: str = "two_way"
    ) -> bool:
        """체크박스 바인딩"""
        return self.create_binding("checked", viewmodel_property, binding_type)

    def bind_spinbox(
        self,
        _spinbox: QSpinBox | QDoubleSpinBox,
        viewmodel_property: str,
        binding_type: str = "two_way",
    ) -> bool:
        """스핀박스 바인딩"""
        return self.create_binding("value", viewmodel_property, binding_type)

    def bind_combobox(
        self, _combobox: QComboBox, viewmodel_property: str, binding_type: str = "two_way"
    ) -> bool:
        """콤보박스 바인딩"""
        return self.create_binding("currentText", viewmodel_property, binding_type)

    def bind_slider(
        self, _slider: QSlider, viewmodel_property: str, binding_type: str = "two_way"
    ) -> bool:
        """슬라이더 바인딩"""
        return self.create_binding("value", viewmodel_property, binding_type)

    def bind_progressbar(
        self, _progressbar: QProgressBar, viewmodel_property: str, binding_type: str = "one_way"
    ) -> bool:
        """프로그레스바 바인딩 (일반적으로 읽기 전용)"""
        return self.create_binding("value", viewmodel_property, binding_type)

    def bind_label(
        self, _label: QLabel, viewmodel_property: str, binding_type: str = "one_way"
    ) -> bool:
        """라벨 바인딩 (일반적으로 읽기 전용)"""
        return self.create_binding("text", viewmodel_property, binding_type)

    def bind_button(
        self, _button: QPushButton, viewmodel_property: str, binding_type: str = "one_way_to_source"
    ) -> bool:
        """버튼 바인딩 (일반적으로 클릭 이벤트만)"""
        return self.create_binding("clicked", viewmodel_property, binding_type)

    def bind_list_widget(
        self, _list_widget: QListWidget, viewmodel_property: str, binding_type: str = "one_way"
    ) -> bool:
        """리스트 위젯 바인딩"""
        return self.create_binding("items", viewmodel_property, binding_type)

    def bind_table_widget(
        self, _table_widget: QTableWidget, viewmodel_property: str, binding_type: str = "one_way"
    ) -> bool:
        """테이블 위젯 바인딩"""
        return self.create_binding("data", viewmodel_property, binding_type)

    def bind_tree_widget(
        self, _tree_widget: QTreeWidget, viewmodel_property: str, binding_type: str = "one_way"
    ) -> bool:
        """트리 위젯 바인딩"""
        return self.create_binding("data", viewmodel_property, binding_type)

    def bind_with_converter(
        self,
        view_property: str,
        viewmodel_property: str,
        converter: Callable,
        binding_type: str = "two_way",
    ) -> bool:
        """컨버터가 있는 바인딩 생성"""
        return self.create_binding(view_property, viewmodel_property, binding_type, converter)

    def bind_with_validator(
        self,
        view_property: str,
        viewmodel_property: str,
        validator: Callable,
        binding_type: str = "two_way",
    ) -> bool:
        """검증기가 있는 바인딩 생성"""
        return self.create_binding(view_property, viewmodel_property, binding_type, None, validator)

    def bind_with_condition(
        self,
        view_property: str,
        viewmodel_property: str,
        condition_property: str,
        condition_value: Any,
        binding_type: str = "two_way",
    ) -> bool:
        """조건부 바인딩 생성"""
        try:
            binding_id = f"{view_property}_{viewmodel_property}"
            self._bindings[binding_id] = {
                "view_property": view_property,
                "viewmodel_property": viewmodel_property,
                "binding_type": binding_type,
                "converter": None,
                "validator": None,
                "active": True,
                "conditional": True,
                "condition_property": condition_property,
                "condition_value": condition_value,
            }
            self._setup_conditional_binding(binding_id)
            self.binding_created.emit(view_property, viewmodel_property)
            self.logger.info(f"조건부 바인딩 생성 완료: {view_property} <-> {viewmodel_property}")
            return True
        except Exception as e:
            self.logger.error(f"조건부 바인딩 생성 중 오류 발생: {e}")
            return False

    def _setup_one_way_binding(self, binding_id: str):
        """단방향 바인딩 설정 (ViewModel -> View)"""
        binding = self._bindings[binding_id]
        view_property = binding["view_property"]
        viewmodel_property = binding["viewmodel_property"]
        if hasattr(self._viewmodel, f"{viewmodel_property}Changed"):
            signal = getattr(self._viewmodel, f"{viewmodel_property}Changed")
            signal.connect(lambda: self._update_view_property(view_property, viewmodel_property))
        self._update_view_property(view_property, viewmodel_property)

    def _setup_two_way_binding(self, binding_id: str):
        """양방향 바인딩 설정"""
        binding = self._bindings[binding_id]
        binding["view_property"]
        binding["viewmodel_property"]
        self._setup_one_way_binding(binding_id)
        self._setup_view_to_viewmodel_binding(binding_id)

    def _setup_one_way_to_source_binding(self, binding_id: str):
        """단방향 바인딩 설정 (View -> ViewModel)"""
        binding = self._bindings[binding_id]
        binding["view_property"]
        binding["viewmodel_property"]
        self._setup_view_to_viewmodel_binding(binding_id)

    def _setup_conditional_binding(self, binding_id: str):
        """조건부 바인딩 설정"""
        binding = self._bindings[binding_id]
        binding["view_property"]
        binding["viewmodel_property"]
        condition_property = binding["condition_property"]
        if hasattr(self._viewmodel, f"{condition_property}Changed"):
            signal = getattr(self._viewmodel, f"{condition_property}Changed")
            signal.connect(lambda: self._update_conditional_binding(binding_id))
        self._update_conditional_binding(binding_id)

    def _setup_view_to_viewmodel_binding(self, binding_id: str):
        """View에서 ViewModel로의 바인딩 설정"""
        binding = self._bindings[binding_id]
        view_property = binding["view_property"]
        viewmodel_property = binding["viewmodel_property"]
        view_widget = self._find_view_widget(view_property)
        if not view_widget:
            return
        if hasattr(view_widget, f"{view_property}Changed"):
            signal = getattr(view_widget, f"{view_property}Changed")
            signal.connect(
                lambda: self._update_viewmodel_property(view_property, viewmodel_property)
            )
        self._connect_widget_specific_signals(view_widget, view_property, viewmodel_property)

    def _connect_widget_specific_signals(
        self, widget: QWidget, view_property: str, viewmodel_property: str
    ):
        """위젯 타입별 시그널 연결"""
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(
                lambda text: self._update_viewmodel_property(view_property, viewmodel_property)
            )
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(
                lambda checked: self._update_viewmodel_property(view_property, viewmodel_property)
            )
        elif isinstance(widget, QSpinBox | QDoubleSpinBox):
            widget.valueChanged.connect(
                lambda value: self._update_viewmodel_property(view_property, viewmodel_property)
            )
        elif isinstance(widget, QComboBox):
            widget.currentTextChanged.connect(
                lambda text: self._update_viewmodel_property(view_property, viewmodel_property)
            )
        elif isinstance(widget, QSlider):
            widget.valueChanged.connect(
                lambda value: self._update_viewmodel_property(view_property, viewmodel_property)
            )
        elif isinstance(widget, QPushButton):
            widget.clicked.connect(
                lambda: self._update_viewmodel_property(view_property, viewmodel_property)
            )

    def _update_view_property(self, view_property: str, viewmodel_property: str):
        """View 속성 업데이트"""
        try:
            if not self._view or not self._viewmodel:
                return
            if hasattr(self._viewmodel, viewmodel_property):
                value = getattr(self._viewmodel, viewmodel_property)
                view_widget = self._find_view_widget(view_property)
                if view_widget and hasattr(view_widget, f"set{view_property.capitalize()}"):
                    setter = getattr(view_widget, f"set{view_property.capitalize()}")
                    setter(value)
        except Exception as e:
            self.logger.error(f"View 속성 업데이트 중 오류 발생: {e}")

    def _update_viewmodel_property(self, view_property: str, viewmodel_property: str):
        """ViewModel 속성 업데이트"""
        try:
            if not self._view or not self._viewmodel:
                return
            view_widget = self._find_view_widget(view_property)
            if view_widget and hasattr(view_widget, view_property):
                value = getattr(view_widget, view_property)
                if hasattr(self._viewmodel, f"set{viewmodel_property.capitalize()}"):
                    setter = getattr(self._viewmodel, f"set{viewmodel_property.capitalize()}")
                    setter(value)
        except Exception as e:
            self.logger.error(f"ViewModel 속성 업데이트 중 오류 발생: {e}")

    def _update_conditional_binding(self, binding_id: str):
        """조건부 바인딩 업데이트"""
        try:
            binding = self._bindings[binding_id]
            condition_property = binding["condition_property"]
            condition_value = binding["condition_value"]
            if hasattr(self._viewmodel, condition_property):
                current_value = getattr(self._viewmodel, condition_property)
                is_active = current_value == condition_value
                binding["active"] = is_active
                if is_active:
                    self._setup_two_way_binding(binding_id)
                else:
                    pass
        except Exception as e:
            self.logger.error(f"조건부 바인딩 업데이트 중 오류 발생: {e}")

    def _update_all_bindings(self):
        """모든 활성 바인딩 업데이트"""
        try:
            for _binding_id, binding in self._bindings.items():
                if binding.get("active", False):
                    self._update_view_property(
                        binding["view_property"], binding["viewmodel_property"]
                    )
        except Exception as e:
            self.logger.error(f"모든 바인딩 업데이트 중 오류 발생: {e}")

    def _find_view_widget(self, property_name: str) -> QWidget | None:
        """View에서 특정 속성을 가진 위젯 찾기"""
        if not self._view:
            return None
        if hasattr(self._view, property_name):
            return self._view
        return None

    def get_binding_summary(self) -> dict[str, Any]:
        """바인딩 요약 정보 반환"""
        return {
            "total_bindings": len(self._bindings),
            "active_bindings": len([b for b in self._bindings.values() if b.get("active", False)]),
            "binding_types": {
                "one_way": len(
                    [b for b in self._bindings.values() if b.get("binding_type") == "one_way"]
                ),
                "two_way": len(
                    [b for b in self._bindings.values() if b.get("binding_type") == "two_way"]
                ),
                "one_way_to_source": len(
                    [
                        b
                        for b in self._bindings.values()
                        if b.get("binding_type") == "one_way_to_source"
                    ]
                ),
                "conditional": len(
                    [b for b in self._bindings.values() if b.get("conditional", False)]
                ),
            },
            "bindings": self.get_all_bindings(),
        }
