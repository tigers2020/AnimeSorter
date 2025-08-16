"""
파일명 파싱 엔진 - AnimeSorter (개선된 버전)

다양한 명명 규칙의 애니메이션 파일명에서 메타데이터를 추출합니다.
"""

import re
import os
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path


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
    confidence: float = 0.0  # 파싱 신뢰도 (0.0 ~ 1.0)


class FileParser:
    """애니메이션 파일명 파싱 엔진"""
    
    def __init__(self):
        """파서 초기화"""
        self.patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> List[Tuple[re.Pattern, str, float]]:
        """파싱 패턴 컴파일 (패턴, 타입, 신뢰도)"""
        patterns = [
            # 패턴 1: [Group] Title - Episode (추가정보).ext
            # [Ohys-Raws] Itou Junji Collection - 10 (WOWOW 1280x720 x264 AAC).mp4
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s*\([^)]*(\d+x\d+|\d+p)[^)]*\)', re.IGNORECASE), 
             'group_title_episode_with_resolution', 0.9),
             
            # 패턴 2: [Group] Title - Episode (기타정보).ext  
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s*(?:\([^)]+\))?', re.IGNORECASE), 
             'group_title_episode', 0.8),
             
            # 패턴 3: Title - Episode [Resolution].ext
            # [HorribleSubs] Peter Grill to Kenja no Jikan - 03 [720p].smi
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s*\[([^\]]*(?:\d+p)[^\]]*)\]', re.IGNORECASE), 
             'group_title_episode_bracket_resolution', 0.9),
             
            # 패턴 4: Title Season Episode.ext (공백으로 구분)
            # GIRLS Bravo Second Season 13.smi
            (re.compile(r'^(.+?)\s+(?:Season\s*(\d+))?\s*(\d+)$', re.IGNORECASE), 
             'title_season_episode_space', 0.7),
             
            # 패턴 5: Title.S##E##.Resolution.codec.ext
            (re.compile(r'^(.+?)\.S(\d+)E(\d+)\.(\d+p)\.([^.]+)\.([^.]+)$', re.IGNORECASE), 
             'title_season_episode_resolution_dots', 0.9),
             
            # 패턴 5-1: Title.E## 형태 (Exx 표기)
            # 수속성의 마법사.E01.250705.1080p-NEXT.mp4
            (re.compile(r'^(.+?)\.E(\d+)', re.IGNORECASE), 
             'title_episode_exx', 0.9),
             
            # 패턴 5-2: Title.E##.Resolution 형태
            # 수속성의 마법사.E01.1080p.mp4
            (re.compile(r'^(.+?)\.E(\d+)\.(\d+p)', re.IGNORECASE), 
             'title_episode_exx_resolution', 0.9),
             
            # 패턴 5-3: Title.E##.Date.Resolution 형태
            # 수속성의 마법사.E01.250705.1080p.mp4
            (re.compile(r'^(.+?)\.E(\d+)\.(\d{6})\.(\d+p)', re.IGNORECASE), 
             'title_episode_exx_date_resolution', 0.9),
             
            # 패턴 6: Title - Episode화/話 형태
            # 기동전사 건담 AGE 30화 (1280x720 XviD).avi
            (re.compile(r'^(.+?)\s*(\d+)화?\s*(?:\([^)]*(\d+x\d+|\d+p)[^)]*\))?', re.IGNORECASE), 
             'title_episode_korean', 0.8),
             
            # 패턴 7: Title EP## 형태
            # Futakoi Alternative TV 2005 EP06 DVDRip 768x576 x264 AC3 2ch.avi
            (re.compile(r'^(.+?)\s+EP(\d+)', re.IGNORECASE), 
             'title_episode_ep', 0.8),
             
            # 패턴 8: [Group]Title Episode.ext (공백 없음)
            # [제블]나루토 349.avi
            (re.compile(r'^\[([^\]]+)\]([^-\s]+)\s*(\d+)', re.IGNORECASE), 
             'group_title_episode_nospace', 0.7),
             
            # 패턴 9: Title - Episode RAW/END 등
            # [Leopard-Raws] Tensei Shitara Slime Datta Ken - 02 RAW
            (re.compile(r'^\[([^\]]+)\]\s*(.+?)\s*-\s*(\d+)\s+(?:RAW|END)', re.IGNORECASE), 
             'group_title_episode_raw', 0.8),
             
            # 패턴 10: Title 第##話/第##화 형태
            # 機動新世紀ガンダムX 第15話 (480p).smi
            (re.compile(r'^(.+?)\s*第(\d+)話', re.IGNORECASE), 
             'title_episode_japanese', 0.8),
             
            # 패턴 11: 년도가 포함된 형태
            # Prince of Tennis TV 2001 R5 DVDRip x264 AC3 EP059.smi
            (re.compile(r'^(.+?)\s+(\d{4})\s+.*?EP(\d+)', re.IGNORECASE), 
             'title_year_episode', 0.7),
             
            # 패턴 12: 단순한 Title Episode 형태 (마지막 패턴)
            (re.compile(r'^(.+?)\s+(\d+)(?:\s|$)', re.IGNORECASE), 
             'title_episode_simple', 0.6),
        ]
        return patterns
        
    def parse_filename(self, filepath: str) -> Optional[ParsedMetadata]:
        """파일명 파싱"""
        if not filepath:
            return None
            
        # 파일명만 추출 (경로 제거)
        filename = os.path.basename(filepath)
        
        # 확장자 추출
        container = Path(filename).suffix.lstrip('.') if '.' in filename else None
        filename_without_ext = Path(filename).stem
        
        # 각 패턴으로 시도
        for pattern, pattern_type, base_confidence in self.patterns:
            match = pattern.match(filename_without_ext)
            if match:
                result = self._extract_metadata(match, pattern_type, filename_without_ext, container)
                result.confidence = base_confidence
                return result
                
        # 패턴 매칭 실패 시 개선된 fallback 파싱
        return self._improved_fallback_parse(filename_without_ext, container)
        
    def _extract_metadata(self, match: re.Match, pattern_type: str, filename: str, container: Optional[str] = None) -> ParsedMetadata:
        """매치된 그룹에서 메타데이터 추출"""
        groups = match.groups()
        
        # 공통적으로 해상도와 기술정보 추출
        resolution = self._extract_resolution(filename)
        codec_info = self._extract_codec_info(filename)
        
        if pattern_type == 'group_title_episode_with_resolution':
            group, title, episode = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                group=group,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.9
            )
            
        elif pattern_type == 'group_title_episode':
            group, title, episode = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                group=group,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.8
            )
            
        elif pattern_type == 'group_title_episode_bracket_resolution':
            group, title, episode, res_info = groups[:4]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=self._extract_resolution_from_text(res_info) or resolution,
                group=group,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.9
            )
            
        elif pattern_type == 'title_season_episode_space':
            title, season, episode = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=int(season) if season else 1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.7
            )
            
        elif pattern_type == 'title_season_episode_resolution_dots':
            title, season, episode, res, video_codec, audio_codec = groups[:6]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=int(season) if season else 1,
                episode=int(episode) if episode else None,
                resolution=res,
                container=container,
                codec=video_codec,
                audio_codec=audio_codec,
                confidence=0.9
            )
            
        elif pattern_type == 'title_episode_exx':
            title, episode = groups[:2]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.9
            )
            
        elif pattern_type == 'title_episode_exx_resolution':
            title, episode, res = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=res,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.9
            )
            
        elif pattern_type == 'title_episode_exx_date_resolution':
            title, episode, date, res = groups[:4]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=res,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.9
            )
            
        elif pattern_type == 'title_episode_korean':
            title, episode, res_info = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=self._extract_resolution_from_text(res_info) if res_info else resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.8
            )
            
        elif pattern_type == 'title_episode_ep':
            title, episode = groups[:2]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.8
            )
            
        elif pattern_type == 'group_title_episode_nospace':
            group, title, episode = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                group=group,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.7
            )
            
        elif pattern_type == 'group_title_episode_raw':
            group, title, episode = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                group=group,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.8
            )
            
        elif pattern_type == 'title_episode_japanese':
            title, episode = groups[:2]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.8
            )
            
        elif pattern_type == 'title_year_episode':
            title, year, episode = groups[:3]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                year=int(year) if year else None,
                resolution=resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.7
            )
            
        elif pattern_type == 'title_episode_simple':
            title, episode = groups[:2]
            return ParsedMetadata(
                title=self._clean_title(title),
                season=1,
                episode=int(episode) if episode else None,
                resolution=resolution,
                container=container,
                codec=codec_info.get('video_codec'),
                audio_codec=codec_info.get('audio_codec'),
                confidence=0.6
            )
            
        # 기본 반환
        return ParsedMetadata(
            title=self._clean_title(filename),
            container=container,
            confidence=0.3
        )
        
    def _improved_fallback_parse(self, filename: str, container: Optional[str] = None) -> ParsedMetadata:
        """개선된 fallback 파싱"""
        # 해상도 추출
        resolution = self._extract_resolution(filename)
        
        # 에피소드 번호 추출 (더 정확한 패턴)
        episode = self._extract_episode_number(filename)
        
        # 그룹 정보 추출
        group = self._extract_group(filename)
        
        # 코덱 정보 추출
        codec_info = self._extract_codec_info(filename)
        
        return ParsedMetadata(
            title=self._clean_title(filename),
            season=1,
            episode=episode,
            resolution=resolution,
            group=group,
            container=container,
            codec=codec_info.get('video_codec'),
            audio_codec=codec_info.get('audio_codec'),
            confidence=0.4
        )
        
    def _extract_resolution(self, text: str) -> Optional[str]:
        """해상도 추출"""
        resolution_patterns = [
            r'(\d+p)',           # 720p, 1080p 등
            r'(\d+x\d+)',        # 1280x720 등
        ]
        
        for pattern in resolution_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
        
    def _extract_resolution_from_text(self, text: str) -> Optional[str]:
        """특정 텍스트에서 해상도 추출"""
        if not text:
            return None
        return self._extract_resolution(text)
        
    def _extract_episode_number(self, filename: str) -> Optional[int]:
        """에피소드 번호 추출 (개선된 버전)"""
        # 우선순위가 높은 패턴들
        episode_patterns = [
            r'제(\d+)화',                # 제05화
            r'第(\d+)話',                # 第15話
            r'(\d+)화',                  # 30화
            r'EP(\d+)',                  # EP06
            r'E(\d+)',                   # E01, E02 등 (Exx 형태)
            r'Episode\s*(\d+)',          # Episode 01
            r'-\s*(\d+)(?:\s|$|\[|\()',  # - 10 (뒤에 공백, 끝, [, ( 가 오는 경우)
            r'\s(\d+)(?:\s|$|\[|\()',    # 공백 + 숫자 + (공백/끝/[/()
        ]
        
        for pattern in episode_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                episode_num = int(match.group(1))
                # 너무 큰 숫자는 에피소드가 아닐 가능성이 높음
                if 1 <= episode_num <= 9999:
                    return episode_num
                    
        return None
        
    def _extract_group(self, filename: str) -> Optional[str]:
        """릴리즈 그룹 추출"""
        group_match = re.match(r'^\[([^\]]+)\]', filename)
        if group_match:
            return group_match.group(1)
        return None
        
    def _extract_codec_info(self, filename: str) -> Dict[str, Optional[str]]:
        """코덱 정보 추출"""
        video_codecs = ['x264', 'x265', 'H.264', 'H.265', 'HEVC', 'AVC', 'DivX', 'XviD']
        audio_codecs = ['AAC', 'AC3', 'DTS', 'MP3', 'FLAC', 'PCM']
        
        video_codec = None
        audio_codec = None
        
        filename_upper = filename.upper()
        
        for codec in video_codecs:
            if codec.upper() in filename_upper:
                video_codec = codec
                break
                
        for codec in audio_codecs:
            if codec.upper() in filename_upper:
                audio_codec = codec
                break
                
        return {
            'video_codec': video_codec,
            'audio_codec': audio_codec
        }
        
    def _clean_title(self, title: str) -> str:
        """제목 정제 - 개선된 버전"""
        if not title:
            return "Unknown Title"
            
        cleaned = title.strip()
        
        # 1단계: 릴리즈 그룹 제거
        cleaned = re.sub(r'^\[([^\]]+)\]\s*', '', cleaned)
        
        # 2단계: 기술적 정보가 포함된 부분 제거
        # 괄호 안의 기술 정보 제거 (해상도, 코덱 등이 포함된 경우)
        tech_patterns = [
            r'\([^)]*(?:\d+x\d+|\d+p|x264|x265|AAC|AC3|DTS)[^)]*\)',  # 기술정보 포함 괄호
            r'\([^)]*(?:RAW|END|WOWOW|BS11|AT-X|TBS|MX)[^)]*\)',      # 방송정보 포함 괄호
        ]
        
        for pattern in tech_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 3단계: 에피소드 번호 및 관련 정보 제거
        episode_patterns = [
            r'\s*-\s*\d+\s*$',          # 끝의 - 숫자
            r'\s*\d+\s*$',              # 끝의 숫자
            r'\s*EP\d+.*$',             # EP## 이후 모든 것
            r'\s*E\d+.*$',              # E## 이후 모든 것 (Exx 형태)
            r'\s*제\d+화.*$',            # 제##화 이후 모든 것
            r'\s*第\d+話.*$',            # 第##話 이후 모든 것
            r'\s*\d+화.*$',              # ##화 이후 모든 것
            r'\s+RAW$',                 # 끝의 RAW
            r'\s+END$',                 # 끝의 END
        ]
        
        for pattern in episode_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 4단계: 추가 기술 정보 제거
        cleaned = self._remove_technical_info(cleaned)
        
        # 5단계: 최종 정리
        cleaned = re.sub(r'[._]', ' ', cleaned)    # 점과 언더스코어를 공백으로
        cleaned = re.sub(r'\s+', ' ', cleaned)     # 연속 공백 정리
        cleaned = cleaned.strip(' -_')             # 앞뒤 공백, 대시, 언더스코어 제거
        
        # 빈 문자열 처리
        if len(cleaned.strip()) < 2:
            return "Unknown Title"
            
        return cleaned.strip()
        
    def _remove_technical_info(self, title: str) -> str:
        """기술적 정보 제거 (기존 메서드 유지)"""
        cleaned = title
        
        # 기술적 정보 패턴들
        tech_patterns = [
            # 해상도
            r'\b\d+x\d+\b', r'\b\d+p\b',
            # 코덱
            r'\bx264\b', r'\bx265\b', r'\bH\.264\b', r'\bH\.265\b', r'\bHEVC\b', 
            r'\bAVC\b', r'\bDivX\b', r'\bXviD\b',
            # 오디오
            r'\bAAC\b', r'\bAC3\b', r'\bDTS\b', r'\bMP3\b',
            # 품질/소스
            r'\bDVDRip\b', r'\bBDRip\b', r'\bHDRip\b', r'\bRAW\b', r'\bWEB-DL\b',
            # 방송국
            r'\bWOWOW\b', r'\bBS11\b', r'\bAT-X\b', r'\bTBS\b', r'\bMX\b',
            # 기타
            r'\bTV\b', r'\bR\d+\b', r'\bEP\d+\b', r'\b\d{4}\b',  # 년도
        ]
        
        for pattern in tech_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        return cleaned
        
    def get_supported_formats(self) -> List[str]:
        """지원되는 파일 형식 반환"""
        return ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.smi', '.ass']
        
    def is_video_file(self, filepath: str) -> bool:
        """비디오/자막 파일 여부 확인"""
        if not filepath:
            return False
            
        ext = Path(filepath).suffix.lower()
        return ext in self.get_supported_formats()
        
    def batch_parse(self, filepaths: List[str]) -> List[Tuple[str, Optional[ParsedMetadata]]]:
        """여러 파일 일괄 파싱"""
        results = []
        for filepath in filepaths:
            if self.is_video_file(filepath):
                metadata = self.parse_filename(filepath)
                results.append((filepath, metadata))
            else:
                results.append((filepath, None))
        return results
        
    def get_parsing_stats(self, results: List[Tuple[str, Optional[ParsedMetadata]]]) -> Dict:
        """파싱 통계 반환"""
        total = len(results)
        successful = sum(1 for _, metadata in results if metadata is not None)
        failed = total - successful
        
        if successful > 0:
            confidences = [metadata.confidence for _, metadata in results if metadata is not None]
            avg_confidence = sum(confidences) / len(confidences)
        else:
            avg_confidence = 0.0
        
        # 신뢰도별 분류
        high_confidence = sum(1 for _, metadata in results if metadata and metadata.confidence >= 0.8)
        medium_confidence = sum(1 for _, metadata in results if metadata and 0.5 <= metadata.confidence < 0.8)
        low_confidence = sum(1 for _, metadata in results if metadata and metadata.confidence < 0.5)
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'average_confidence': avg_confidence
        }
