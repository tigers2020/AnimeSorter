import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Pattern
from guessit import guessit

@dataclass
class CleanResult:
    """
    파일명 정제 결과를 저장하는 데이터 클래스
    """
    title: str                 # 정제된 제목 (검색용)
    original_filename: Path     # 원본 파일명
    season: int = 1            # 시즌 번호 (기본값: 1)
    episode: Optional[int] = None  # 에피소드 번호
    year: Optional[int] = None     # 연도
    is_movie: bool = False      # 영화 여부
    extra_info: dict = field(default_factory=dict)  # 추가 정보

# FileCleaner: 모든 메서드는 입력→출력만 사용하는 순수 함수형 구현입니다.
# 내부에 전역 변수, 클래스 변수, 파일 핸들, DB 커넥션 등 공유 상태를 사용하지 않으므로
# 멀티스레드(ThreadPoolExecutor 등) 환경에서 안전하게 호출할 수 있습니다.
class FileCleaner:
    """
    파일명 정제 유틸리티
    """
    def __init__(self, config):
        self.config = config
        self._compile_patterns()

    def _compile_patterns(self):
        self.season_episode_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.get("filename_cleaner.season_episode_patterns", [
                r'S(\d{1,2})E(\d{1,3})',
                r'(?:시즌|Season)[\s.]*(\d{1,2})[\s.]*(?:에피소드|Episode)[\s.]*(\d{1,3})',
                r'(?<![A-Za-z0-9])(\d{1,2})[xX](\d{2,3})(?![A-Za-z0-9])',
                r'제\s*(\d{1,2})-(\d{1,2})화',
                r'제\s*(\d{1,2})화',
                r'[Cc][Dd](\d{1,2})',
            ])
        ]
        self.episode_only_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.get("filename_cleaner.episode_only_patterns", [
                r'(?<![A-Za-z0-9])EP[. ]?(\d{1,3})(?![A-Za-z0-9])',
                r'(?:에피소드|Episode)[\s.]*(\d{1,3})(?![A-Za-z0-9])',
                r'(?<![A-Za-z0-9])E(\d{1,3})(?![A-Za-z0-9])',
                r'제\s*(\d{1,3})화',
                r'[\s._-](\d{2,3})(?=[\s._-]|$)',
                r'[\s._-](\d{2,3})(?=\s*\[)',
                r'[\[\(](\d{2,3})[\]\)]',
                r'(?<![A-Za-z0-9])(\d{2,3})(?![A-Za-z0-9])',
            ])
        ]
        self.remove_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.get("filename_cleaner.remove_patterns", [
                r'\[([^]]*?(?:Raws|Sub|ASW|HEVC)[^]]*?)\]',
                r'\[([^]]+)\]',
                r'\([^)]*\)',
                r'\d{3,4}[pP]',
                r'\d+x\d+',
                r'[BH]D',
                r'(?:H|x|X)\.?26[45]',
                r'HEVC',
                r'[xX][vV][iI][dD]',
                r'10bit',
                r'8bit',
                r'AC3[\s._-]*(?:2ch|5\.1|2\.0)',
                r'AAC(?:\d?\.?\d)?',
                r'MP3',
                r'FLAC',
                r'DTS',
                r'(?:ASS|SSA|SRT)',
                r'(?:KOR|ENG|JAP|JPN|CHN)(?:[\s._-]|$)',
                r'BluRay',
                r'WEB-DL',
                r'HDTV',
                r'WEBRip',
                r'BDRip',
                r'DVDRip',
                r'CD\d{1,2}',
                r'TV(?=\s|$)',
                r'[\s._-]v\d(?=[\s._-]|$)',
                r'_T\d+$',
            ])
        ]
        self.year_pattern = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)')
        self.movie_keywords = ['movie', 'film', 'theatrical', 'ova', 'special']

    @staticmethod
    def refine_title(raw: str) -> str:
        ORDINAL = re.compile(r'\b\d+(?:st|nd|rd|th)\b', re.I)
        META_TOKENS = re.compile(r'\b(?:TV|WEB|BD(?:Rip)?|BluRay|OVA|ReRip)\b', re.I)
        txt = ORDINAL.sub('', raw)
        txt = META_TOKENS.sub('', txt)
        txt = re.sub(r'\s{2,}', ' ', txt)
        return txt.strip().title()

    @staticmethod
    def clean_filename_static(file_path):
        from guessit import guessit
        from pathlib import Path
        meta = guessit(Path(file_path).name)
        title = meta.get('title', '')
        clean_title = FileCleaner.refine_title(title)
        meta['clean_title'] = clean_title
        return meta

    def clean_filename(self, file_path: Path) -> CleanResult:
        """
        기존 인스턴스 메서드: 내부적으로 static 버전 호출
        """
        return FileCleaner.clean_filename_static(file_path) 

def clean_filename_mp(file_path):
    from guessit import guessit
    import re
    # 1차 guessit
    meta = guessit(file_path)
    # 2차 정제
    title = meta.get('title', '')
    ORDINAL = re.compile(r'\b\d+(?:st|nd|rd|th)\b', re.I)
    META_TOKENS = re.compile(r'\b(?:TV|WEB|BD(?:Rip)?|BluRay|OVA|ReRip)\b', re.I)
    txt = ORDINAL.sub('', title)
    txt = META_TOKENS.sub('', txt)
    txt = re.sub(r'\s{2,}', ' ', txt)
    clean_title = txt.strip().title()
    meta['clean_title'] = clean_title
    return meta 