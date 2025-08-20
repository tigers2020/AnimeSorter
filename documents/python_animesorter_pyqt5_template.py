#!/usr/bin/env python3
"""
AnimeSorter – PyQt5 UI Prototype (single-file)
- Mirrors the React prototype layout in a desktop app.
- Includes: left actions (scan/pause, drop zone stub, progress), stats, filters;
  right results table with status/metadata/actions; activity/error logs; settings dialog.
- Uses mock data and a simulated scanner (QTimer). Wire your backend where noted.

Requires: PyQt5
    pip install PyQt5

Run:
    python animesorter_pyqt5.py
"""
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QTimer,
    QVariant,
    pyqtSignal,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


# ----------------- Data -----------------
@dataclass
class ParsedItem:
    id: str
    status: str  # 'parsed' | 'needs_review' | 'error'
    sourcePath: str
    detectedTitle: str
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None
    tmdbId: Optional[int] = None
    resolution: Optional[str] = None
    group: Optional[str] = None
    codec: Optional[str] = None
    container: Optional[str] = None
    sizeMB: Optional[int] = None
    message: Optional[str] = None


MOCK_ITEMS: list[ParsedItem] = [
    ParsedItem(
        id="1",
        status="parsed",
        sourcePath="/downloads/[EMBER] Frieren - 01 [1080p][HEVC][AAC].mkv",
        detectedTitle="Frieren: Beyond Journey's End",
        season=1,
        episode=1,
        year=2023,
        tmdbId=209867,
        resolution="1080p",
        group="EMBER",
        codec="HEVC",
        container="MKV",
        sizeMB=981,
    ),
    ParsedItem(
        id="2",
        status="needs_review",
        sourcePath="/downloads/[SomeGroup] Sousou no Frieren - S01E02 2160p.mkv",
        detectedTitle="Frieren: Beyond Journey's End",
        season=1,
        episode=2,
        year=2023,
        resolution="2160p",
        group="SomeGroup",
        codec="H.264",
        container="MKV",
        sizeMB=1900,
        message="Conflicting episode numbering detected (E02 vs Ep 1-2 special)",
    ),
    ParsedItem(
        id="3",
        status="error",
        sourcePath="/downloads/[???] Unknown.Show.12v2.mp4",
        detectedTitle="Unknown",
        codec="H.264",
        container="MP4",
        sizeMB=420,
        message="Failed to link TMDB: title ambiguous; try manual search.",
    ),
]


# ----------------- Table Model -----------------
class ItemsTableModel(QAbstractTableModel):
    headers = ["Status", "Title / Path", "S", "E", "Year", "Resolution", "Size", "TMDB", "Actions"]

    def __init__(self, items: list[ParsedItem]):
        super().__init__()
        self.items = items

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        item = self.items[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return item.status
            elif col == 1:
                text = f"{item.detectedTitle}\n{item.sourcePath}"
                if item.message:
                    text += f"\n⚠ {item.message}"
                return text
            elif col == 2:
                return item.season if item.season is not None else "-"
            elif col == 3:
                return item.episode if item.episode is not None else "-"
            elif col == 4:
                return item.year if item.year is not None else "-"
            elif col == 5:
                return item.resolution or "-"
            elif col == 6:
                if item.sizeMB is None:
                    return "-"
                if item.sizeMB > 1024:
                    return f"{item.sizeMB/1024:.1f} GB"
                return f"{item.sizeMB} MB"
            elif col == 7:
                return str(item.tmdbId) if item.tmdbId else "—"
            elif col == 8:
                return "✔ / ! / ×"  # placeholders for actions column text

        if role == Qt.TextAlignmentRole:
            if col in (2, 3, 4, 5, 6, 7, 8):
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return self.headers[section]
        return section + 1

    # convenience for updates
    def setStatus(self, row: int, status: str):
        if 0 <= row < len(self.items):
            self.items[row].status = status
            self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [Qt.DisplayRole])


# ----------------- Filter Proxy -----------------
class ItemsFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.query = ""
        self.status = "all"

    def setQuery(self, text: str):
        self.query = text.lower()
        self.invalidateFilter()

    def setStatus(self, status: str):
        self.status = status
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        model: ItemsTableModel = self.sourceModel()  # type: ignore
        item = model.items[source_row]
        if self.status != "all" and item.status != self.status:
            return False
        if not self.query:
            return True
        hay = f"{item.sourcePath} {item.detectedTitle}".lower()
        return self.query in hay


# ----------------- Settings Dialog -----------------
class SettingsDialog(QDialog):
    settingsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)

        self.destination = QLineEdit("/media/AnimeLibrary")
        self.preferAnitopy = QCheckBox("Prefer Anitopy first")
        self.preferAnitopy.setChecked(True)
        self.fallback = QComboBox()
        self.fallback.addItems(["GuessIt", "Custom"])
        self.realtime = QCheckBox("Auto-scan incoming files")
        self.realtime.setChecked(True)
        self.tmdbKey = QLineEdit("••••••••••••")
        self.organizeMode = QComboBox()
        self.organizeMode.addItems(["Copy", "Move", "Hardlink"])

        form = QFormLayout()
        form.addRow("Destination Library", self.destination)

        line = QWidget()
        hl = QHBoxLayout(line)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(self.preferAnitopy)
        fb_label = QLabel("Fallback:")
        fb_label.setStyleSheet("color: gray; font-size: 12px;")
        hl.addWidget(fb_label)
        hl.addWidget(self.fallback)
        hl.addStretch(1)
        form.addRow("Parser order", line)

        form.addRow("Realtime Watcher", self.realtime)
        form.addRow("TMDB API Key", self.tmdbKey)
        form.addRow("Organize Mode", self.organizeMode)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self):
        self.settingsChanged.emit()
        super().accept()


# ----------------- Main Window -----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnimeSorter – PyQt5")
        self.resize(1200, 780)

        # State
        self.items: list[ParsedItem] = [x for x in MOCK_ITEMS]
        self.scanning = False
        self.progress = 0

        # Top bar
        top = QWidget()
        top_l = QHBoxLayout(top)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, path…")
        self.statusFilter = QComboBox()
        self.statusFilter.addItems(["all", "parsed", "needs_review", "error"])
        self.btnSettings = QPushButton("Settings")
        self.btnSettings.clicked.connect(self.openSettings)
        top_l.addWidget(QLabel("AnimeSorter"))
        top_l.addStretch(1)
        top_l.addWidget(self.search)
        top_l.addWidget(self.statusFilter)
        top_l.addWidget(self.btnSettings)

        # Splitter main area
        split = QSplitter()
        split.setChildrenCollapsible(False)

        # Left panel
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setSpacing(10)

        # Quick Actions box
        qa = QGroupBox("Quick Actions")
        qa_l = QVBoxLayout(qa)
        self.btnChooseFiles = QPushButton("Choose Files…")
        self.btnChooseFiles.clicked.connect(self.chooseFiles)
        self.btnChooseFolder = QPushButton("Choose Folder…")
        self.btnChooseFolder.clicked.connect(self.chooseFolder)
        self.btnStart = QPushButton("Start Scan")
        self.btnStart.clicked.connect(self.startScan)
        self.btnPause = QPushButton("Pause")
        self.btnPause.clicked.connect(self.stopScan)
        self.btnPause.setEnabled(False)
        self.progressBar = QProgressBar()
        self.progressBar.setValue(0)
        qa_l.addWidget(self.btnChooseFiles)
        qa_l.addWidget(self.btnChooseFolder)
        row = QWidget()
        row_l = QHBoxLayout(row)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.addWidget(self.btnStart)
        row_l.addWidget(self.btnPause)
        qa_l.addWidget(row)
        qa_l.addWidget(QLabel("Progress"))
        qa_l.addWidget(self.progressBar)

        # Statistics box
        stat = QGroupBox("Statistics")
        stat_l = QFormLayout(stat)
        self.lblTotal = QLabel("0")
        self.lblParsed = QLabel("0")
        self.lblPending = QLabel("0")
        self.btnClearCompleted = QPushButton("Clear completed")
        self.btnClearCompleted.clicked.connect(self.clearCompleted)
        stat_l.addRow("Total", self.lblTotal)
        stat_l.addRow("Parsed", self.lblParsed)
        stat_l.addRow("Pending", self.lblPending)
        stat_l.addRow("", self.btnClearCompleted)

        # Filters box
        filt = QGroupBox("Filters")
        filt_l = QFormLayout(filt)
        self.cmbResolution = QComboBox()
        self.cmbResolution.addItems(["All", "2160p", "1080p", "720p"])  # stub only
        self.cmbContainer = QComboBox()
        self.cmbContainer.addItems(["All", "MKV", "MP4"])  # stub only
        self.cmbCodec = QComboBox()
        self.cmbCodec.addItems(["All", "HEVC", "H.264"])  # stub only
        self.cmbYear = QComboBox()
        self.cmbYear.addItems(["All", "2025", "2024", "2023"])  # stub only
        self.btnResetFilters = QPushButton("Reset filters")
        self.btnResetFilters.clicked.connect(self.resetFilters)
        filt_l.addRow("Resolution", self.cmbResolution)
        filt_l.addRow("Container", self.cmbContainer)
        filt_l.addRow("Codec", self.cmbCodec)
        filt_l.addRow("Year", self.cmbYear)
        filt_l.addRow("", self.btnResetFilters)

        left_l.addWidget(qa)
        left_l.addWidget(stat)
        left_l.addWidget(filt)
        left_l.addStretch(1)

        # Right panel
        right = QWidget()
        right_l = QVBoxLayout(right)
        # Results header actions
        rh = QWidget()
        rh_l = QHBoxLayout(rh)
        rh_l.setContentsMargins(0, 0, 0, 0)
        rh_l.addWidget(QLabel("Scan Results"))
        rh_l.addStretch(1)
        self.btnSmartFilter = QPushButton("Smart filter")
        self.btnBulk = QPushButton("Bulk actions…")
        self.btnBulk.clicked.connect(self.bulkActions)
        rh_l.addWidget(self.btnSmartFilter)
        rh_l.addWidget(self.btnBulk)

        # Table + Grouped (Season/Episode) view
        self.model = ItemsTableModel(self.items)
        self.proxy = ItemsFilterProxy()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Grouped tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["Title / Season / Episode", "Files", "Best Res"]
        )  # minimal columns
        self.tree.setAlternatingRowColors(True)
        self.tree.setColumnWidth(0, 320)

        # Tabs to switch views
        self.viewTabs = QTabWidget()
        self.viewTabs.addTab(self.table, "Table")
        self.viewTabs.addTab(self.tree, "Season/Episode")

        # Footer actions
        rf = QWidget()
        rf_l = QHBoxLayout(rf)
        rf_l.setContentsMargins(0, 0, 0, 0)
        self.lblShowing = QLabel("")
        rf_l.addWidget(self.lblShowing)
        rf_l.addStretch(1)
        self.btnCommit = QPushButton("Commit organize")
        self.btnCommit.clicked.connect(
            lambda: QMessageBox.information(self, "Commit", "Commit organization plan (stub)")
        )
        self.btnSimulate = QPushButton("Simulate")
        self.btnSimulate.clicked.connect(
            lambda: QMessageBox.information(self, "Simulate", "Simulate file moves (stub)")
        )
        rf_l.addWidget(self.btnCommit)
        rf_l.addWidget(self.btnSimulate)

        # Logs tabs
        self.tabs = QTabWidget()
        self.txtLog = QTextEdit()
        self.txtLog.setReadOnly(True)
        self.txtErr = QTextEdit()
        self.txtErr.setReadOnly(True)
        self.txtLog.setText(
            """[12:00:01] Watching /downloads ...\n[12:00:04] Parsed Frieren S01E01 (score=0.92, tmdb=209867)\n[12:00:08] Found potential special episode; awaiting review\n[12:00:17] Ready to organize 1 item (copy mode)"""
        )
        self.txtErr.setText(
            """[12:01:12] Failed TMDB match for Unknown.Show.12v2.mp4 — try manual search with an alias."""
        )
        self.tabs.addTab(self.txtLog, "Activity Log")
        self.tabs.addTab(self.txtErr, "Errors")

        # Manual Match box (simple stub)
        mm = QGroupBox("Manual Match")
        mm_l = QHBoxLayout(mm)
        self.leManual = QLineEdit()
        self.leManual.setPlaceholderText("Search TMDB for title (ja/en/ko)")
        btnMMSearch = QPushButton("Search")
        btnMMAttach = QPushButton("Attach")
        btnMMSearch.clicked.connect(
            lambda: QMessageBox.information(self, "TMDB", "Search TMDB (stub)")
        )
        btnMMAttach.clicked.connect(
            lambda: QMessageBox.information(self, "TMDB", "Attach metadata (stub)")
        )
        mm_l.addWidget(self.leManual)
        mm_l.addWidget(btnMMSearch)
        mm_l.addWidget(btnMMAttach)

        # Assemble right
        right_l.addWidget(rh)
        right_l.addWidget(self.viewTabs, 1)
        right_l.addWidget(rf)
        right_l.addWidget(self.tabs)
        right_l.addWidget(mm)

        # Put into splitter
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)

        # Root layout
        root = QWidget()
        root_l = QVBoxLayout(root)
        root_l.addWidget(top)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        root_l.addWidget(line)
        root_l.addWidget(split, 1)
        self.setCentralWidget(root)

        # Wire search/filter
        self.search.textChanged.connect(self.proxy.setQuery)
        self.statusFilter.currentTextChanged.connect(self.proxy.setStatus)
        # Rebuild grouped view on filter/search changes
        self.search.textChanged.connect(lambda _=None: self.rebuildGroupedView())
        self.statusFilter.currentTextChanged.connect(lambda _=None: self.rebuildGroupedView())

        # Timer for scanning simulation
        self.timer = QTimer(self)
        self.timer.setInterval(700)
        self.timer.timeout.connect(self.onScanTick)

        # Initial refresh
        self.refreshStats()
        self.refreshShowing()
        self.rebuildGroupedView()

        # Double-click action cell to change status quickly
        self.table.doubleClicked.connect(self.onDoubleClick)

    # ------- UI actions -------
    def chooseFiles(self):
        QFileDialog.getOpenFileNames(self, "Choose files")

    def chooseFolder(self):
        QFileDialog.getExistingDirectory(self, "Choose folder")

    def startScan(self):
        self.scanning = True
        self.progress = 0
        self.progressBar.setValue(0)
        self.btnStart.setEnabled(False)
        self.btnPause.setEnabled(True)
        self.timer.start()

    def stopScan(self):
        self.scanning = False
        self.timer.stop()
        self.btnStart.setEnabled(True)
        self.btnPause.setEnabled(False)

    def onScanTick(self):
        # Simulate incremental progress
        self.progress = min(100, self.progress + 7)
        self.progressBar.setValue(self.progress)
        if self.progress >= 100:
            self.stopScan()
            # Example: append a log line
            self.txtLog.append("[12:02:23] Scan finished. Parsed 2 items; 1 pending.")

    def clearCompleted(self):
        # Remove rows with status == 'parsed'
        self.model.beginResetModel()
        self.items = [it for it in self.items if it.status != "parsed"]
        self.model.items = self.items
        self.model.endResetModel()
        self.refreshStats()
        self.refreshShowing()
        self.rebuildGroupedView()

    def resetFilters(self):
        self.cmbResolution.setCurrentIndex(0)
        self.cmbContainer.setCurrentIndex(0)
        self.cmbCodec.setCurrentIndex(0)
        self.cmbYear.setCurrentIndex(0)
        self.search.clear()
        self.statusFilter.setCurrentText("all")

    def bulkActions(self):
        QMessageBox.information(
            self, "Bulk actions", "- TMDB auto-match\n- Organize selected\n- Export CSV\n(Stub)"
        )

    def refreshStats(self):
        total = len(self.items)
        parsed = len([i for i in self.items if i.status == "parsed"])
        pending = total - parsed
        self.lblTotal.setText(str(total))
        self.lblParsed.setText(str(parsed))
        self.lblPending.setText(str(pending))

    def refreshShowing(self):
        self.lblShowing.setText(f"Showing {self.proxy.rowCount()} of {self.model.rowCount()} items")
        # Keep grouped view in sync (cheap enough for this dataset)
        self.rebuildGroupedView()

        self.lblShowing.setText(f"Showing {self.proxy.rowCount()} of {self.model.rowCount()} items")

    def openSettings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # Apply settings here as needed
            QMessageBox.information(self, "Settings", "Settings saved (stub)")

    def onDoubleClick(self, idx: QModelIndex):
        # Toggle status cycle: parsed -> needs_review -> error -> parsed
        src = self.proxy.mapToSource(idx)
        row = src.row()
        if row < 0:
            return
        current = self.model.items[row].status
        nxt = {"parsed": "needs_review", "needs_review": "error", "error": "parsed"}[current]
        self.model.setStatus(row, nxt)
        self.refreshStats()
        self.refreshShowing()
        self.rebuildGroupedView()

    def rebuildGroupedView(self):
        """Build season/episode grouped tree from *filtered* rows in proxy."""
        self.tree.clear()
        # maps for season and episode nodes
        season_nodes = {}
        episode_nodes = {}

        def best_res(res_list):
            order = {"4320p": 5, "2160p": 4, "1440p": 3, "1080p": 2, "720p": 1}
            sel = None
            score = -1
            for r in res_list:
                sc = order.get(r or "", 0)
                if sc > score:
                    sel, score = r, sc
            return sel or "-"

        # aggregate by (title, season, episode)
        groups = {}
        for r in range(self.proxy.rowCount()):
            src = self.proxy.mapToSource(self.proxy.index(r, 0))
            it = self.model.items[src.row()]
            key = (it.detectedTitle, it.season or 0, it.episode or 0)
            groups.setdefault(key, []).append(it)

        # build tree
        for (title, season, episode), files in sorted(
            groups.items(), key=lambda k: (k[0][0].lower(), k[0][1], k[0][2])
        ):
            s_key = (title, season)
            if s_key not in season_nodes:
                season_item = QTreeWidgetItem(
                    [f"{title} – Season {season}", "", ""]
                )  # title at season level
                self.tree.addTopLevelItem(season_item)
                season_nodes[s_key] = season_item
            else:
                season_item = season_nodes[s_key]

            # episode node with count and best res
            res_list = [f.resolution for f in files if f.resolution]
            ep_best = best_res(res_list)
            ep_item = QTreeWidgetItem([f"E{episode:02d}", str(len(files)), ep_best])
            season_item.addChild(ep_item)

            # leaf nodes for each file
            for f in files:
                leaf = QTreeWidgetItem([f.sourcePath, "1", f.resolution or "-"])
                ep_item.addChild(leaf)

        self.tree.expandToDepth(1)


# ----------------- Entrypoint -----------------
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
