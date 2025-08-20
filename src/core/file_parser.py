"""
파일명 파싱 모듈 - AnimeSorter

애니메이션 파일명에서 메타데이터를 추출하는 기능을 제공합니다.
"""

import re
import os
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache


@dataclass
class ParsedMetadata:
    """파싱된 파일 메타데이터"""
    title: str
    season: Optional[int] = None
    episode: Optional[int] = None
    year: Optional[int] = None
    resolution: Optional[str] = None
    group: Optional[str] = None
    codec: Optional[str] = None
    container: Optional[str] = None
    audio_codec: Optional[str] = None
    language: Optional[str] = None
    quality: Optional[str] = None
    source: Optional[str] = None
    confidence: float = 0.0


class FileParser:
    """애니메이션 파일명 파싱 엔진 (최적화됨)"""
    
    def __init__(self):
        """파서 초기화"""
        self.patterns = self._compile_patterns()
        # 캐시 크기 설정 (메모리 사용량과 성능의 균형)
        self._parse_cache_size = 256
    
    def _compile_patterns(self) -> List[Tuple[re.Pattern, str, float]]:
        """파싱 패턴 컴파일 (최적화된 순서)"""
        patterns = [
            # 가장 일반적이고 정확한 패턴들을 먼저 배치
            # 패턴 1: Title.S##E##.Resolution.codec.ext (가장 정확함)
            (re.compile(r'^(.+?)\.S(\d+)E(\d+)\.(\d+p)\.([^.]+)\.([^.]+)$', re.IGNORECASE), 
             'title_season_episode_resolution_dots', 0.95),
            
            # 패턴 2: Title.E## 형태 (Exx 표기 - 매우 일반적)
            (re.compile(r'^(.+?)\.E(\d+)', re.IGNORECASE), 
             'title_episode_exx', 0.9),
            
            # 패턴 3: [Group] Title - Episode (추가정보).ext
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s*\([^)]*(\d{3,4}x\d{3,4}|\d{3,4}p)[^)]*\)', re.IGNORECASE), 
             'group_title_episode_with_resolution', 0.9),
            
            # 패턴 4: Title - Episode화/話 형태 (한국어)
            (re.compile(r'^(.+?)\s*(\d+)화?\s*(?:\([^)]*(\d+x\d+|\d+p)[^)]*\))?', re.IGNORECASE), 
             'title_episode_korean', 0.85),
            
            # 패턴 5: Title.E##.Resolution 형태
            (re.compile(r'^(.+?)\.E(\d+)\.(\d+p)', re.IGNORECASE), 
             'title_episode_exx_resolution', 0.9),
            
            # 패턴 6: [Group] Title - Episode (기타정보).ext
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s*(?:\([^)]+\))?', re.IGNORECASE), 
             'group_title_episode', 0.8),
            
            # 패턴 7: Title - Episode [Resolution].ext
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s*\[([^\]]*(?:\d+p)[^\]]*)\]', re.IGNORECASE), 
             'group_title_episode_bracket_resolution', 0.9),
            
            # 패턴 8: Title EP## 형태
            (re.compile(r'^(.+?)\s+EP(\d+)', re.IGNORECASE), 
             'title_episode_ep', 0.8),
            
            # 패턴 9: Title - Episode RAW/END 등
            (re.compile(r'^(.+?)\s*-\s*(\d+)\s*(RAW|END|FIN|COMPLETE)', re.IGNORECASE), 
             'title_episode_special', 0.8),
            
            # 패턴 10: Title Season Episode.ext (공백으로 구분)
            (re.compile(r'^(.+?)\s+(?:Season\s*(\d+))?\s*(\d+)$', re.IGNORECASE), 
             'title_season_episode_space', 0.7),
            
            # 패턴 11: [Group]Title Episode.ext (공백 없음)
            (re.compile(r'^\[([^\]]+)\]([^-\s]+)\s*(\d+)', re.IGNORECASE), 
             'group_title_episode_nospace', 0.7),
            
            # 패턴 12: Title Episode.ext (간단한 형태) - 마지막에 배치
            (re.compile(r'^(.+?)\s+(\d+)$', re.IGNORECASE), 
             'title_episode_simple', 0.6)
        ]
        return patterns
    
    @lru_cache(maxsize=256)
    def parse_filename(self, filename: str) -> Optional[ParsedMetadata]:
        """파일명에서 메타데이터 추출 (캐시됨)"""
        if not filename:
            return None
        
        # 파일 경로에서 파일명만 추출
        basename = os.path.basename(filename)
        
        # 확장자 제거
        name_without_ext = os.path.splitext(basename)[0]
        
        # 컨테이너 추출
        container = os.path.splitext(basename)[1].lower()
        
        # 패턴 매칭 시도 (최적화된 순서)
        for pattern, pattern_type, base_confidence in self.patterns:
            match = pattern.match(name_without_ext)
            if match:
                metadata = self._extract_metadata(match, pattern_type, base_confidence, container)
                if metadata:
                    return metadata
        
        # 패턴 매칭 실패 시 fallback 파싱
        return self._improved_fallback_parse(name_without_ext, container)
    
    def _extract_metadata(self, match, pattern_type: str, base_confidence: float, container: str) -> Optional[ParsedMetadata]:
        """매치된 패턴에서 메타데이터 추출 (최적화됨)"""
        try:
            groups = match.groups()
            
            if pattern_type == 'title_season_episode_resolution_dots':
                title, season, episode, resolution, codec, _ = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    season=int(season),
                    episode=int(episode),
                    resolution=resolution,
                    codec=codec,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_episode_exx':
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    season=1,  # Exx 형태는 보통 시즌 1
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'group_title_episode_with_resolution':
                group, title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    resolution=resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_episode_korean':
                title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_episode_exx_resolution':
                title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    season=1,
                    episode=int(episode),
                    resolution=resolution,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'group_title_episode':
                group, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'group_title_episode_bracket_resolution':
                group, title, episode, resolution = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    resolution=resolution,
                    group=group,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_episode_ep':
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_episode_special':
                title, episode, special = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    quality=special,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_season_episode_space':
                title, season, episode = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    season=int(season) if season else 1,
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'group_title_episode_nospace':
                group, title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    group=group,
                    container=container,
                    confidence=base_confidence
                )
            
            elif pattern_type == 'title_episode_simple':
                title, episode = groups
                return ParsedMetadata(
                    title=self._clean_title(title),
                    episode=int(episode),
                    container=container,
                    confidence=base_confidence
                )
            
        except (ValueError, IndexError) as e:
            print(f"메타데이터 추출 오류: {e}")
            return None
        
        return None
    
    @lru_cache(maxsize=128)
    def _improved_fallback_parse(self, filename: str, container: str) -> Optional[ParsedMetadata]:
        """개선된 fallback 파싱 (캐시됨)"""
        try:
            # 에피소드 번호 추출 (더 정확한 방법)
            episode_match = re.search(r'(\d{1,2})', filename)
            episode = int(episode_match.group(1)) if episode_match else None
            
            # 해상도 추출 (캐시된 함수 사용)
            resolution = self._extract_resolution_cached(filename)
            
            # 제목 정리 (에피소드 번호 제거)
            title = filename
            if episode:
                title = re.sub(rf'\D{episode}\D', ' ', title)
            
            title = self._clean_title_cached(title)
            
            return ParsedMetadata(
                title=title,
                episode=episode,
                resolution=resolution,
                container=container,
                confidence=0.4  # fallback 신뢰도
            )
            
        except Exception as e:
            print(f"Fallback 파싱 오류: {e}")
            return None
    
    @lru_cache(maxsize=64)
    def _extract_resolution_cached(self, text: str) -> Optional[str]:
        """텍스트에서 해상도 추출 (캐시됨)"""
        # 해상도 패턴들 (우선순위 순)
        resolution_patterns = [
            (r'(\d{3,4}x\d{3,4})', 'exact'),      # 1920x1080 형태
            (r'(\d{3,4}p)', 'p'),                 # 720p, 1080p 형태
            (r'(4K|2160p)', '4k'),                # 4K
            (r'(2K|1440p)', '2k'),                # 2K
            (r'(HD|720p)', '720p'),               # HD/720p
            (r'(SD|480p)', '480p'),               # SD/480p
            (r'(\d{3,4}i)', 'interlaced'),        # 인터레이스
            (r'(\d{3,4}v)', 'vertical'),          # 수직 해상도만
        ]
        
        for pattern, res_type in resolution_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                resolution = match.group(1).upper()
                
                # 해상도 정규화
                if res_type == 'exact':
                    # 1920x1080 형태를 1080p로 변환
                    if '1920x1080' in resolution or '1080x1920' in resolution:
                        return '1080p'
                    elif '1280x720' in resolution or '720x1280' in resolution:
                        return '720p'
                    elif '854x480' in resolution or '480x854' in resolution:
                        return '480p'
                    else:
                        return resolution
                
                elif res_type == 'p':
                    # 080p는 1080p로 수정
                    if resolution == '080P':
                        return '1080p'
                    return resolution
                
                elif res_type == '4k':
                    return '4K'
                elif res_type == '2k':
                    return '2K'
                elif res_type == '720p':
                    return '720p'
                elif res_type == '480p':
                    return '480p'
                else:
                    return resolution
        
        return None
    
    @lru_cache(maxsize=128)
    def _clean_title_cached(self, title: str) -> str:
        """제목에서 불필요한 정보 제거 (캐시됨)"""
        if not title:
            return ""
        
        # 1단계: 기본 정리
        title = re.sub(r'[._-]+', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        
        # 2단계: 에피소드 표기 제거
        title = re.sub(r'\b(?:E\d+|EP\d+|Episode\s*\d+)\b', '', title, flags=re.IGNORECASE)
        
        # 3단계: 시즌 표기 제거
        title = re.sub(r'\b(?:S\d+|Season\s*\d+)\b', '', title, flags=re.IGNORECASE)
        
        # 4단계: 날짜 제거
        title = re.sub(r'\b\d{6,8}\b', '', title)
        
        # 5단계: 기술 정보 제거
        title = self._remove_technical_info_cached(title)
        
        # 6단계: 최종 정리
        title = title.strip()
        title = re.sub(r'\s+', ' ', title)
        
        return title
    
    @lru_cache(maxsize=64)
    def _remove_technical_info_cached(self, title: str) -> str:
        """기술적 정보 제거 (캐시됨)"""
        # 코덱 정보
        codecs = ['x264', 'x265', 'H.264', 'H.265', 'AVC', 'HEVC', 'DivX', 'XviD']
        for codec in codecs:
            title = re.sub(rf'\b{codec}\b', '', title, flags=re.IGNORECASE)
        
        # 오디오 정보
        audio_patterns = [
            r'\bAAC\b', r'\bAC3\b', r'\bMP3\b', r'\bFLAC\b', r'\bDTS\b',
            r'\b\d+ch\b', r'\b\d+\.\d+ch\b'
        ]
        for pattern in audio_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # 품질 정보
        quality_patterns = [
            r'\b(?:WEB-DL|BluRay|DVDRip|TVRip|HDTV|PDTV)\b',
            r'\b(?:RAW|SUB|DUB|UNCUT|EXTENDED|DIRECTOR\'S CUT)\b'
        ]
        for pattern in quality_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # 언어 정보
        language_patterns = [
            r'\b(?:KOR|JPN|ENG|CHI|GER|FRE|SPA|ITA|RUS)\b',
            r'\b(?:Korean|Japanese|English|Chinese|German|French|Spanish|Italian|Russian)\b'
        ]
        for pattern in language_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        return title
    
    # 기존 메서드들 (하위 호환성을 위해 유지)
    def _extract_resolution(self, text: str) -> Optional[str]:
        """텍스트에서 해상도 추출 (기존 메서드)"""
        return self._extract_resolution_cached(text)
    
    def _clean_title(self, title: str) -> str:
        """제목에서 불필요한 정보 제거 (기존 메서드)"""
        return self._clean_title_cached(title)
    
    def _remove_technical_info(self, title: str) -> str:
        """기술적 정보 제거 (기존 메서드)"""
        return self._remove_technical_info_cached(title)
    
    def get_supported_formats(self) -> List[str]:
        """지원되는 파일 형식 반환"""
        return ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.webm', '.srt', '.ass', '.ssa', '.sub', '.idx', '.smi', '.vtt']
    
    def is_video_file(self, filename: str) -> bool:
        """비디오 파일 여부 확인"""
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.webm']
        return any(filename.lower().endswith(ext) for ext in video_extensions)
    
    def get_parsing_stats(self, results: List[ParsedMetadata]) -> Dict[str, any]:
        """파싱 통계 반환"""
        if not results:
            return {}
        
        total_files = len(results)
        successful_parses = len([r for r in results if r.confidence > 0])
        average_confidence = sum(r.confidence for r in results) / total_files if total_files > 0 else 0
        
        return {
            'total_files': total_files,
            'successful_parses': successful_parses,
            'success_rate': successful_parses / total_files if total_files > 0 else 0,
            'average_confidence': average_confidence,
            'confidence_distribution': {
                'high': len([r for r in results if r.confidence >= 0.8]),
                'medium': len([r for r in results if 0.5 <= r.confidence < 0.8]),
                'low': len([r for r in results if r.confidence < 0.5])
            }
        }
    
    def clear_cache(self):
        """캐시를 모두 지웁니다 (메모리 관리용)"""
        self.parse_filename.cache_clear()
        self._improved_fallback_parse.cache_clear()
        self._extract_resolution_cached.cache_clear()
        self._clean_title_cached.cache_clear()
        self._remove_technical_info_cached.cache_clear()
    
    def get_cache_info(self) -> Dict[str, int]:
        """캐시 정보를 반환합니다"""
        parse_cache_info = self.parse_filename.cache_info()
        fallback_cache_info = self._improved_fallback_parse.cache_info()
        resolution_cache_info = self._extract_resolution_cached.cache_info()
        title_cache_info = self._clean_title_cached.cache_info()
        tech_cache_info = self._remove_technical_info_cached.cache_info()
        
        return {
            'parse_filename_cache_size': parse_cache_info.currsize,
            'parse_filename_cache_hits': parse_cache_info.hits,
            'parse_filename_cache_misses': parse_cache_info.misses,
            'fallback_parse_cache_size': fallback_cache_info.currsize,
            'resolution_cache_size': resolution_cache_info.currsize,
            'title_clean_cache_size': title_cache_info.currsize,
            'technical_info_cache_size': tech_cache_info.currsize
        }
