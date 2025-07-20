"""
파일명 정제 및 메타데이터 추출 모듈

Anitopy와 GuessIt을 사용하여 애니메이션 파일명에서 메타데이터를 추출하고
정제된 제목을 생성하는 기능을 제공합니다.
"""

import re
import logging
import time
from pathlib import Path
from typing import Union, Optional, Dict, Any
from dataclasses import dataclass
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from datetime import datetime

try:
    import anitopy
except ImportError:
    anitopy = None
    logging.getLogger("animesorter.file_cleaner").warning("Anitopy not available")

try:
    from guessit import guessit
except ImportError:
    guessit = None
    logging.getLogger("animesorter.file_cleaner").warning("GuessIt not available")


@dataclass
class CleanResult:
    """정제 결과 데이터 클래스"""
    title: str
    original_filename: Optional[Union[str, Path]] = None
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_end: Optional[int] = None
    quality: Optional[str] = None
    resolution: Optional[str] = None
    audio_codec: Optional[str] = None
    video_codec: Optional[str] = None
    release_group: Optional[str] = None
    language: Optional[str] = None
    subtitles: Optional[str] = None
    is_anime: bool = True
    special_episode: Optional[str] = None
    multi_episode: Optional[str] = None
    korean_season: Optional[str] = None
    korean_episode: Optional[str] = None
    is_movie: bool = False
    extra_info: Optional[Dict[str, Any]] = None


class FileCleaner:
    """파일명 정제 및 메타데이터 추출 클래스"""
    
    # 성능 최적화 상수
    PARSING_TIMEOUT = 5.0  # 파싱 타임아웃 (초)
    MAX_REGEX_ITERATIONS = 10  # 최대 정규식 반복 횟수
    
    def __init__(self):
        """FileCleaner 초기화"""
        self.logger = logging.getLogger("animesorter.file_cleaner")
        self.logger.setLevel(logging.DEBUG)  # 디버그 레벨 설정
        self._executor = ThreadPoolExecutor(max_workers=2)
        
    def __del__(self):
        """소멸자에서 리소스 정리"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
    
    @staticmethod
    def clean_filename(file_path: Union[str, Path], *, include_file_info: bool = False) -> CleanResult:
        """
        파일명 정제 (통합된 정적 메서드)
        
        Args:
            file_path: 파일 경로 또는 제목 문자열
            include_file_info: 파일 정보 포함 여부 (기본값: False)
            
        Returns:
            CleanResult: 정제된 결과
        """
        cleaner = FileCleaner()
        try:
            # 파일 경로인 경우 전체 파싱
            if isinstance(file_path, (str, Path)) and Path(file_path).exists():
                result = cleaner.parse(file_path)
                
                # 파일 정보 추가 (요청된 경우)
                if include_file_info:
                    result = cleaner._add_file_info(result, Path(file_path))
                
                return result
            else:
                # 문자열인 경우 제목만 정제
                return cleaner._clean_title_only(str(file_path))
        finally:
            cleaner.__del__()
    
    def _add_file_info(self, result: CleanResult, file_path: Path) -> CleanResult:
        """
        파일 정보를 결과에 추가
        
        Args:
            result: CleanResult 객체
            file_path: 파일 경로
            
        Returns:
            CleanResult: 파일 정보가 추가된 결과
        """
        try:
            stat_info = file_path.stat()
            if result.extra_info is None:
                result.extra_info = {}
            result.extra_info.update({
                'file_size': stat_info.st_size,
                'last_modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            })
        except (OSError, FileNotFoundError):
            if result.extra_info is None:
                result.extra_info = {}
            result.extra_info.update({
                'file_size': 0,
                'last_modified': datetime.now().isoformat()
            })
        return result
    
    def _clean_title_only(self, title: str) -> CleanResult:
        """
        제목만 정제 (파일 경로가 아닌 경우)
        
        Args:
            title: 정제할 제목 문자열
            
        Returns:
            CleanResult: 정제된 결과
        """
        result = self._pre_clean_filename(title)
        result = self._normalize_korean_tokens(result)
        result = self._post_clean_title(result)
        
        return CleanResult(
            title=result,
            original_filename=title,
            is_anime=True
        )
    
    # 기존 clean_filename_static 함수는 하위 호환성을 위해 유지하되 내부적으로 clean_filename 호출
    @staticmethod
    def clean_filename_static(file_path: Union[str, Path]) -> CleanResult:
        """
        파일명 정제 (정적 메서드, 하위 호환성용)
        
        Args:
            file_path: 파일 경로 또는 제목 문자열
            
        Returns:
            CleanResult: 정제된 결과
        """
        return FileCleaner.clean_filename(file_path, include_file_info=True)
    
    def parse(self, file_path: Union[str, Path], *, strict: bool = False) -> CleanResult:
        """
        파일명 파싱 및 정제 (상세한 디버그 로그 포함)
        
        Args:
            file_path: 파일 경로
            strict: 엄격한 모드 (기본값: False)
            
        Returns:
            CleanResult: 정제된 결과
        """
        parse_start = time.time()
        
        # Path 객체로 변환
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        filename = file_path.name
        self.logger.info(f"🔧 [CLEANER] Starting filename parsing: {filename}")
        
        try:
            # 1단계: Anitopy 파싱
            self.logger.debug(f"📋 [CLEANER] Step 1: Anitopy parsing for '{filename}'")
            anitopy_start = time.time()
            
            anitopy_result = self._parse_with_anitopy(filename)
            
            anitopy_elapsed = time.time() - anitopy_start
            self.logger.debug(f"✅ [CLEANER] Anitopy parsing completed in {anitopy_elapsed:.3f}s")
            
            if anitopy_result:
                self.logger.debug(f"📊 [CLEANER] Anitopy found {len(anitopy_result)} fields")
            else:
                self.logger.debug("📊 [CLEANER] Anitopy found 0 fields")
            
            # 2단계: GuessIt 파싱 (폴백)
            self.logger.debug(f"📋 [CLEANER] Step 2: GuessIt parsing for '{filename}'")
            guessit_start = time.time()
            
            guessit_result = self._parse_with_guessit(filename)
            
            guessit_elapsed = time.time() - guessit_start
            self.logger.debug(f"✅ [CLEANER] GuessIt parsing completed in {guessit_elapsed:.3f}s")
            
            if guessit_result:
                self.logger.debug(f"📊 [CLEANER] GuessIt found {len(guessit_result)} fields")
            else:
                self.logger.debug("📊 [CLEANER] GuessIt found 0 fields")
            
            # 3단계: 결과 병합 및 정규화
            self.logger.debug(f"🔄 [CLEANER] Step 3: Merging and normalizing results")
            merge_start = time.time()
            
            # 결과 병합 (Anitopy 우선, GuessIt으로 보완)
            merged_result = {}
            if anitopy_result:
                merged_result.update(anitopy_result)
            if guessit_result:
                # GuessIt 결과로 누락된 필드 보완
                for key, value in guessit_result.items():
                    if key not in merged_result or not merged_result[key]:
                        merged_result[key] = value
            
            merge_elapsed = time.time() - merge_start
            self.logger.debug(f"✅ [CLEANER] Result merging completed in {merge_elapsed:.3f}s")
            
            # 4단계: 메타데이터 정규화
            self.logger.debug(f"🔧 [CLEANER] Step 4: Normalizing metadata")
            normalize_start = time.time()
            
            # 기본 필드 추출
            title = merged_result.get('anime_title', '') or merged_result.get('title', '')
            year = merged_result.get('anime_year') or merged_result.get('year')
            season = merged_result.get('anime_season') or merged_result.get('season')
            episode = merged_result.get('episode_number') or merged_result.get('episode')
            episode_end = merged_result.get('episode_number_end')
            quality = merged_result.get('video_resolution') or merged_result.get('quality')
            resolution = merged_result.get('video_resolution')
            audio_codec = merged_result.get('audio_codec')
            video_codec = merged_result.get('video_codec')
            release_group = merged_result.get('release_group')
            language = merged_result.get('language')
            subtitles = merged_result.get('subtitles')
            
            normalize_elapsed = time.time() - normalize_start
            self.logger.debug(f"✅ [CLEANER] Metadata normalization completed in {normalize_elapsed:.3f}s")
            
            # 5단계: 제목 정제
            self.logger.debug(f"🧹 [CLEANER] Step 5: Cleaning title")
            clean_start = time.time()
            
            if title:
                # 제목 전처리
                title = self._pre_clean_filename(title)
                
                # 콘텐츠 타입 분류
                is_anime, content_type = self._classify_content_type(filename)
                
                # 한국어 토큰 정규화
                title = self._normalize_korean_tokens(title)
                
                # 제목 후처리
                title = self._post_clean_title(title)
                
                # 특수 에피소드 정보 추출
                special_episode = self._extract_special_episode_info(filename)
                multi_episode = self._extract_multi_episode_info(filename)
                korean_season = self._extract_korean_season_info(filename)
                korean_episode = self._extract_korean_episode_info(filename)
                
                # 영화 여부 판단
                is_movie = self._is_movie_file(filename)
                
                # 추가 정보 수집
                extra_info = {
                    'anitopy_result': anitopy_result,
                    'guessit_result': guessit_result,
                    'merged_result': merged_result,
                    'content_type': content_type
                }
            else:
                # 제목이 없는 경우 파일명에서 추출
                title = file_path.stem
                title = self._pre_clean_filename(title)
                is_anime, content_type = self._classify_content_type(filename)
                title = self._normalize_korean_tokens(title)
                title = self._post_clean_title(title)
                special_episode = None
                multi_episode = None
                korean_season = None
                korean_episode = None
                is_movie = self._is_movie_file(filename)
                
                # 추가 정보 수집
                extra_info = {
                    'anitopy_result': anitopy_result,
                    'guessit_result': guessit_result,
                    'merged_result': merged_result,
                    'content_type': content_type
                }
            
            clean_elapsed = time.time() - clean_start
            self.logger.debug(f"✅ [CLEANER] Title cleaning completed in {clean_elapsed:.3f}s")
            
            # 6단계: 결과 생성
            self.logger.debug(f"📝 [CLEANER] Step 6: Creating final result")
            
            result = CleanResult(
                title=title,
                original_filename=file_path,
                year=year,
                season=season,
                episode=episode,
                episode_end=episode_end,
                quality=quality,
                resolution=resolution,
                audio_codec=audio_codec,
                video_codec=video_codec,
                release_group=release_group,
                language=language,
                subtitles=subtitles,
                is_anime=is_anime,
                special_episode=special_episode,
                multi_episode=multi_episode,
                korean_season=korean_season,
                korean_episode=korean_episode,
                is_movie=is_movie,
                extra_info=extra_info
            )
            
            total_elapsed = time.time() - parse_start
            self.logger.info(f"✅ [CLEANER] Filename parsing completed in {total_elapsed:.3f}s")
            self.logger.info(f"📝 [CLEANER] Final result: '{result.title}' (anime: {result.is_anime}, year: {result.year})")
            
            return result
            
        except Exception as e:
            total_elapsed = time.time() - parse_start
            self.logger.error(f"❌ [CLEANER] Filename parsing failed after {total_elapsed:.3f}s: {e}")
            
            # 에러 시 기본 결과 반환
            return CleanResult(
                title=file_path.stem,
                original_filename=file_path,
                is_anime=True,
                is_movie=False,
                extra_info={'error': str(e)}
            )
    
    def _parse_with_anitopy(self, filename: str) -> Optional[Dict[str, Any]]:
        """Anitopy를 사용한 파싱 (타임아웃 적용)"""
        if not anitopy:
            self.logger.debug("⚠️ [CLEANER] Anitopy not available, skipping")
            return None
        
        try:
            self.logger.debug(f"🔍 [CLEANER] Anitopy parsing: {filename}")
            
            # 동기적으로 직접 호출 (이벤트 루프 충돌 방지)
            result = anitopy.parse(filename)
            
            self.logger.debug(f"✅ [CLEANER] Anitopy parsing successful: {len(result) if result else 0} fields")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Anitopy parsing error for {filename}: {e}")
            return None
    
    def _parse_with_guessit(self, filename: str) -> Dict[str, Any]:
        """GuessIt을 사용한 파싱 (타임아웃 적용)"""
        if not guessit:
            self.logger.debug("⚠️ [CLEANER] GuessIt not available, using fallback")
            return {}
        
        try:
            self.logger.debug(f"🔍 [CLEANER] GuessIt parsing: {filename}")
            
            # 동기적으로 직접 호출 (이벤트 루프 충돌 방지)
            result = guessit(filename)
            
            # GuessIt 결과를 딕셔너리로 변환
            result_dict = {}
            if result:
                for key, value in result.items():
                    if value is not None:
                        result_dict[str(key)] = value
            
            self.logger.debug(f"✅ [CLEANER] GuessIt parsing successful: {len(result_dict)} fields")
            return result_dict
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] GuessIt parsing error for {filename}: {e}")
            return {}
    
    @staticmethod
    def _safe_regex_sub(pattern: str, repl: str, string: str, flags: int = 0, max_iterations: int = 10) -> str:
        """안전한 정규식 치환 (무한 루프 방지)"""
        try:
            result = string
            iterations = 0
            while iterations < max_iterations:
                new_result = re.sub(pattern, repl, result, flags=flags)
                if new_result == result:
                    break
                result = new_result
                iterations += 1
            
            if iterations >= max_iterations:
                logging.getLogger("animesorter.file_cleaner").warning(
                    f"⚠️ [CLEANER] Regex substitution reached max iterations for pattern: {pattern}"
                )
            
            return result
        except Exception as e:
            logging.getLogger("animesorter.file_cleaner").error(
                f"❌ [CLEANER] Regex substitution failed for pattern {pattern}: {e}"
            )
            return string
    
    def _pre_clean_filename(self, filename: str) -> str:
        """파일명 전처리 (상세한 디버그 로그 포함)"""
        self.logger.debug(f"🧹 [CLEANER] Pre-cleaning filename: '{filename}'")
        clean_start = time.time()
        
        try:
            result = filename
            
            # 릴리즈 그룹 제거
            self.logger.debug("🧹 [CLEANER] Removing release groups...")
            release_patterns = [
                r'\[[^\]]*\]',  # 대괄호로 둘러싸인 모든 것
                r'\([^)]*\)',   # 소괄호로 둘러싸인 모든 것
                r'-[A-Za-z0-9]+$',  # 끝에 붙은 릴리즈 그룹
            ]
            
            for pattern in release_patterns:
                result = self._safe_regex_sub(pattern, '', result)
            
            # 해상도 제거
            self.logger.debug("🧹 [CLEANER] Removing resolution...")
            resolution_patterns = [
                r'\b\d{3,4}p\b',
                r'\bHD\b',
                r'\bSD\b',
                r'\bFHD\b',
                r'\bUHD\b',
                r'\b4K\b',
                r'\b1080p\b',
                r'\b720p\b',
                r'\b480p\b',
            ]
            
            for pattern in resolution_patterns:
                result = self._safe_regex_sub(pattern, '', result, flags=re.IGNORECASE)
            
            # 코덱 제거
            self.logger.debug("🧹 [CLEANER] Removing codecs...")
            codec_patterns = [
                r'\bH\.264\b',
                r'\bH\.265\b',
                r'\bHEVC\b',
                r'\bAVC\b',
                r'\bAAC\b',
                r'\bAC3\b',
                r'\bFLAC\b',
                r'\bMP3\b',
                r'\bOPUS\b',
            ]
            
            for pattern in codec_patterns:
                result = self._safe_regex_sub(pattern, '', result, flags=re.IGNORECASE)
            
            # 품질 제거
            self.logger.debug("🧹 [CLEANER] Removing quality indicators...")
            quality_patterns = [
                r'\bHigh\b',
                r'\bLow\b',
                r'\bMedium\b',
                r'\bWEB-DL\b',
                r'\bBluRay\b',
                r'\bBRRip\b',
                r'\bHDRip\b',
                r'\bDVDRip\b',
            ]
            
            for pattern in quality_patterns:
                result = self._safe_regex_sub(pattern, '', result, flags=re.IGNORECASE)
            
            # 언어 제거
            self.logger.debug("🧹 [CLEANER] Removing language indicators...")
            language_patterns = [
                r'\bKOR\b',
                r'\bENG\b',
                r'\bJPN\b',
                r'\bCHI\b',
                r'\bKorean\b',
                r'\bEnglish\b',
                r'\bJapanese\b',
                r'\bChinese\b',
            ]
            
            for pattern in language_patterns:
                result = self._safe_regex_sub(pattern, '', result, flags=re.IGNORECASE)
            
            # 메타데이터 패턴 제거
            self.logger.debug("🧹 [CLEANER] Removing metadata patterns...")
            metadata_patterns = [
                r'\bSubbed\b',
                r'\bDubbed\b',
                r'\bUncensored\b',
                r'\bCensored\b',
                r'\bComplete\b',
                r'\bSeason\b',
                r'\bEpisode\b',
                r'\bOVA\b',
                r'\bMovie\b',
                r'\bSpecial\b',
            ]
            
            for pattern in metadata_patterns:
                result = self._safe_regex_sub(pattern, '', result, flags=re.IGNORECASE)
            
            # 연속된 공백 정리
            result = self._safe_regex_sub(r'\s+', ' ', result)
            
            # 앞뒤 공백 제거
            result = result.strip()
            
            clean_elapsed = time.time() - clean_start
            self.logger.debug(f"✅ [CLEANER] Pre-cleaning completed in {clean_elapsed:.3f}s")
            self.logger.debug(f"📝 [CLEANER] Pre-cleaned result: '{result}'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Pre-cleaning error: {e}")
            return filename
    
    def _classify_content_type(self, filename: str) -> tuple[bool, str]:
        """콘텐츠 타입 분류 (애니메 vs 드라마)"""
        self.logger.debug(f"🏷️ [CLEANER] Classifying content type for: {filename}")
        
        try:
            # 애니메 키워드
            anime_keywords = [
                'anime', '애니', '애니메', 'cartoon', 'animation',
                'japan', 'japanese', '일본', 'manga', '만화'
            ]
            
            # 드라마 키워드
            drama_keywords = [
                'drama', '드라마', 'series', '시리즈', 'tv', 'television',
                'korea', 'korean', '한국', 'k-drama', '케이드라마'
            ]
            
            filename_lower = filename.lower()
            
            anime_count = sum(1 for keyword in anime_keywords if keyword in filename_lower)
            drama_count = sum(1 for keyword in drama_keywords if keyword in filename_lower)
            
            is_anime = anime_count >= drama_count
            content_type = "anime" if is_anime else "drama"
            
            self.logger.debug(f"🏷️ [CLEANER] Content classification: {content_type} (anime: {anime_count}, drama: {drama_count})")
            
            return is_anime, content_type
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Content classification error: {e}")
            return True, "anime"  # 기본값
    
    def _normalize_korean_tokens(self, filename: str) -> str:
        """한국어 토큰 정규화"""
        self.logger.debug(f"🇰🇷 [CLEANER] Normalizing Korean tokens: '{filename}'")
        
        try:
            result = filename
            
            # 한국어 시즌/에피소드 패턴 정규화
            korean_patterns = [
                (r'시즌\s*(\d+)', r'Season \1'),
                (r'에피소드\s*(\d+)', r'Episode \1'),
                (r'(\d+)화', r'Episode \1'),
                (r'(\d+)회', r'Episode \1'),
            ]
            
            for pattern, replacement in korean_patterns:
                result = self._safe_regex_sub(pattern, replacement, result)
            
            self.logger.debug(f"🇰🇷 [CLEANER] Korean normalization result: '{result}'")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Korean normalization error: {e}")
            return filename
    
    def _post_clean_title(self, title: str) -> str:
        """제목 후처리"""
        self.logger.debug(f"🧹 [CLEANER] Post-cleaning title: '{title}'")
        
        try:
            result = title
            
            # 메타데이터 패턴 제거
            metadata_patterns = [
                r'\b\d{4}\b',  # 연도
                r'\bSeason\s*\d+\b',
                r'\bEpisode\s*\d+\b',
                r'\bPart\s*\d+\b',
                r'\bVol\s*\d+\b',
            ]
            
            for pattern in metadata_patterns:
                result = self._safe_regex_sub(pattern, '', result)
            
            # 연속된 공백 정리
            result = self._safe_regex_sub(r'\s+', ' ', result)
            
            # 앞뒤 공백 제거
            result = result.strip()
            
            # 빈 문자열 처리
            if not result:
                result = "Unknown Title"
            
            self.logger.debug(f"🧹 [CLEANER] Post-cleaning result: '{result}'")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Post-cleaning error: {e}")
            return title
    
    def _extract_special_episode_info(self, filename: str) -> Optional[str]:
        """특수 에피소드 정보 추출 (개선된 버전)"""
        try:
            # 특집(SP) 패턴들 (TMDB Season 0으로 분류)
            special_patterns = [
                r'\bSP\d*\b',  # SP, SP1, SP2 등
                r'\bSpecial\b',
                r'\bOVA\b',
                r'\bOAV\b',
                r'\bMovie\b',
                r'\bExtra\b',
                r'\bBonus\b',
                r'\b특집\b',
                r'\b스페셜\b',
                r'\b영화\b',
                r'\b추가\b',
                r'\b보너스\b',
                r'\bS(?P<season>\d{1,2})SP(?P<sp>\d{1,2})\b',  # S01SP01 형태
                r'\bEpisode\s*0\b',  # Episode 0
                r'\bE0\b',  # E0
            ]
            
            for pattern in special_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    special_type = match.group()
                    self.logger.debug(f"🎬 [CLEANER] Special episode detected: '{special_type}' in '{filename}'")
                    return special_type
            
            return None
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Special episode extraction error: {e}")
            return None
    
    def _extract_multi_episode_info(self, filename: str) -> Optional[str]:
        """다중 에피소드 정보 추출"""
        try:
            multi_patterns = [
                r'(\d+)-(\d+)',  # 1-12
                r'(\d+)~(\d+)',  # 1~12
                r'(\d+)_(\d+)',  # 1_12
            ]
            
            for pattern in multi_patterns:
                match = re.search(pattern, filename)
                if match:
                    return f"{match.group(1)}-{match.group(2)}"
            
            return None
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Multi-episode extraction error: {e}")
            return None
    
    def _extract_korean_season_info(self, filename: str) -> Optional[str]:
        """한국어 시즌 정보 추출"""
        try:
            season_patterns = [
                r'시즌\s*(\d+)',
                r'Season\s*(\d+)',
                r'S(\d+)',
            ]
            
            for pattern in season_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Korean season extraction error: {e}")
            return None
    
    def _extract_korean_episode_info(self, filename: str) -> Optional[str]:
        """한국어 에피소드 정보 추출"""
        try:
            episode_patterns = [
                r'에피소드\s*(\d+)',
                r'Episode\s*(\d+)',
                r'E(\d+)',
                r'(\d+)화',
                r'(\d+)회',
            ]
            
            for pattern in episode_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Korean episode extraction error: {e}")
            return None
    
    def _is_movie_file(self, filename: str) -> bool:
        """영화 파일 여부 판단"""
        try:
            movie_keywords = [
                'movie', '영화', 'theatrical', 'cinema', 'film',
                'ova', 'oav', 'special', 'extra', 'bonus'
            ]
            
            filename_lower = filename.lower()
            
            # 영화 관련 키워드가 있으면 영화로 판단
            for keyword in movie_keywords:
                if keyword in filename_lower:
                    return True
            
            # 에피소드 번호가 없으면 영화로 판단
            episode_patterns = [
                r'\bE\d+\b',
                r'\bEpisode\s*\d+\b',
                r'\b\d+화\b',
                r'\b\d+회\b',
            ]
            
            for pattern in episode_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    return False  # 에피소드가 있으면 영화가 아님
            
            return True  # 에피소드가 없으면 영화로 판단
            
        except Exception as e:
            self.logger.error(f"❌ [CLEANER] Movie detection error: {e}")
            return False 