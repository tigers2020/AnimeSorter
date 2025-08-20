"""
테이블 모델 및 필터 프록시
파싱된 애니메이션 아이템을 테이블에 표시하고 필터링하는 기능을 제공합니다.
"""

import os
import re
from typing import List, Optional, Dict

from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt, QModelIndex, QVariant, QSortFilterProxyModel
from PyQt5.QtGui import QIcon, QPixmap

from core.tmdb_client import TMDBAnimeInfo
from managers.anime_data_manager import ParsedItem


class GroupedListModel(QAbstractTableModel):
    """그룹화된 애니메이션 목록을 표시하는 모델"""
    headers = [
        "포스터", "제목", "최종 이동 경로", "시즌", "에피소드 수", "최고 해상도", "상태"
    ]

    def __init__(self, grouped_items: Dict[str, List] = None, tmdb_client=None, destination_directory: str = None):
        super().__init__()
        self.grouped_items = grouped_items or {}
        self.tmdb_client = tmdb_client
        self.destination_directory = destination_directory or "대상 폴더"
        self._group_list = []  # 그룹 리스트 (순서 유지)
        self._update_group_list()
    
    def set_grouped_items(self, grouped_items: Dict[str, List]):
        """그룹화된 아이템 설정"""
        self.beginResetModel()
        self.grouped_items = grouped_items
        self._update_group_list()
        self.endResetModel()
    
    def _update_group_list(self):
        """그룹 리스트 업데이트"""
        self._group_list = []
        for group_key, items in self.grouped_items.items():
            if not items:
                continue
                
            # 그룹 정보 생성
            representative = items[0]
            
            # 에피소드 범위 계산
            episodes = [item.episode for item in items if item.episode is not None]
            if episodes:
                min_ep = min(episodes)
                max_ep = max(episodes)
                if min_ep == max_ep:
                    episode_info = f"E{min_ep:02d}"
                else:
                    episode_info = f"E{min_ep:02d}-E{max_ep:02d}"
            else:
                episode_info = "Unknown"
            
            # 해상도별 분포 (더 정확한 해상도 정보 사용)
            resolutions = {}
            for item in items:
                res = item.resolution or "Unknown"
                if res != "Unknown":
                    # 해상도 정규화 (예: 1080p, 720p 등)
                    if '1080' in res or '1920' in res:
                        res = '1080p'
                    elif '720' in res or '1280' in res:
                        res = '720p'
                    elif '480' in res or '854' in res:
                        res = '480p'
                    elif '080' in res:  # 080p는 1080p로 수정
                        res = '1080p'
                resolutions[res] = resolutions.get(res, 0) + 1
            
            # 가장 높은 해상도 선택 (우선순위: 1080p > 720p > 480p > Unknown)
            resolution_priority = {'1080p': 4, '720p': 3, '480p': 2, 'Unknown': 1}
            best_resolution = max(resolutions.items(), 
                                key=lambda x: (resolution_priority.get(x[0], 0), x[1]))[0] if resolutions else "Unknown"
            
            # 그룹 상태 (TMDB 매치가 있으면 우선, 그 다음 기존 로직)
            if representative.tmdbMatch:
                group_status = 'tmdb_matched'
            else:
                statuses = [item.status for item in items]
                if all(s == 'parsed' for s in statuses):
                    group_status = 'complete'
                elif any(s == 'error' for s in statuses):
                    group_status = 'error'
                elif any(s == 'needs_review' for s in statuses):
                    group_status = 'partial'
                else:
                    group_status = 'pending'
            
            # 최종 이동 경로 계산
            final_path = self._calculate_final_path(representative, items)
            
            group_info = {
                'key': group_key,
                'title': representative.title or representative.detectedTitle or "Unknown",
                'season': representative.season or 1,
                'episode_info': episode_info,
                'file_count': len(items),
                'best_resolution': best_resolution,
                'status': group_status,
                'items': items,
                'tmdb_match': representative.tmdbMatch,
                'tmdb_anime': representative.tmdbMatch,  # TMDB 애니메이션 정보
                'final_path': final_path  # 최종 이동 경로
            }
            
            self._group_list.append(group_info)
        
        # 제목, 시즌, 에피소드 순으로 정렬
        self._group_list.sort(key=lambda x: (x['title'].lower(), x['season'], x['episode_info']))
    
    def _calculate_final_path(self, representative, items):
        """최종 이동 경로 계산"""
        try:
            # 기본 대상 폴더 (실제로는 설정에서 가져와야 함)
            base_destination = self.destination_directory
            
            # 제목 결정 (TMDB 매치가 있으면 TMDB 제목, 없으면 원본 제목)
            if representative.tmdbMatch and representative.tmdbMatch.name:
                raw_title = representative.tmdbMatch.name
            else:
                raw_title = representative.title or representative.detectedTitle or "Unknown"
            
            # 특수문자 제거 및 정제 (알파벳, 숫자, 한글, 공백만 허용)
            safe_title = re.sub(r'[^a-zA-Z0-9가-힣\s]', '', raw_title)
            # 연속된 공백을 하나로 치환
            safe_title = re.sub(r'\s+', ' ', safe_title)
            # 앞뒤 공백 제거
            safe_title = safe_title.strip()
            
            if not safe_title:
                safe_title = "Unknown"
            
            # 시즌 정보
            season = representative.season or 1
            season_folder = f"Season{season:02d}"
            
            # 파일명들 (원본 파일명들)
            file_names = []
            for item in items:
                if hasattr(item, 'filename') and item.filename:
                    file_names.append(item.filename)
                elif hasattr(item, 'sourcePath') and item.sourcePath:
                    file_names.append(os.path.basename(item.sourcePath))
            
            # 파일명이 있으면 첫 번째 파일명 표시, 없으면 "original_file_names"
            if file_names:
                file_name_display = file_names[0]
                if len(file_names) > 1:
                    file_name_display += f" (+{len(file_names)-1}개)"
            else:
                file_name_display = "original_file_names"
            
            # 최종 경로 구성
            final_path = f"{base_destination}/{safe_title}/{season_folder}/{file_name_display}"
            
            return final_path
            
        except Exception as e:
            print(f"⚠️ 최종 경로 계산 실패: {e}")
            return "경로 계산 오류"
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._group_list)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        if index.row() >= len(self._group_list):
            return QVariant()
        
        group_info = self._group_list[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:  # 포스터 - 이미지만 표시하므로 빈 문자열 반환
                return ""
            elif col == 1:  # 제목 - TMDB 매치가 있으면 TMDB 제목 우선 사용
                if group_info.get('tmdb_match') and group_info['tmdb_match'].name:
                    return group_info['tmdb_match'].name  # TMDB 한글 제목
                else:
                    return group_info.get('title', 'Unknown')
            elif col == 2:  # 최종 이동 경로
                return group_info.get('final_path', 'N/A')
            elif col == 3:  # 시즌
                season = group_info.get('season')
                return f"S{season:02d}" if season is not None else "-"
            elif col == 4:  # 에피소드 수
                return str(group_info.get('file_count', 0))
            elif col == 5:  # 최고 해상도
                return group_info.get('best_resolution', '-')
            elif col == 6:  # 상태
                status = group_info.get('status', 'unknown')
                status_map = {
                    'complete': '✅ 완료',
                    'partial': '⚠️ 부분',
                    'pending': '⏳ 대기중',
                    'error': '❌ 오류',
                    'tmdb_matched': '🎯 TMDB 매치'
                }
                return status_map.get(status, status)
        
        elif role == Qt.DecorationRole:
            if col == 0:  # 포스터 컬럼에 이미지 표시
                if group_info.get('tmdb_match') and group_info['tmdb_match'].poster_path and self.tmdb_client:
                    try:
                        poster_path = self.tmdb_client.get_poster_path(group_info['tmdb_match'].poster_path, 'w154')
                        
                        if poster_path and os.path.exists(poster_path):
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                # 80x120 크기로 스케일링 (포스터 비율 유지)
                                scaled_pixmap = pixmap.scaled(80, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                return scaled_pixmap
                    except Exception as e:
                        print(f"포스터 로드 실패: {e}")
                
                # 기본 아이콘 반환
                return QIcon("🎬")
        
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return QVariant()
    
    def get_group_at_row(self, row: int) -> Optional[dict]:
        """특정 행의 그룹 정보 반환"""
        if 0 <= row < len(self._group_list):
            return self._group_list[row]
        return None

    def get_column_widths(self) -> Dict[int, int]:
        """컬럼별 권장 너비 반환"""
        return {
            0: 80,   # 포스터
            1: 300,  # 제목
            2: 250,  # 최종 이동 경로
            3: 80,   # 시즌
            4: 100,  # 에피소드 수
            5: 100,  # 최고 해상도
            6: 100   # 상태
        }
    
    def get_stretch_columns(self) -> List[int]:
        """확장 가능한 컬럼 인덱스 반환"""
        return [1]  # 제목 컬럼만 확장 가능


class DetailFileModel(QAbstractTableModel):
    """그룹 내 상세 파일 목록을 표시하는 모델"""
    headers = [
        "포스터", "파일명", "시즌", "에피소드", "해상도", "코덱", "상태"
    ]

    def __init__(self, items: List[ParsedItem] = None, tmdb_client=None):
        super().__init__()
        self.items = items or []
        self.tmdb_client = tmdb_client
    
    def set_items(self, items: List[ParsedItem]):
        """아이템 목록 설정 및 테이블 새로고침"""
        self.beginResetModel()
        self.items = items
        self.endResetModel()

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
            if col == 0:  # 포스터 - 이미지만 표시하므로 빈 문자열 반환
                return ""
            elif col == 1:  # 파일명
                return os.path.basename(item.sourcePath) if item.sourcePath else "—"
            elif col == 2:  # 시즌
                return f"S{item.season:02d}" if item.season is not None else "-"
            elif col == 3:  # 에피소드
                return f"E{item.episode:02d}" if item.episode is not None else "-"
            elif col == 4:  # 해상도
                return item.resolution or "-"
            elif col == 5:  # 코덱
                return item.codec or "-"
            elif col == 6:  # 상태
                status_map = {
                    'parsed': '✅ 완료',
                    'needs_review': '⚠️ 검토필요',
                    'error': '❌ 오류',
                    'skipped': '⏭️ 건너뛰기',
                    'pending': '⏳ 대기중'
                }
                return status_map.get(item.status, item.status)
        
        elif role == Qt.DecorationRole:
            if col == 0:  # 포스터 컬럼에 이미지 표시
                if item.tmdbMatch and item.tmdbMatch.poster_path and self.tmdb_client:
                    try:
                        poster_path = self.tmdb_client.get_poster_path(item.tmdbMatch.poster_path, 'w92')
                        
                        if poster_path and os.path.exists(poster_path):
                            pixmap = QPixmap(poster_path)
                            if not pixmap.isNull():
                                # 60x90 크기로 스케일링 (포스터 비율 유지)
                                scaled_pixmap = pixmap.scaled(60, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                return scaled_pixmap
                    except Exception as e:
                        print(f"포스터 로드 실패: {e}")
                
                # 기본 아이콘 반환
                return QIcon("🎬")
        
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return QVariant()
    
    def get_column_widths(self) -> Dict[int, int]:
        """컬럼별 권장 너비 반환"""
        return {
            0: 60,   # 포스터
            1: 300,  # 파일명
            2: 80,   # 시즌
            3: 80,   # 에피소드
            4: 100,  # 해상도
            5: 100,  # 코덱
            6: 100   # 상태
        }
    
    def get_stretch_columns(self) -> List[int]:
        """확장 가능한 컬럼 인덱스 반환"""
        return [1]  # 파일명 컬럼만 확장 가능
