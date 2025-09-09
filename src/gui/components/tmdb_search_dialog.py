"""
TMDB 검색 결과 선택 다이얼로그
그룹화된 애니메이션에 대한 TMDB 검색 결과를 표시하고 사용자가 선택할 수 있는 다이얼로그입니다.
"""

import contextlib

import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.tmdb_client import TMDBAnimeInfo


class TMDBSearchWorker(QThread):
    """TMDB 검색을 백그라운드에서 수행하는 워커 스레드"""

    search_completed = pyqtSignal(list)  # 검색 결과
    search_failed = pyqtSignal(str)  # 오류 메시지

    def __init__(self, tmdb_client, query: str):
        super().__init__()
        self.tmdb_client = tmdb_client
        self.query = query

    def run(self):
        """검색 실행"""
        try:
            results = self.tmdb_client.search_anime(self.query)
            self.search_completed.emit(results)
        except Exception as e:
            self.search_failed.emit(str(e))


class TMDBSearchDialog(QDialog):
    """TMDB 검색 결과 선택 다이얼로그"""

    # 시그널 정의
    anime_selected = pyqtSignal(TMDBAnimeInfo)  # 애니메이션 선택됨
    search_requested = pyqtSignal(str)  # 새로운 검색 요청

    def __init__(
        self,
        group_title: str,
        tmdb_client,
        parent=None,
        file_info: str = None,
        failed_search_query: str = None,
        initial_results: list = None,
    ):
        super().__init__(parent)
        self.group_title = group_title
        self.tmdb_client = tmdb_client
        self.search_results = []
        self.selected_anime = None
        self.file_info = file_info or ""
        self.failed_search_query = failed_search_query or group_title
        self.initial_results = initial_results or []

        self.init_ui()
        self.setup_connections()

        # 초기 검색 결과가 있으면 설정, 없으면 검색 실행
        if self.initial_results:
            self.set_search_results(self.initial_results)
        else:
            self.perform_search(self.failed_search_query)

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(f"TMDB 검색: {self.group_title}")
        self.setMinimumSize(600, 500)
        self.setModal(False)  # 모달을 False로 변경하여 다이얼로그가 숨겨지지 않도록 함
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # 항상 위에 표시

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 그룹 정보
        group_info = self.create_group_info()
        layout.addWidget(group_info)

        # 검색 영역
        search_area = self.create_search_area()
        layout.addWidget(search_area)

        # 검색 결과
        results_area = self.create_results_area()
        layout.addWidget(results_area)

        # 버튼
        buttons = self.create_buttons()
        layout.addWidget(buttons)

    def create_group_info(self):
        """그룹 정보 영역 생성"""
        group = QGroupBox("📋 검색 대상")
        layout = QVBoxLayout(group)

        # 그룹 제목
        self.lblGroupTitle = QLabel(f"제목: {self.group_title}")
        self.lblGroupTitle.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lblGroupTitle)

        # 파일 정보 (파일 풀 네임)
        if self.file_info:
            self.lblFileInfo = QLabel(f"파일: {self.file_info}")
            self.lblFileInfo.setStyleSheet("color: #666; font-size: 12px;")
            self.lblFileInfo.setWordWrap(True)
            layout.addWidget(self.lblFileInfo)

        return group

    def create_search_area(self):
        """검색 영역 생성"""
        group = QGroupBox("🔍 TMDB 검색")
        layout = QHBoxLayout(group)

        self.txtSearch = QLineEdit()
        self.txtSearch.setPlaceholderText("검색어를 입력하세요...")
        # 실패한 검색어를 입력란에 표시
        self.txtSearch.setText(self.failed_search_query)
        self.txtSearch.returnPressed.connect(self.on_search_clicked)

        self.btnSearch = QPushButton("🔍 검색")
        self.btnSearch.clicked.connect(self.on_search_clicked)

        layout.addWidget(self.txtSearch)
        layout.addWidget(self.btnSearch)

        return group

    def create_results_area(self):
        """검색 결과 영역 생성"""
        group = QGroupBox("📊 검색 결과")
        layout = QVBoxLayout(group)

        # 검색 상태
        self.lblSearchStatus = QLabel("검색 중...")
        self.lblSearchStatus.setStyleSheet("color: #3498db; font-style: italic;")
        layout.addWidget(self.lblSearchStatus)

        # 검색 결과 리스트
        self.resultsList = QListWidget()
        self.resultsList.setAlternatingRowColors(True)
        self.resultsList.setSpacing(6)
        try:
            from PyQt5.QtWidgets import QAbstractItemView, QListView

            self.resultsList.setResizeMode(QListView.Adjust)
            self.resultsList.setSelectionMode(QAbstractItemView.SingleSelection)
        except Exception:
            pass
        self.resultsList.itemClicked.connect(self.on_result_selected)
        self.resultsList.itemDoubleClicked.connect(self.on_result_double_clicked)
        layout.addWidget(self.resultsList)

        return group

    def create_buttons(self):
        """버튼 영역 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btnSelect = QPushButton("✅ 선택")
        self.btnSelect.setEnabled(False)
        self.btnSelect.clicked.connect(self.on_select_clicked)

        self.btnSkip = QPushButton("⏭️ 건너뛰기")
        self.btnSkip.clicked.connect(self.reject)

        self.btnRefresh = QPushButton("🔄 새로고침")
        self.btnRefresh.clicked.connect(self.on_refresh_clicked)

        layout.addWidget(self.btnSelect)
        layout.addWidget(self.btnSkip)
        layout.addWidget(self.btnRefresh)
        layout.addStretch(1)

        return widget

    def setup_connections(self):
        """시그널/슬롯 연결"""
        # 이미 위에서 연결됨

    def perform_search(self, query: str):
        """검색 실행"""
        if not query.strip():
            self.lblSearchStatus.setText("검색어를 입력해주세요")
            return

        self.lblSearchStatus.setText("검색 중...")
        self.btnSearch.setEnabled(False)
        self.resultsList.clear()

        # 백그라운드에서 검색 실행
        self.search_worker = TMDBSearchWorker(self.tmdb_client, query)
        self.search_worker.search_completed.connect(self.on_search_completed)
        self.search_worker.search_failed.connect(self.on_search_failed)
        self.search_worker.start()

    def on_search_clicked(self):
        """검색 버튼 클릭"""
        query = self.txtSearch.text().strip()
        if query:
            self.perform_search(query)

    def on_refresh_clicked(self):
        """새로고침 버튼 클릭"""
        query = self.txtSearch.text().strip()
        if query:
            self.perform_search(query)

    def set_search_results(self, results: list[TMDBAnimeInfo]):
        """검색 결과를 미리 설정"""
        self.search_results = results
        self.on_search_completed(results)

    def on_search_completed(self, results: list[TMDBAnimeInfo]):
        """검색 완료"""
        print(f"🔍 검색 완료: {len(results)}개 결과")
        self.btnSearch.setEnabled(True)
        self.search_results = results

        if not results:
            self.lblSearchStatus.setText("검색 결과가 없습니다")
            return

        # 결과 개수에 따른 처리
        if len(results) == 1:
            # 결과가 1개면 자동 선택 (UI 업데이트만)
            self.selected_anime = results[0]
            self.lblSearchStatus.setText("검색결과 1개 - 자동 선택됨")
            self.btnSelect.setEnabled(True)
            self.btnSelect.setText("✅ 자동 선택됨")
            # 자동 선택은 메인 윈도우에서 처리하므로 여기서는 UI만 업데이트
        else:
            self.lblSearchStatus.setText(f"검색결과 {len(results)}개 - 선택해주세요")

        # 결과 목록에 추가
        for i, anime in enumerate(results):
            try:
                print(f"📋 결과 {i + 1}: ID={anime.id}, 제목={anime.name}")

                item = QListWidgetItem()  # Create QListWidgetItem first
                self.resultsList.addItem(item)  # Add it to the list widget
                widget = self.create_result_item_widget(anime)  # Create the custom widget
                self.resultsList.setItemWidget(item, widget)  # Set the custom widget for the item
                # Ensure the row height matches the custom widget
                with contextlib.suppress(Exception):
                    item.setSizeHint(widget.sizeHint())

                print(f"✅ 결과 {i + 1} 추가 완료")
            except Exception as e:
                print(f"❌ 결과 아이템 생성 실패: {e}")
                import traceback

                traceback.print_exc()
                # 간단한 텍스트 아이템으로 대체
                try:
                    simple_item = QListWidgetItem(
                        f"ID: {anime.id} - {getattr(anime, 'name', 'Unknown')}"
                    )
                    self.resultsList.addItem(simple_item)
                    print(f"✅ 간단한 아이템 {i + 1} 추가 완료")
                except Exception as e2:
                    print(f"❌ 간단한 아이템도 실패: {e2}")
                    # 최후의 수단: 기본 텍스트
                    basic_item = QListWidgetItem(f"결과 {i + 1}")
                    self.resultsList.addItem(basic_item)

    def on_search_failed(self, error: str):
        """검색 실패"""
        self.btnSearch.setEnabled(True)
        self.lblSearchStatus.setText(f"검색 실패: {error}")

    def create_result_item_widget(self, anime: TMDBAnimeInfo) -> QWidget:
        """검색 결과 아이템 위젯 생성"""
        print(f"🎨 위젯 생성 시작: ID={anime.id}, 제목={anime.name}")

        # 아이템 위젯 생성
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)

        # 포스터 (100x150 크기로 통일)
        poster_label = QLabel()
        poster_label.setFixedSize(100, 150)  # 일관된 크기로 조정
        poster_label.setStyleSheet("border: 1px solid #ddd; background-color: #f8f9fa;")

        if anime.poster_path:
            try:
                print(f"🖼️ 포스터 로드 시도: {anime.poster_path}")
                # 포스터 이미지 로드 (더 큰 크기로 수정)
                poster_url = (
                    f"https://image.tmdb.org/t/p/w154{anime.poster_path}"  # w92에서 w154로 변경
                )
                response = requests.get(poster_url)
                if response.status_code == 200:
                    pixmap = QPixmap()
                    pixmap.loadFromData(response.content)
                    poster_label.setPixmap(
                        pixmap.scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                    print(f"✅ 포스터 로드 성공: {poster_url}")
                else:
                    print(f"❌ 포스터 HTTP 오류: {response.status_code}")
            except Exception as e:
                print(f"❌ 포스터 로드 실패: {e}")
                poster_label.setText("🎬")
        else:
            print("⚠️ 포스터 경로 없음")
            poster_label.setText("🎬")

        layout.addWidget(poster_label)

        # 정보 영역
        info_layout = QVBoxLayout()

        # 제목 (name 속성 사용)
        try:
            title_text = getattr(anime, "name", "제목 없음")
            print(f"📺 제목 설정: {title_text}")
            title_label = QLabel(title_text)
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            info_layout.addWidget(title_label)
        except Exception as e:
            print(f"❌ 제목 설정 실패: {e}")
            title_label = QLabel("제목 없음")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            info_layout.addWidget(title_label)

        # 원제목 (original_name 속성 사용)
        try:
            original_name = getattr(anime, "original_name", None)
            if original_name and original_name != getattr(anime, "name", ""):
                print(f"🎬 원제목 설정: {original_name}")
                original_label = QLabel(f"원제목: {original_name}")
                original_label.setStyleSheet("color: #666; font-size: 12px;")
                info_layout.addWidget(original_label)
        except Exception as e:
            print(f"❌ 원제목 설정 실패: {e}")

        # 개요
        try:
            overview = getattr(anime, "overview", None)
            if overview:
                print(f"📝 개요 설정: {overview[:50]}...")
                overview_text = overview[:100] + "..." if len(overview) > 100 else overview
                overview_label = QLabel(overview_text)
                overview_label.setStyleSheet("color: #555; font-size: 11px;")
                overview_label.setWordWrap(True)
                info_layout.addWidget(overview_label)
        except Exception as e:
            print(f"❌ 개요 설정 실패: {e}")

        # 메타데이터 (first_air_date 속성 사용)
        meta_info = []
        try:
            first_air_date = getattr(anime, "first_air_date", None)
            if first_air_date:
                meta_info.append(f"첫 방영일: {first_air_date}")

            vote_average = getattr(anime, "vote_average", None)
            if vote_average:
                meta_info.append(f"평점: {vote_average:.1f}")

            anime_id = getattr(anime, "id", None)
            if anime_id:
                meta_info.append(f"TMDB ID: {anime_id}")

            if meta_info:
                print(f"📊 메타데이터 설정: {meta_info}")
                meta_label = QLabel(" | ".join(meta_info))
                meta_label.setStyleSheet("color: #888; font-size: 10px;")
                info_layout.addWidget(meta_label)
        except Exception as e:
            print(f"❌ 메타데이터 설정 실패: {e}")

        layout.addLayout(info_layout)
        layout.addStretch(1)

        widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        widget.setFixedHeight(100)  # Fixed height for consistent item size

        print(f"✅ 위젯 생성 완료: ID={anime.id}")
        return widget

    def on_result_selected(self, item: QListWidgetItem):
        """결과 아이템 선택"""
        index = self.resultsList.row(item)
        if 0 <= index < len(self.search_results):
            self.selected_anime = self.search_results[index]
            self.btnSelect.setEnabled(True)
            self.btnSelect.setText("✅ 선택됨")

    def on_result_double_clicked(self, item: QListWidgetItem):
        """결과 아이템 더블클릭 시 즉시 확정"""
        self.on_result_selected(item)
        if self.selected_anime:
            self.anime_selected.emit(self.selected_anime)
            self.accept()

    def on_select_clicked(self):
        """선택 버튼 클릭"""
        if self.selected_anime:
            self.anime_selected.emit(self.selected_anime)
            self.accept()
        else:
            QMessageBox.warning(self, "선택 오류", "애니메이션을 선택해주세요")
