"""
경로 계획 로직

메타데이터를 기반으로 파일의 최종 이동 경로를 결정하는 로직을 제공합니다.
TV 시리즈와 영화를 구분하여 적절한 폴더 구조를 생성합니다.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class PathPlanner:
    """
    경로 계획자
    
    메타데이터를 기반으로 파일의 최종 이동 경로를 결정합니다.
    TV 시리즈와 영화를 구분하여 적절한 폴더 구조를 생성합니다.
    """
    
    def __init__(
        self,
        folder_template: str = "{title} ({year})",
        keep_original_name: bool = True,
        overwrite_existing: bool = False
    ):
        """
        PathPlanner 초기화
        
        Args:
            folder_template: 폴더 이름 템플릿 (기본값: "{title} ({year})")
            keep_original_name: 원본 파일명 유지 여부 (기본값: True)
            overwrite_existing: 기존 파일 덮어쓰기 여부 (기본값: False)
        """
        self.folder_template = folder_template
        self.keep_original_name = keep_original_name
        self.overwrite_existing = overwrite_existing
        
    def plan_path(
        self, 
        source_file: Path, 
        target_dir: Path, 
        metadata: Optional[Dict[str, Any]] = None,
        clean_result: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        파일의 이동 경로를 계획
        
        Args:
            source_file: 원본 파일 경로
            target_dir: 대상 디렉토리
            metadata: 메타데이터 (옵션)
            clean_result: 파일명 정제 결과 (옵션)
            
        Returns:
            Path: 계획된 대상 파일 경로
        """
        try:
            # 메타데이터가 있는 경우 메타데이터 기반 경로 결정
            if metadata:
                return self._plan_path_with_metadata(source_file, target_dir, metadata)
            
            # 정제 결과가 있는 경우 정제 결과 기반 경로 결정
            elif clean_result:
                return self._plan_path_with_clean_result(source_file, target_dir, clean_result)
            
            # 둘 다 없는 경우 원본 파일명 사용
            else:
                return self._plan_path_with_filename(source_file, target_dir)
                
        except Exception as e:
            logger.error(f"Error planning path for {source_file}: {e}")
            # 오류 발생 시 원본 파일명 사용
            return self._plan_path_with_filename(source_file, target_dir)
            
    def _plan_path_with_metadata(
        self, 
        source_file: Path, 
        target_dir: Path, 
        metadata: Dict[str, Any]
    ) -> Path:
        """메타데이터 기반 경로 계획"""
        # TV 시리즈와 영화 구분
        is_tv = self._is_tv_series(metadata)
        
        # 기본 정보 추출
        if is_tv:
            title = metadata.get("name", "Unknown TV Show")
            year = self._extract_year(metadata.get("first_air_date"))
        else:
            title = metadata.get("title", "Unknown Movie")
            year = self._extract_year(metadata.get("release_date"))
            
        # 경로에 사용할 수 없는 문자 제거
        safe_title = self._sanitize_filename(title)
        
        # 폴더 템플릿 적용
        folder_name = self.folder_template.format(
            title=safe_title,
            year=year or "",
            type="TV Show" if is_tv else "Movie"
        ).strip()
        
        # 끝에 불필요한 괄호 제거
        folder_name = re.sub(r'\(\s*\)$', '', folder_name).strip()
        
        # 시즌 정보 추출 (TV 시리즈인 경우)
        season_folder = ""
        if is_tv and "season_number" in metadata:
            season_num = metadata.get("season_number", 1)
            season_folder = f"Season {season_num:02d}"
            
        # 최종 대상 폴더 경로 구성
        if is_tv and season_folder:
            target_folder = target_dir / folder_name / season_folder
        else:
            target_folder = target_dir / folder_name
            
        # 파일명 결정
        if self.keep_original_name:
            # 원본 파일명 유지
            target_filename = source_file.name
        else:
            # 메타데이터 기반 파일명 생성
            target_filename = self._generate_filename(source_file, metadata, is_tv)
            
        return target_folder / target_filename
        
    def _plan_path_with_clean_result(
        self, 
        source_file: Path, 
        target_dir: Path, 
        clean_result: Dict[str, Any]
    ) -> Path:
        """정제 결과 기반 경로 계획"""
        title = clean_result.get("title", source_file.stem)
        year = clean_result.get("year")
        season = clean_result.get("season", 1)
        episode = clean_result.get("episode")
        
        # 경로에 사용할 수 없는 문자 제거
        safe_title = self._sanitize_filename(title)
        
        # 폴더 템플릿 적용
        folder_name = self.folder_template.format(
            title=safe_title,
            year=year or "",
            type="TV Show" if episode else "Movie"
        ).strip()
        
        # 끝에 불필요한 괄호 제거
        folder_name = re.sub(r'\(\s*\)$', '', folder_name).strip()
        
        # 시즌 정보 (에피소드가 있는 경우)
        season_folder = ""
        if episode:
            season_folder = f"Season {season:02d}"
            
        # 최종 대상 폴더 경로 구성
        if season_folder:
            target_folder = target_dir / folder_name / season_folder
        else:
            target_folder = target_dir / folder_name
            
        # 파일명 결정
        if self.keep_original_name:
            target_filename = source_file.name
        else:
            target_filename = self._generate_filename_from_clean_result(
                source_file, clean_result
            )
            
        return target_folder / target_filename
        
    def _plan_path_with_filename(
        self, 
        source_file: Path, 
        target_dir: Path
    ) -> Path:
        """파일명 기반 경로 계획 (폴백)"""
        # 파일명에서 확장자 제거
        filename_without_ext = source_file.stem
        
        # 경로에 사용할 수 없는 문자 제거
        safe_filename = self._sanitize_filename(filename_without_ext)
        
        # 기본 폴더명 생성
        folder_name = f"Unknown - {safe_filename}"
        
        target_folder = target_dir / folder_name
        return target_folder / source_file.name
        
    def _is_tv_series(self, metadata: Dict[str, Any]) -> bool:
        """TV 시리즈 여부 판단"""
        # media_type이 tv인 경우
        if metadata.get("media_type") == "tv":
            return True
            
        # number_of_seasons가 있는 경우
        if "number_of_seasons" in metadata:
            return True
            
        # name 필드가 있고 title 필드가 없는 경우 (TV 시리즈의 경우)
        if "name" in metadata and "title" not in metadata:
            return True
            
        return False
        
    def _extract_year(self, date_string: Optional[str]) -> Optional[int]:
        """날짜 문자열에서 연도 추출"""
        if not date_string:
            return None
            
        try:
            # YYYY-MM-DD 형식에서 연도 추출
            year_str = date_string.split("-")[0]
            return int(year_str)
        except (ValueError, IndexError):
            return None
            
    def _sanitize_filename(self, filename: str) -> str:
        """파일명에서 사용할 수 없는 문자 제거"""
        # 경로에 사용할 수 없는 문자 제거/대체
        invalid_chars = r'[\/:*?"<>|]'
        sanitized = re.sub(invalid_chars, '', filename)
        
        # 연속된 공백을 단일 공백으로 변경
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # 앞뒤 공백 제거
        sanitized = sanitized.strip()
        
        return sanitized
        
    def _generate_filename(
        self, 
        source_file: Path, 
        metadata: Dict[str, Any], 
        is_tv: bool
    ) -> str:
        """메타데이터 기반 파일명 생성"""
        if is_tv and "episode_number" in metadata:
            # TV 시리즈 에피소드
            season_num = metadata.get("season_number", 1)
            episode_num = metadata.get("episode_number", 1)
            episode_title = metadata.get("episode_name", "")
            
            if episode_title:
                safe_episode_title = self._sanitize_filename(episode_title)
                return f"S{season_num:02d}E{episode_num:02d} - {safe_episode_title}{source_file.suffix}"
            else:
                return f"S{season_num:02d}E{episode_num:02d}{source_file.suffix}"
        else:
            # 영화 또는 일반 파일
            title = metadata.get("title") or metadata.get("name", source_file.stem)
            safe_title = self._sanitize_filename(title)
            return f"{safe_title}{source_file.suffix}"
            
    def _generate_filename_from_clean_result(
        self, 
        source_file: Path, 
        clean_result: Dict[str, Any]
    ) -> str:
        """정제 결과 기반 파일명 생성"""
        title = clean_result.get("title", source_file.stem)
        season = clean_result.get("season", 1)
        episode = clean_result.get("episode")
        
        if episode:
            # TV 시리즈 에피소드
            episode_title = clean_result.get("episode_title", "")
            if episode_title:
                safe_episode_title = self._sanitize_filename(episode_title)
                return f"S{season:02d}E{episode:02d} - {safe_episode_title}{source_file.suffix}"
            else:
                return f"S{season:02d}E{episode:02d}{source_file.suffix}"
        else:
            # 영화 또는 일반 파일
            safe_title = self._sanitize_filename(title)
            return f"{safe_title}{source_file.suffix}"
            
    def create_directories(self, target_path: Path) -> None:
        """필요한 디렉토리 생성"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
    def check_file_exists(self, target_path: Path) -> bool:
        """대상 파일 존재 여부 확인"""
        return target_path.exists()
        
    def get_unique_path(self, target_path: Path) -> Path:
        """중복되지 않는 경로 생성"""
        if not target_path.exists() or self.overwrite_existing:
            return target_path
            
        # 파일명에 번호 추가
        counter = 1
        while True:
            stem = target_path.stem
            suffix = target_path.suffix
            new_path = target_path.parent / f"{stem} ({counter}){suffix}"
            
            if not new_path.exists():
                return new_path
                
            counter += 1 