"""
결과 뷰 컴포넌트 - Phase 3 UI/UX 리팩토링
5개 탭(전체, 미매칭, 충돌, 중복, 완료)을 가진 QTabWidget 기반의 결과 표시 영역을 관리합니다.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QSizePolicy,
                             QSplitter, QTableView, QTabWidget, QVBoxLayout,
                             QWidget)

# Phase 6: 셀 표현 Delegate 추가
from src.gui.components.cell_delegates import (ProgressCellDelegate,
                                               StatusCellDelegate,
                                               TextPreviewCellDelegate)


class ResultsView(QTabWidget):
    """결과 표시 뷰 (5개 탭 구조)"""

    # 시그널 정의
    group_selected = pyqtSignal(dict)  # 그룹 정보
    group_double_clicked = pyqtSignal(dict)  # 그룹 더블클릭

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

        # 탭별 필터 관리자 초기화
        self.filter_manager = None

        # 데이터 동기화를 위한 변수들
        self._current_group_selection = None
        self._cross_tab_sync_enabled = True
        self._detail_model = None

    def init_ui(self):
        """UI 초기화"""
        # 결과 헤더
        self.create_results_header()

        # 5개 탭 생성
        self.create_tabs()

        # 크기 정책 설정
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 기본 활성 탭을 '미매칭'으로 설정
        self.setCurrentIndex(1)  # 미매칭 탭 (인덱스 1)

        # 탭 변경 시그널 연결
        self.currentChanged.connect(self.on_tab_changed)

        # Phase 6: Delegate 설정 (테이블들이 생성된 후에 실행)
        self.setup_delegates()

    def setup_delegates(self):
        """Phase 6: 각 테이블에 적절한 Delegate 설정"""
        try:
            # 모든 탭의 테이블에 Delegate 적용
            self._apply_delegates_to_table(self.all_group_table, "group")
            self._apply_delegates_to_table(self.all_detail_table, "detail")

            self._apply_delegates_to_table(self.unmatched_group_table, "group")
            self._apply_delegates_to_table(self.unmatched_detail_table, "detail")

            self._apply_delegates_to_table(self.conflict_group_table, "group")
            self._apply_delegates_to_table(self.conflict_detail_table, "detail")

            self._apply_delegates_to_table(self.duplicate_group_table, "group")
            self._apply_delegates_to_table(self.duplicate_detail_table, "detail")

            self._apply_delegates_to_table(self.completed_group_table, "group")
            self._apply_delegates_to_table(self.completed_detail_table, "detail")

            print("✅ 셀 표현 Delegate 설정 완료")

        except Exception as e:
            print(f"❌ Delegate 설정 실패: {e}")

    def _apply_delegates_to_table(self, table: QTableView, table_type: str):
        """테이블에 Delegate 적용"""
        if not table:
            return

        # 컬럼별 Delegate 설정
        if table_type == "group":
            # 그룹 테이블: [제목, 최종이동경로, 시즌, 에피소드수, 최고해상도, 상태]
            table.setItemDelegateForColumn(
                0, TextPreviewCellDelegate(table)
            )  # 제목 (툴팁으로 포스터 표시)
            table.setItemDelegateForColumn(1, TextPreviewCellDelegate(table))  # 최종이동경로
            table.setItemDelegateForColumn(2, TextPreviewCellDelegate(table))  # 시즌
            table.setItemDelegateForColumn(3, ProgressCellDelegate(table))  # 에피소드수
            table.setItemDelegateForColumn(4, TextPreviewCellDelegate(table))  # 최고해상도
            table.setItemDelegateForColumn(5, StatusCellDelegate(table))  # 상태

        elif table_type == "detail":
            # 상세 테이블: [파일명, 시즌, 에피소드, 해상도, 코덱, 상태]
            table.setItemDelegateForColumn(
                0, TextPreviewCellDelegate(table)
            )  # 파일명 (툴팁으로 포스터 표시)
            table.setItemDelegateForColumn(1, TextPreviewCellDelegate(table))  # 시즌
            table.setItemDelegateForColumn(2, ProgressCellDelegate(table))  # 에피소드
            table.setItemDelegateForColumn(3, TextPreviewCellDelegate(table))  # 해상도
            table.setItemDelegateForColumn(4, TextPreviewCellDelegate(table))  # 코덱
            table.setItemDelegateForColumn(5, StatusCellDelegate(table))  # 상태

    def on_tab_changed(self, index):
        """탭 변경 시 호출"""
        if self.filter_manager:
            # 탭 변경 시 필터 통계 업데이트
            stats = self.filter_manager.get_filter_stats()
            tab_name = self.tabText(index)
            print(f"📊 {tab_name} 탭으로 변경됨 - 필터 통계: {stats}")

    def setup_filter_manager(self):
        """필터 관리자 설정"""
        from src.gui.components.status_filter_proxy import TabFilterManager

        self.filter_manager = TabFilterManager(self)

    def create_tabs(self):
        """5개 탭 생성"""
        # 전체 탭
        self.all_tab = self.create_tab_content("📋 전체")
        self.addTab(self.all_tab, "📋 전체")

        # 미매칭 탭 (기본 활성)
        self.unmatched_tab = self.create_tab_content("⚠️ 미매칭")
        self.addTab(self.unmatched_tab, "⚠️ 미매칭")

        # 충돌 탭
        self.conflict_tab = self.create_tab_content("💥 충돌")
        self.addTab(self.conflict_tab, "💥 충돌")

        # 중복 탭
        self.duplicate_tab = self.create_tab_content("🔄 중복")
        self.addTab(self.duplicate_tab, "🔄 중복")

        # 완료 탭
        self.completed_tab = self.create_tab_content("✅ 완료")
        self.addTab(self.completed_tab, "✅ 완료")

    def create_tab_content(self, title):
        """탭 내용 생성 (마스터-디테일 스플리터 구조)"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 탭 제목 라벨
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 기본 스플리터로 분할 (고급 스플리터 모듈이 없음)
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # 상단: 그룹 리스트
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(5)

        group_label = QLabel("📋 애니메이션 그룹")
        group_font = QFont()
        group_font.setPointSize(11)
        group_font.setBold(True)
        group_label.setFont(group_font)
        group_layout.addWidget(group_label)

        # 그룹 테이블 생성
        group_table = QTableView()
        group_table.verticalHeader().setVisible(False)
        group_table.setSelectionBehavior(QTableView.SelectRows)
        group_table.setAlternatingRowColors(True)
        group_table.setWordWrap(True)
        group_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 툴팁 활성화
        group_table.setMouseTracking(True)  # 마우스 추적 활성화
        group_table.setToolTip(
            "애니메이션 그룹 목록 - 제목에 마우스를 올리면 포스터를 볼 수 있습니다"
        )

        # Phase 9.1: 성능 최적화 설정
        # setUniformRowHeights: PyQt5 버전 호환성 확인
        if hasattr(group_table, "setUniformRowHeights"):
            group_table.setUniformRowHeights(True)  # 대량 행 렌더링 최적화
        group_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)  # 부드러운 스크롤
        group_table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        group_table.setShowGrid(False)  # 그리드 표시 비활성화로 성능 향상

        group_layout.addWidget(group_table)

        # 하단: 상세 파일 목록
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(5)

        detail_label = QLabel("📁 선택된 그룹의 파일들")
        detail_font = QFont()
        detail_font.setPointSize(11)
        detail_font.setBold(True)
        detail_label.setFont(detail_font)
        detail_layout.addWidget(detail_label)

        # 상세 테이블 생성
        detail_table = QTableView()
        detail_table.verticalHeader().setVisible(False)
        detail_table.setSelectionBehavior(QTableView.SelectRows)
        detail_table.setAlternatingRowColors(True)
        detail_table.setWordWrap(True)
        detail_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 툴팁 활성화
        detail_table.setMouseTracking(True)  # 마우스 추적 활성화
        detail_table.setToolTip("파일 상세 목록 - 파일명에 마우스를 올리면 포스터를 볼 수 있습니다")

        # Phase 9.1: 성능 최적화 설정
        # setUniformRowHeights: PyQt5 버전 호환성 확인
        if hasattr(detail_table, "setUniformRowHeights"):
            detail_table.setUniformRowHeights(True)  # 대량 행 렌더링 최적화
        detail_table.setHorizontalScrollMode(QTableView.ScrollPerPixel)  # 부드러운 스크롤
        detail_table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        detail_table.setShowGrid(False)  # 그리드 표시 비활성화로 성능 향상

        detail_layout.addWidget(detail_table)

        # 스플리터에 추가
        splitter.addWidget(group_widget)
        splitter.addWidget(detail_widget)

        # 고급 스플리터 설정
        # 스플리터 크기 설정
        splitter.setSizes([400, 300])  # 기본 크기 설정

        layout.addWidget(splitter)

        # 탭별 테이블 참조 저장 및 시그널 연결
        if title == "📋 전체":
            self.all_group_table = group_table
            self.all_detail_table = detail_table
            self.all_splitter = splitter
        elif title == "⚠️ 미매칭":
            self.unmatched_group_table = group_table
            self.unmatched_detail_table = detail_table
            self.unmatched_splitter = splitter
        elif title == "💥 충돌":
            self.conflict_group_table = group_table
            self.conflict_detail_table = detail_table
            self.conflict_splitter = splitter
        elif title == "🔄 중복":
            self.duplicate_group_table = group_table
            self.duplicate_detail_table = detail_table
            self.duplicate_splitter = splitter
        elif title == "✅ 완료":
            self.completed_group_table = group_table
            self.completed_detail_table = detail_table
            self.completed_splitter = splitter

        return tab_widget

    def setup_connections(self):
        """시그널 연결 설정"""
        print("🔧 setup_connections 호출됨")

        # 모든 탭의 그룹 테이블에 시그널 연결
        tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]

        for i, table in enumerate(tables):
            if table:
                print(f"🔧 테이블 {i} 연결 중: {type(table).__name__}")
                if table.selectionModel():
                    table.selectionModel().selectionChanged.connect(self.on_group_selection_changed)
                    table.doubleClicked.connect(self.on_group_double_clicked)
                    print(f"✅ 테이블 {i} 시그널 연결 완료")
                else:
                    print(f"⚠️ 테이블 {i}의 selectionModel이 None")
            else:
                print(f"⚠️ 테이블 {i}가 None")

        print("🔧 setup_connections 완료")

    def create_results_header(self):
        """결과 헤더 생성"""
        header_widget = QWidget()
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("📋 스캔 결과")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)

        layout.addWidget(title_label)
        layout.addStretch(1)

        # 헤더를 탭 위젯 위에 추가
        self.setCornerWidget(header_widget, Qt.TopLeftCorner)

    def set_group_model(self, model):
        """그룹 리스트 모델 설정 (모든 탭에 동일한 모델 적용)"""
        # 모든 탭의 그룹 테이블에 모델 설정
        tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]

        for table in tables:
            table.setModel(model)
            self.adjust_group_table_columns(table, model)

        # 필터 관리자 설정 및 모델 적용
        if not self.filter_manager:
            self.setup_filter_manager()

        if self.filter_manager:
            self.filter_manager.update_source_model(model)

        # 모델 설정 후 시그널 연결
        self.setup_connections()

    def set_detail_model(self, model):
        """상세 파일 목록 모델 설정 (모든 탭에 동일한 모델 적용)"""
        self._detail_model = model

        # 모든 탭의 상세 테이블에 모델 설정
        tables = [
            self.all_detail_table,
            self.unmatched_detail_table,
            self.conflict_detail_table,
            self.duplicate_detail_table,
            self.completed_detail_table,
        ]

        for table in tables:
            table.setModel(model)
            self.adjust_detail_table_columns(table, model)

    def adjust_group_table_columns(self, table, model):
        """그룹 테이블 컬럼 크기 조정"""
        header = table.horizontalHeader()

        if hasattr(model, "get_column_widths"):
            column_widths = model.get_column_widths()
            stretch_columns = model.get_stretch_columns()

            for col in range(header.count()):
                if col in stretch_columns:
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    if col in column_widths:
                        header.resizeSection(col, column_widths[col])
        else:
            # 기본 설정 (기존 코드)
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            table.setColumnWidth(0, 120)

            for i in range(1, model.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

            header.setStretchLastSection(True)

        # 일반적인 행 높이로 조정 (포스터 컬럼 제거)
        table.verticalHeader().setDefaultSectionSize(25)

    def adjust_detail_table_columns(self, table, model):
        """상세 테이블 컬럼 크기 조정"""
        header = table.horizontalHeader()

        if hasattr(model, "get_column_widths"):
            column_widths = model.get_column_widths()
            stretch_columns = model.get_stretch_columns()

            for col in range(header.count()):
                if col in stretch_columns:
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    if col in column_widths:
                        header.resizeSection(col, column_widths[col])
        else:
            # 기본 설정 (기존 코드)
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            table.setColumnWidth(0, 120)

            for i in range(1, model.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

            header.setStretchLastSection(True)

        # 일반적인 행 높이로 조정 (포스터 컬럼 제거)
        table.verticalHeader().setDefaultSectionSize(25)

    def sync_selection_across_tabs(self, group_id):
        """모든 탭에서 동일한 그룹 선택 동기화 (상세 뷰 업데이트 없이)"""
        if not self._cross_tab_sync_enabled:
            return

        # 현재 선택된 그룹 ID 저장
        self._current_group_selection = group_id

        # 모든 탭의 그룹 테이블에서 해당 그룹 선택 (상세 뷰 업데이트 없이)
        all_tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]

        for table in all_tables:
            if table and table.model():
                # 기존 선택 해제
                table.clearSelection()

                # 그룹 ID에 해당하는 행 찾기 및 선택 (상세 뷰 업데이트 없이)
                self._select_group_in_table(table, group_id)

    def _select_group_in_table(self, table, group_id):
        """테이블에서 특정 그룹 ID를 가진 행 선택"""
        model = table.model()
        if not model:
            return

        # 프록시 모델인 경우 소스 모델에서 검색
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model

        if hasattr(source_model, "find_group_by_id"):
            # 그룹 ID로 행 인덱스 찾기
            row_index = source_model.find_group_by_id(group_id)
            if row_index >= 0:
                # 프록시 모델인 경우 매핑된 인덱스로 변환
                if hasattr(model, "mapFromSource"):
                    proxy_index = model.mapFromSource(source_model.index(row_index, 0))
                    if proxy_index.isValid():
                        table.selectRow(proxy_index.row())
                else:
                    # 직접 모델인 경우
                    table.selectRow(row_index)

    def enable_cross_tab_sync(self, enabled=True):
        """탭 간 동기화 활성화/비활성화"""
        self._cross_tab_sync_enabled = enabled

    def get_current_selection(self):
        """현재 선택된 그룹 정보 반환"""
        return self._current_group_selection

    def refresh_all_tabs(self):
        """모든 탭 새로고침"""
        # 필터 관리자가 있는 경우 필터 새로고침
        if self.filter_manager:
            self.filter_manager.refresh_filters()

        # 모든 탭의 테이블 새로고침
        all_tables = [
            self.all_group_table,
            self.unmatched_group_table,
            self.conflict_group_table,
            self.duplicate_group_table,
            self.completed_group_table,
        ]

        for table in all_tables:
            if table and table.model():
                table.viewport().update()

    def get_tab_statistics(self):
        """각 탭별 통계 정보 반환"""
        stats = {}

        if self.filter_manager:
            filter_stats = self.filter_manager.get_filter_stats()
            for tab_name, data in filter_stats.items():
                stats[tab_name] = {
                    "filtered_count": data["filtered_count"],
                    "source_count": data["source_count"],
                    "percentage": (
                        (data["filtered_count"] / data["source_count"] * 100)
                        if data["source_count"] > 0
                        else 0
                    ),
                }

        return stats

    def set_tab_visibility(self, tab_name, visible):
        """특정 탭의 가시성 설정"""
        tab_index = -1

        if tab_name == "all":
            tab_index = 0
        elif tab_name == "unmatched":
            tab_index = 1
        elif tab_name == "conflict":
            tab_index = 2
        elif tab_name == "duplicate":
            tab_index = 3
        elif tab_name == "completed":
            tab_index = 4

        if tab_index >= 0:
            self.setTabVisible(tab_index, visible)

    def get_visible_tabs(self):
        """현재 보이는 탭 목록 반환"""
        visible_tabs = []
        for i in range(self.count()):
            if self.isTabVisible(i):
                visible_tabs.append(
                    {
                        "index": i,
                        "name": self.tabText(i),
                        "tooltip": self.tabToolTip(i) if self.tabToolTip(i) else "",
                    }
                )
        return visible_tabs

    def on_group_selection_changed(self, selected, deselected):
        """그룹 선택 변경 시 호출"""
        print(
            f"🔍 그룹 선택 변경 감지: selected={len(selected.indexes())}, deselected={len(deselected.indexes())}"
        )

        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            print(f"🔍 선택된 행: {row}")

            # 현재 활성 탭의 그룹 테이블에서 모델 가져오기
            current_widget = self.currentWidget()
            if current_widget:
                tables = current_widget.findChildren(QTableView)
                print(
                    f"🔍 찾은 테이블들: {[type(t.model()).__name__ if t.model() else 'None' for t in tables]}"
                )

                if tables and len(tables) > 0:
                    # 그룹 테이블 찾기 (GroupedListModel을 사용하는 테이블)
                    group_table = None
                    for table in tables:
                        model = table.model()
                        if model:
                            # 프록시 모델인 경우 소스 모델 확인
                            if hasattr(model, "sourceModel") and model.sourceModel():
                                source_model = model.sourceModel()
                                if hasattr(source_model, "get_group_at_row"):
                                    group_table = table
                                    break
                            # 직접 모델인 경우
                            elif hasattr(model, "get_group_at_row"):
                                group_table = table
                                break

                    if group_table:
                        model = group_table.model()
                        print(f"🔍 그룹 테이블 모델: {type(model).__name__}")

                        if model:
                            # 프록시 모델인 경우 소스 모델에서 그룹 정보 가져오기
                            if hasattr(model, "sourceModel") and model.sourceModel():
                                source_model = model.sourceModel()
                                print(f"🔍 소스 모델: {type(source_model).__name__}")
                                if hasattr(source_model, "get_group_at_row"):
                                    group = source_model.get_group_at_row(row)
                                    if group:
                                        print(
                                            f"✅ 그룹 정보 가져옴: {group.get('title', 'Unknown')}"
                                        )
                                        # 상세 정보만 업데이트 (MainWindow의 on_group_selected는 호출하지 않음)
                                        self.update_detail_view(group)
                                        # 다른 탭과 선택 동기화 (상세 뷰 업데이트 없이)
                                        self.sync_selection_across_tabs(group.get("key", ""))
                                    else:
                                        print("⚠️ 그룹 정보가 None")
                                else:
                                    print("⚠️ 소스 모델에 get_group_at_row 메서드 없음")
                            else:
                                # 직접 모델인 경우
                                if hasattr(model, "get_group_at_row"):
                                    group = model.get_group_at_row(row)
                                    if group:
                                        print(
                                            f"✅ 그룹 정보 가져옴: {group.get('title', 'Unknown')}"
                                        )
                                        # 상세 정보만 업데이트 (MainWindow의 on_group_selected는 호출하지 않음)
                                        self.update_detail_view(group)
                                        # 다른 탭과 선택 동기화 (상세 뷰 업데이트 없이)
                                        self.sync_selection_across_tabs(group.get("key", ""))
                                    else:
                                        print("⚠️ 그룹 정보가 None")
                                else:
                                    print("⚠️ 모델에 get_group_at_row 메서드 없음")
                        else:
                            print("⚠️ 그룹 테이블 모델이 None")
                    else:
                        print(
                            "⚠️ 그룹 테이블을 찾을 수 없음 (get_group_at_row 메서드가 있는 모델이 없음)"
                        )
                else:
                    print("⚠️ 테이블을 찾을 수 없음")
            else:
                print("⚠️ 현재 위젯이 None")
        else:
            print("⚠️ 선택된 인덱스가 없음")

    def on_group_double_clicked(self, index):
        """그룹 더블클릭 시 호출"""
        # 현재 활성 탭의 그룹 테이블에서 모델 가져오기 (첫 번째 테이블이 그룹 테이블)
        current_widget = self.currentWidget()
        if current_widget:
            tables = current_widget.findChildren(QTableView)
            if tables and len(tables) > 0:
                group_table = tables[0]  # 첫 번째 테이블이 그룹 테이블
                model = group_table.model()
                if model and hasattr(model, "get_group_at_row"):
                    group = model.get_group_at_row(index.row())
                    if group:
                        self.group_double_clicked.emit(group)

    def get_selected_group_row(self):
        """현재 활성 탭의 그룹 테이블에서 선택된 행 반환"""
        current_widget = self.currentWidget()
        if current_widget:
            group_table = current_widget.findChild(QTableView)
            if group_table:
                selection = group_table.selectionModel()
                if not selection.hasSelection():
                    return -1

                indexes = selection.selectedRows()
                if indexes:
                    return indexes[0].row()
        return -1

    def get_current_tab_name(self):
        """현재 활성 탭 이름 반환"""
        return self.tabText(self.currentIndex())

    def set_current_tab_by_status(self, status):
        """상태에 따라 해당하는 탭으로 이동"""
        status_to_tab = {
            "tmdb_matched": 4,  # 완료 탭
            "complete": 4,  # 완료 탭
            "error": 2,  # 충돌 탭
            "needs_review": 1,  # 미매칭 탭
            "pending": 1,  # 미매칭 탭
        }

        tab_index = status_to_tab.get(status, 0)  # 기본값: 전체 탭
        self.setCurrentIndex(tab_index)

    def update_detail_view(self, group):
        """상세 뷰 업데이트"""
        print(
            f"🔍 update_detail_view 호출됨: group={group.get('title', 'Unknown') if group else 'None'}"
        )

        if not group:
            print("⚠️ 그룹이 None이므로 업데이트 중단")
            return

        # 현재 활성 탭의 상세 테이블 찾기
        current_widget = self.currentWidget()
        if current_widget:
            # 상세 테이블을 더 정확하게 찾기
            detail_table = self._find_detail_table(current_widget)

            if detail_table:
                print(f"🔍 상세 테이블 찾음: {type(detail_table).__name__}")

                # 그룹에 해당하는 파일 목록 모델 설정
                if self._detail_model:
                    print(f"🔍 상세 모델 설정: {type(self._detail_model).__name__}")
                    detail_table.setModel(self._detail_model)

                    # 그룹의 파일들을 상세 모델에 설정
                    if "items" in group:
                        items = group["items"]
                        print(f"🔍 그룹의 파일 수: {len(items)}")
                        self._detail_model.set_items(items)
                        print(f"✅ 상세 뷰 업데이트 완료: {len(items)}개 파일")
                    else:
                        print(f"⚠️ 그룹에 'items' 키가 없음: {list(group.keys())}")

                    # 상세 테이블 컬럼 조정
                    self.adjust_detail_table_columns(detail_table, self._detail_model)
                else:
                    print("⚠️ 상세 모델이 None")
            else:
                print("⚠️ 상세 테이블을 찾을 수 없음")
        else:
            print("⚠️ 현재 위젯이 None")

    def _find_detail_table(self, widget):
        """위젯에서 상세 테이블을 찾는 헬퍼 메서드"""
        # 모든 QTableView 찾기
        tables = widget.findChildren(QTableView)
        print(f"🔍 찾은 테이블 수: {len(tables)}")

        if len(tables) < 2:
            return None

        # 상세 테이블을 찾기 위해 부모 위젯의 라벨을 확인
        for table in tables:
            parent = table.parent()
            if parent:
                # 부모 위젯의 자식들을 확인하여 라벨 찾기
                for child in parent.children():
                    if isinstance(child, QLabel):
                        label_text = child.text()
                        if "선택된 그룹의 파일들" in label_text:
                            print(f"🔍 상세 테이블 발견: 라벨='{label_text}'")
                            return table

        # 라벨로 찾지 못한 경우, 두 번째 테이블을 상세 테이블로 가정
        print("🔍 라벨로 상세 테이블을 찾지 못함, 두 번째 테이블 사용")
        return tables[1] if len(tables) > 1 else None

    def get_current_splitter(self):
        """현재 활성 탭의 스플리터 반환"""
        current_index = self.currentIndex()
        if current_index == 0:  # 전체 탭
            return getattr(self, "all_splitter", None)
        if current_index == 1:  # 미매칭 탭
            return getattr(self, "unmatched_splitter", None)
        if current_index == 2:  # 충돌 탭
            return getattr(self, "conflict_splitter", None)
        if current_index == 3:  # 중복 탭
            return getattr(self, "duplicate_splitter", None)
        if current_index == 4:  # 완료 탭
            return getattr(self, "completed_splitter", None)
        return None

    def set_splitter_ratio(self, ratio):
        """현재 활성 탭의 스플리터 비율 설정"""
        splitter = self.get_current_splitter()
        if splitter:
            total_height = splitter.height()
            group_height = int(total_height * ratio)
            detail_height = total_height - group_height
            splitter.setSizes([group_height, detail_height])

    def get_splitter_ratio(self):
        """현재 활성 탭의 스플리터 비율 반환"""
        splitter = self.get_current_splitter()
        if splitter:
            sizes = splitter.sizes()
            if sizes[1] > 0:  # 상세 테이블 높이가 0보다 큰 경우
                return sizes[0] / (sizes[0] + sizes[1])
        return 0.6  # 기본값: 그룹 테이블 60%

    def get_file_model_for_group(self, group_index):
        """선택된 그룹의 파일 모델을 반환"""
        try:
            # 그룹 인덱스에서 그룹 데이터 추출
            if not group_index.isValid():
                print("❌ 유효하지 않은 그룹 인덱스")
                return None

            # 그룹 모델 타입 확인
            group_model = group_index.model()
            if not group_model:
                print("❌ 그룹 모델이 None")
                return None

            print(f"🔍 그룹 모델 타입: {type(group_model).__name__}")

            # GroupedListModel인 경우
            if hasattr(group_model, "get_group_at_row"):
                print("✅ GroupedListModel 감지됨")
                group_info = group_model.get_group_at_row(group_index.row())
                if not group_info:
                    print(f"❌ 그룹 정보를 찾을 수 없음: row={group_index.row()}")
                    return None

                print(f"✅ 그룹 정보 찾음: {group_info.get('title', 'Unknown')}")

                # 그룹에 포함된 파일들 가져오기
                group_items = group_info.get("items", [])
                if not group_items:
                    print("❌ 그룹에 파일이 없음")
                    return None

                print(f"✅ 그룹 내 파일 수: {len(group_items)}")

                # 새로운 파일 모델 생성
                from src.gui.table_models import DetailFileModel

                file_model = DetailFileModel()
                file_model.set_items(group_items)

                print(f"✅ 파일 모델 생성 완료: {len(group_items)}개 파일")
                return file_model

            # 다른 타입의 모델인 경우 - MainWindow의 grouped_model 사용
            print(f"❌ get_group_at_row 메서드가 없는 모델: {type(group_model).__name__}")
            print("🔍 MainWindow의 grouped_model 사용 시도")

            # MainWindow에서 grouped_model 가져오기
            from PyQt5.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                main_windows = [
                    widget for widget in app.topLevelWidgets() if hasattr(widget, "grouped_model")
                ]
                if main_windows:
                    main_window = main_windows[0]
                    if hasattr(main_window, "grouped_model") and main_window.grouped_model:
                        grouped_model = main_window.grouped_model
                        print(f"✅ MainWindow의 grouped_model 찾음: {type(grouped_model).__name__}")

                        if hasattr(grouped_model, "get_group_at_row"):
                            group_info = grouped_model.get_group_at_row(group_index.row())
                            if group_info:
                                group_items = group_info.get("items", [])
                                if group_items:
                                    from src.gui.table_models import \
                                        DetailFileModel

                                    file_model = DetailFileModel()
                                    file_model.set_items(group_items)
                                    print(
                                        f"✅ MainWindow grouped_model로 파일 모델 생성: {len(group_items)}개 파일"
                                    )
                                    return file_model

            print("❌ MainWindow의 grouped_model에서도 그룹 정보를 찾을 수 없음")
            return None

        except Exception as e:
            print(f"❌ get_file_model_for_group 실패: {e}")
            import traceback

            traceback.print_exc()
            return None
