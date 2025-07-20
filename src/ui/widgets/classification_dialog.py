"""
분류 설정 다이얼로그
고급 분류 시스템의 설정을 관리하는 UI
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem,
    QGroupBox, QFormLayout, QMessageBox, QFileDialog,
    QProgressBar, QSlider, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from src.utils.advanced_classifier import (
    AdvancedClassifier, ClassificationStrategy, ClassificationRule,
    SmartClassifier, TagBasedClassifier, RuleBasedClassifier
)
from src.config.config_manager import ConfigManager


class ClassificationDialog(QDialog):
    """분류 설정 다이얼로그"""
    
    def __init__(self, parent=None, config_manager: Optional[ConfigManager] = None):
        super().__init__(parent)
        self.config_manager = config_manager or ConfigManager()
        
        # 분류기 초기화
        self.classifier = AdvancedClassifier()
        
        self.setWindowTitle("고급 분류 설정")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_settings()
        self._create_connections()
        
    def _setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 탭 추가
        self._create_general_tab()
        self._create_smart_classification_tab()
        self._create_tag_based_tab()
        self._create_rule_based_tab()
        self._create_advanced_tab()
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("저장")
        self.save_button.setDefault(True)
        
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        
        self.apply_button = QPushButton("적용")
        self.apply_button.clicked.connect(self._apply_settings)
        
        self.export_button = QPushButton("내보내기")
        self.export_button.clicked.connect(self._export_config)
        
        self.import_button = QPushButton("가져오기")
        self.import_button.clicked.connect(self._import_config)
        
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.import_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
    def _create_general_tab(self):
        """일반 설정 탭"""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)
        
        # 분류 전략 우선순위
        strategy_group = QGroupBox("분류 전략 우선순위")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_list = QListWidget()
        self.strategy_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        
        # 전략 목록 초기화
        strategies = [
            ("태그 기반 분류", ClassificationStrategy.TAG_BASED),
            ("규칙 기반 분류", ClassificationStrategy.RULE_BASED),
            ("스마트 분류", ClassificationStrategy.SMART),
            ("사용자 정의", ClassificationStrategy.USER_DEFINED)
        ]
        
        for name, strategy in strategies:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, strategy)
            self.strategy_list.addItem(item)
        
        strategy_layout.addWidget(self.strategy_list)
        layout.addWidget(strategy_group)
        
        # 분류 통계
        stats_group = QGroupBox("분류 통계")
        stats_layout = QFormLayout(stats_group)
        
        self.tag_count_label = QLabel("0")
        self.rule_count_label = QLabel("0")
        self.enabled_rules_label = QLabel("0")
        
        stats_layout.addRow("태그 수:", self.tag_count_label)
        stats_layout.addRow("규칙 수:", self.rule_count_label)
        stats_layout.addRow("활성 규칙:", self.enabled_rules_label)
        
        layout.addWidget(stats_group)
        
        # 새로고침 버튼
        refresh_button = QPushButton("통계 새로고침")
        refresh_button.clicked.connect(self._refresh_stats)
        layout.addWidget(refresh_button)
        
        layout.addStretch()
        self.tab_widget.addTab(general_widget, "일반")
        
    def _create_smart_classification_tab(self):
        """스마트 분류 탭"""
        smart_widget = QWidget()
        layout = QVBoxLayout(smart_widget)
        
        # 장르 키워드 설정
        genre_group = QGroupBox("장르 키워드")
        genre_layout = QVBoxLayout(genre_group)
        
        self.genre_table = QTableWidget()
        self.genre_table.setColumnCount(2)
        self.genre_table.setHorizontalHeaderLabels(["장르", "키워드"])
        self.genre_table.horizontalHeader().setStretchLastSection(True)
        
        # 기본 장르 키워드 로드
        self._load_genre_keywords()
        
        genre_layout.addWidget(self.genre_table)
        
        # 장르 키워드 버튼
        genre_button_layout = QHBoxLayout()
        add_genre_button = QPushButton("장르 추가")
        add_genre_button.clicked.connect(self._add_genre)
        remove_genre_button = QPushButton("장르 제거")
        remove_genre_button.clicked.connect(self._remove_genre)
        
        genre_button_layout.addWidget(add_genre_button)
        genre_button_layout.addWidget(remove_genre_button)
        genre_button_layout.addStretch()
        
        genre_layout.addLayout(genre_button_layout)
        layout.addWidget(genre_group)
        
        # 품질 키워드 설정
        quality_group = QGroupBox("품질 키워드")
        quality_layout = QVBoxLayout(quality_group)
        
        self.quality_table = QTableWidget()
        self.quality_table.setColumnCount(2)
        self.quality_table.setHorizontalHeaderLabels(["품질", "키워드"])
        self.quality_table.horizontalHeader().setStretchLastSection(True)
        
        # 기본 품질 키워드 로드
        self._load_quality_keywords()
        
        quality_layout.addWidget(self.quality_table)
        
        # 품질 키워드 버튼
        quality_button_layout = QHBoxLayout()
        add_quality_button = QPushButton("품질 추가")
        add_quality_button.clicked.connect(self._add_quality)
        remove_quality_button = QPushButton("품질 제거")
        remove_quality_button.clicked.connect(self._remove_quality)
        
        quality_button_layout.addWidget(add_quality_button)
        quality_button_layout.addWidget(remove_quality_button)
        quality_button_layout.addStretch()
        
        quality_layout.addLayout(quality_button_layout)
        layout.addWidget(quality_group)
        
        self.tab_widget.addTab(smart_widget, "스마트 분류")
        
    def _create_tag_based_tab(self):
        """태그 기반 분류 탭"""
        tag_widget = QWidget()
        layout = QVBoxLayout(tag_widget)
        
        # 태그 관리
        tag_group = QGroupBox("태그 관리")
        tag_layout = QVBoxLayout(tag_group)
        
        # 태그 목록
        self.tag_list = QListWidget()
        tag_layout.addWidget(self.tag_list)
        
        # 태그 추가/제거
        tag_button_layout = QHBoxLayout()
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("애니메 제목")
        
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("태그")
        
        add_tag_button = QPushButton("태그 추가")
        add_tag_button.clicked.connect(self._add_tag)
        
        remove_tag_button = QPushButton("태그 제거")
        remove_tag_button.clicked.connect(self._remove_tag)
        
        tag_button_layout.addWidget(QLabel("제목:"))
        tag_button_layout.addWidget(self.title_edit)
        tag_button_layout.addWidget(QLabel("태그:"))
        tag_button_layout.addWidget(self.tag_edit)
        tag_button_layout.addWidget(add_tag_button)
        tag_button_layout.addWidget(remove_tag_button)
        
        tag_layout.addLayout(tag_button_layout)
        layout.addWidget(tag_group)
        
        # 태그 통계
        tag_stats_group = QGroupBox("태그 통계")
        tag_stats_layout = QFormLayout(tag_stats_group)
        
        self.total_tags_label = QLabel("0")
        self.unique_titles_label = QLabel("0")
        self.most_used_tag_label = QLabel("-")
        
        tag_stats_layout.addRow("총 태그 수:", self.total_tags_label)
        tag_stats_layout.addRow("고유 제목 수:", self.unique_titles_label)
        tag_stats_layout.addRow("가장 많이 사용된 태그:", self.most_used_tag_label)
        
        layout.addWidget(tag_stats_group)
        
        self.tab_widget.addTab(tag_widget, "태그 기반")
        
    def _create_rule_based_tab(self):
        """규칙 기반 분류 탭"""
        rule_widget = QWidget()
        layout = QVBoxLayout(rule_widget)
        
        # 규칙 목록
        rule_group = QGroupBox("분류 규칙")
        rule_layout = QVBoxLayout(rule_group)
        
        self.rule_table = QTableWidget()
        self.rule_table.setColumnCount(5)
        self.rule_table.setHorizontalHeaderLabels([
            "이름", "패턴", "대상 폴더", "우선순위", "활성"
        ])
        self.rule_table.horizontalHeader().setStretchLastSection(True)
        
        rule_layout.addWidget(self.rule_table)
        
        # 규칙 추가/제거
        rule_button_layout = QHBoxLayout()
        add_rule_button = QPushButton("규칙 추가")
        add_rule_button.clicked.connect(self._add_rule)
        remove_rule_button = QPushButton("규칙 제거")
        remove_rule_button.clicked.connect(self._remove_rule)
        edit_rule_button = QPushButton("규칙 편집")
        edit_rule_button.clicked.connect(self._edit_rule)
        
        rule_button_layout.addWidget(add_rule_button)
        rule_button_layout.addWidget(edit_rule_button)
        rule_button_layout.addWidget(remove_rule_button)
        rule_button_layout.addStretch()
        
        rule_layout.addLayout(rule_button_layout)
        layout.addWidget(rule_group)
        
        # 규칙 편집 영역
        edit_group = QGroupBox("규칙 편집")
        edit_layout = QFormLayout(edit_group)
        
        self.rule_name_edit = QLineEdit()
        self.rule_pattern_edit = QLineEdit()
        self.rule_target_edit = QLineEdit()
        self.rule_priority_spin = QSpinBox()
        self.rule_priority_spin.setRange(1, 100)
        self.rule_enabled_check = QCheckBox()
        self.rule_description_edit = QTextEdit()
        self.rule_description_edit.setMaximumHeight(60)
        
        edit_layout.addRow("이름:", self.rule_name_edit)
        edit_layout.addRow("패턴:", self.rule_pattern_edit)
        edit_layout.addRow("대상 폴더:", self.rule_target_edit)
        edit_layout.addRow("우선순위:", self.rule_priority_spin)
        edit_layout.addRow("활성:", self.rule_enabled_check)
        edit_layout.addRow("설명:", self.rule_description_edit)
        
        layout.addWidget(edit_group)
        
        self.tab_widget.addTab(rule_widget, "규칙 기반")
        
    def _create_advanced_tab(self):
        """고급 설정 탭"""
        advanced_widget = QWidget()
        layout = QVBoxLayout(advanced_widget)
        
        # 성능 설정
        performance_group = QGroupBox("성능 설정")
        performance_layout = QFormLayout(performance_group)
        
        self.cache_enabled_check = QCheckBox("캐시 사용")
        self.cache_enabled_check.setChecked(True)
        
        self.parallel_processing_check = QCheckBox("병렬 처리")
        self.parallel_processing_check.setChecked(True)
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 16)
        self.max_workers_spin.setValue(4)
        
        performance_layout.addRow("캐시 사용:", self.cache_enabled_check)
        performance_layout.addRow("병렬 처리:", self.parallel_processing_check)
        performance_layout.addRow("최대 워커 수:", self.max_workers_spin)
        
        layout.addWidget(performance_group)
        
        # 테스트 영역
        test_group = QGroupBox("분류 테스트")
        test_layout = QVBoxLayout(test_group)
        
        # 테스트 파일명 입력
        test_input_layout = QHBoxLayout()
        self.test_filename_edit = QLineEdit()
        self.test_filename_edit.setPlaceholderText("테스트할 파일명을 입력하세요")
        test_button = QPushButton("테스트")
        test_button.clicked.connect(self._test_classification)
        
        test_input_layout.addWidget(self.test_filename_edit)
        test_input_layout.addWidget(test_button)
        
        test_layout.addLayout(test_input_layout)
        
        # 테스트 결과
        self.test_result_text = QTextEdit()
        self.test_result_text.setMaximumHeight(150)
        self.test_result_text.setReadOnly(True)
        test_layout.addWidget(self.test_result_text)
        
        layout.addWidget(test_group)
        
        # 백업/복원
        backup_group = QGroupBox("백업 및 복원")
        backup_layout = QHBoxLayout(backup_group)
        
        backup_button = QPushButton("설정 백업")
        backup_button.clicked.connect(self._backup_settings)
        
        restore_button = QPushButton("설정 복원")
        restore_button.clicked.connect(self._restore_settings)
        
        reset_button = QPushButton("기본값으로 초기화")
        reset_button.clicked.connect(self._reset_to_defaults)
        
        backup_layout.addWidget(backup_button)
        backup_layout.addWidget(restore_button)
        backup_layout.addWidget(reset_button)
        
        layout.addWidget(backup_group)
        layout.addStretch()
        
        self.tab_widget.addTab(advanced_widget, "고급")
        
    def _load_settings(self):
        """설정 로드"""
        self._refresh_stats()
        self._load_tags()
        self._load_rules()
        
    def _create_connections(self):
        """시그널 연결"""
        self.save_button.clicked.connect(self._save_settings)
        self.rule_table.itemSelectionChanged.connect(self._on_rule_selection_changed)
        self.tag_list.itemSelectionChanged.connect(self._on_tag_selection_changed)
        
    def _refresh_stats(self):
        """통계 새로고침"""
        stats = self.classifier.get_classification_stats()
        
        self.tag_count_label.setText(str(stats["tag_count"]))
        self.rule_count_label.setText(str(stats["rule_count"]))
        self.enabled_rules_label.setText(str(stats["enabled_rules"]))
        
    def _load_genre_keywords(self):
        """장르 키워드 로드"""
        smart_classifier = self.classifier.smart_classifier
        self.genre_table.setRowCount(len(smart_classifier.genre_keywords))
        
        for row, (genre, keywords) in enumerate(smart_classifier.genre_keywords.items()):
            self.genre_table.setItem(row, 0, QTableWidgetItem(genre))
            self.genre_table.setItem(row, 1, QTableWidgetItem(", ".join(keywords)))
            
    def _load_quality_keywords(self):
        """품질 키워드 로드"""
        smart_classifier = self.classifier.smart_classifier
        self.quality_table.setRowCount(len(smart_classifier.quality_keywords))
        
        for row, (quality, keywords) in enumerate(smart_classifier.quality_keywords.items()):
            self.quality_table.setItem(row, 0, QTableWidgetItem(quality))
            self.quality_table.setItem(row, 1, QTableWidgetItem(", ".join(keywords)))
            
    def _load_tags(self):
        """태그 로드"""
        self.tag_list.clear()
        
        for title, tags in self.classifier.tag_classifier.tags.items():
            item_text = f"{title}: {', '.join(tags)}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, (title, tags))
            self.tag_list.addItem(item)
            
        self._update_tag_stats()
        
    def _load_rules(self):
        """규칙 로드"""
        self.rule_table.setRowCount(len(self.classifier.rule_classifier.rules))
        
        for row, rule in enumerate(self.classifier.rule_classifier.rules):
            self.rule_table.setItem(row, 0, QTableWidgetItem(rule.name))
            self.rule_table.setItem(row, 1, QTableWidgetItem(rule.pattern))
            self.rule_table.setItem(row, 2, QTableWidgetItem(rule.target_folder))
            self.rule_table.setItem(row, 3, QTableWidgetItem(str(rule.priority)))
            
            enabled_item = QTableWidgetItem()
            enabled_item.setCheckState(Qt.CheckState.Checked if rule.enabled else Qt.CheckState.Unchecked)
            self.rule_table.setItem(row, 4, enabled_item)
            
    def _update_tag_stats(self):
        """태그 통계 업데이트"""
        tags = self.classifier.tag_classifier.tags
        
        total_tags = sum(len(tag_list) for tag_list in tags.values())
        unique_titles = len(tags)
        
        # 가장 많이 사용된 태그 찾기
        tag_counts = {}
        for tag_list in tags.values():
            for tag in tag_list:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        most_used_tag = max(tag_counts.items(), key=lambda x: x[1])[0] if tag_counts else "-"
        
        self.total_tags_label.setText(str(total_tags))
        self.unique_titles_label.setText(str(unique_titles))
        self.most_used_tag_label.setText(most_used_tag)
        
    def _add_tag(self):
        """태그 추가"""
        title = self.title_edit.text().strip()
        tag = self.tag_edit.text().strip()
        
        if not title or not tag:
            QMessageBox.warning(self, "입력 오류", "제목과 태그를 모두 입력해주세요.")
            return
            
        self.classifier.tag_classifier.add_tag(title, tag)
        self._load_tags()
        
        self.title_edit.clear()
        self.tag_edit.clear()
        
    def _remove_tag(self):
        """태그 제거"""
        current_item = self.tag_list.currentItem()
        if not current_item:
            return
            
        title, tags = current_item.data(Qt.ItemDataRole.UserRole)
        
        if len(tags) == 1:
            # 마지막 태그 제거
            self.classifier.tag_classifier.remove_tag(title, tags[0])
        else:
            # 태그 선택 다이얼로그 표시
            from PyQt6.QtWidgets import QInputDialog
            tag, ok = QInputDialog.getItem(self, "태그 선택", 
                                         f"'{title}'에서 제거할 태그를 선택하세요:", 
                                         tags, 0, False)
            if ok and tag:
                self.classifier.tag_classifier.remove_tag(title, tag)
                
        self._load_tags()
        
    def _add_rule(self):
        """규칙 추가"""
        name = self.rule_name_edit.text().strip()
        pattern = self.rule_pattern_edit.text().strip()
        target = self.rule_target_edit.text().strip()
        priority = self.rule_priority_spin.value()
        enabled = self.rule_enabled_check.isChecked()
        description = self.rule_description_edit.toPlainText().strip()
        
        if not name or not pattern or not target:
            QMessageBox.warning(self, "입력 오류", "이름, 패턴, 대상 폴더를 모두 입력해주세요.")
            return
            
        rule = ClassificationRule(
            name=name,
            pattern=pattern,
            target_folder=target,
            priority=priority,
            enabled=enabled,
            description=description
        )
        
        self.classifier.rule_classifier.add_rule(rule)
        self._load_rules()
        self._clear_rule_edits()
        
    def _remove_rule(self):
        """규칙 제거"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            return
            
        rule_name = self.rule_table.item(current_row, 0).text()
        self.classifier.rule_classifier.remove_rule(rule_name)
        self._load_rules()
        
    def _edit_rule(self):
        """규칙 편집"""
        current_row = self.rule_table.currentRow()
        if current_row < 0:
            return
            
        # 현재 규칙 정보를 편집 필드에 로드
        rule_name = self.rule_table.item(current_row, 0).text()
        rule = next((r for r in self.classifier.rule_classifier.rules if r.name == rule_name), None)
        
        if rule:
            self.rule_name_edit.setText(rule.name)
            self.rule_pattern_edit.setText(rule.pattern)
            self.rule_target_edit.setText(rule.target_folder)
            self.rule_priority_spin.setValue(rule.priority)
            self.rule_enabled_check.setChecked(rule.enabled)
            self.rule_description_edit.setPlainText(rule.description)
            
    def _clear_rule_edits(self):
        """규칙 편집 필드 초기화"""
        self.rule_name_edit.clear()
        self.rule_pattern_edit.clear()
        self.rule_target_edit.clear()
        self.rule_priority_spin.setValue(1)
        self.rule_enabled_check.setChecked(True)
        self.rule_description_edit.clear()
        
    def _on_rule_selection_changed(self):
        """규칙 선택 변경"""
        current_row = self.rule_table.currentRow()
        if current_row >= 0:
            self._edit_rule()
            
    def _on_tag_selection_changed(self):
        """태그 선택 변경"""
        current_item = self.tag_list.currentItem()
        if current_item:
            title, tags = current_item.data(Qt.ItemDataRole.UserRole)
            self.title_edit.setText(title)
            if tags:
                self.tag_edit.setText(tags[0])
                
    def _test_classification(self):
        """분류 테스트"""
        filename = self.test_filename_edit.text().strip()
        if not filename:
            QMessageBox.warning(self, "입력 오류", "테스트할 파일명을 입력해주세요.")
            return
            
        try:
            from src.utils.file_cleaner import FileCleaner
            clean_result = FileCleaner.clean_filename_static(Path(filename))
            
            result = self.classifier.classify(clean_result)
            
            test_result = f"""
분류 테스트 결과:
파일명: {filename}
정제된 제목: {clean_result.title}
제안 폴더: {result.suggested_folder}
분류 전략: {result.strategy.value}
신뢰도: {result.confidence:.2f}
이유: {result.reason}

메타데이터:
{json.dumps(result.metadata, indent=2, ensure_ascii=False)}
"""
            
            self.test_result_text.setPlainText(test_result)
            
        except Exception as e:
            self.test_result_text.setPlainText(f"테스트 실패: {str(e)}")
            
    def _apply_settings(self):
        """설정 적용"""
        try:
            # 전략 우선순위 업데이트
            strategies = []
            for i in range(self.strategy_list.count()):
                item = self.strategy_list.item(i)
                strategy = item.data(Qt.ItemDataRole.UserRole)
                strategies.append(strategy)
            
            self.classifier.strategy_priority = strategies
            
            # 설정 저장
            self._save_settings()
            
            QMessageBox.information(self, "성공", "설정이 적용되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 적용 중 오류가 발생했습니다: {str(e)}")
            
    def _save_settings(self):
        """설정 저장"""
        try:
            # 분류기 설정 저장
            self.classifier.rule_classifier.save_rules()
            self.classifier.tag_classifier.save_tags()
            
            # 전략 우선순위 저장
            strategies = []
            for i in range(self.strategy_list.count()):
                item = self.strategy_list.item(i)
                strategy = item.data(Qt.ItemDataRole.UserRole)
                strategies.append(strategy.value)
            
            if self.config_manager:
                self.config_manager.set("classification.strategy_priority", strategies)
                self.config_manager.set("classification.cache_enabled", self.cache_enabled_check.isChecked())
                self.config_manager.set("classification.parallel_processing", self.parallel_processing_check.isChecked())
                self.config_manager.set("classification.max_workers", self.max_workers_spin.value())
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 중 오류가 발생했습니다: {str(e)}")
            
    def _export_config(self):
        """설정 내보내기"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "설정 내보내기", "", "JSON 파일 (*.json)"
            )
            
            if file_path:
                self.classifier.export_config(Path(file_path))
                QMessageBox.information(self, "성공", "설정이 내보내기되었습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 내보내기 중 오류가 발생했습니다: {str(e)}")
            
    def _import_config(self):
        """설정 가져오기"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "설정 가져오기", "", "JSON 파일 (*.json)"
            )
            
            if file_path:
                self.classifier.import_config(Path(file_path))
                self._load_settings()
                QMessageBox.information(self, "성공", "설정이 가져와졌습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 가져오기 중 오류가 발생했습니다: {str(e)}")
            
    def _backup_settings(self):
        """설정 백업"""
        try:
            backup_dir = Path.home() / "AnimeSorter" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"classification_backup_{timestamp}.json"
            
            self.classifier.export_config(backup_file)
            QMessageBox.information(self, "성공", f"설정이 백업되었습니다:\n{backup_file}")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 백업 중 오류가 발생했습니다: {str(e)}")
            
    def _restore_settings(self):
        """설정 복원"""
        try:
            backup_dir = Path.home() / "AnimeSorter" / "backups"
            if not backup_dir.exists():
                QMessageBox.warning(self, "백업 없음", "백업 디렉토리가 존재하지 않습니다.")
                return
                
            file_path, _ = QFileDialog.getOpenFileName(
                self, "백업에서 복원", str(backup_dir), "JSON 파일 (*.json)"
            )
            
            if file_path:
                self.classifier.import_config(Path(file_path))
                self._load_settings()
                QMessageBox.information(self, "성공", "설정이 복원되었습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 복원 중 오류가 발생했습니다: {str(e)}")
            
    def _reset_to_defaults(self):
        """기본값으로 초기화"""
        reply = QMessageBox.question(
            self, "초기화 확인",
            "모든 분류 설정을 기본값으로 초기화하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 새로운 분류기로 교체
                self.classifier = AdvancedClassifier()
                self._load_settings()
                QMessageBox.information(self, "성공", "설정이 기본값으로 초기화되었습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"초기화 중 오류가 발생했습니다: {str(e)}") 