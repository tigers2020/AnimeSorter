# AnimeSorter API 참조

## 📖 목차
1. [개요](#개요)
2. [핵심 모듈 API](#핵심-모듈-api)
3. [GUI 컴포넌트 API](#gui-컴포넌트-api)
4. [플러그인 API](#플러그인-api)
5. [데이터 모델](#데이터-모델)
6. [예외 처리](#예외-처리)
7. [설정 API](#설정-api)

## 🎯 개요

이 문서는 AnimeSorter의 모든 공개 API에 대한 상세한 참조 정보를 제공합니다. 각 클래스, 메서드, 속성에 대한 설명과 사용 예제를 포함합니다.

## 🔧 핵심 모듈 API

### FileParser

파일명 파싱을 담당하는 핵심 클래스입니다.

#### 클래스 정의
```python
class FileParser:
    """애니메이션 파일명 파싱 클래스"""
```

#### 생성자
```python
def __init__(self, patterns: Optional[List[str]] = None):
    """
    FileParser 초기화

    Args:
        patterns: 사용자 정의 파싱 패턴 리스트
    """
```

#### 주요 메서드

##### parse
```python
def parse(self, filename: str) -> Dict[str, Any]:
    """
    파일명에서 메타데이터를 추출합니다.

    Args:
        filename: 파싱할 파일명

    Returns:
        추출된 메타데이터 딕셔너리
        {
            'title': str,           # 애니메이션 제목
            'season': int,          # 시즌 번호
            'episode': int,         # 에피소드 번호
            'quality': str,         # 화질 정보
            'audio': str,           # 오디오 정보
            'subtitle': str,        # 자막 정보
            'group': str,           # 릴리즈 그룹
            'year': int,            # 제작년도
            'original_filename': str # 원본 파일명
        }

    Raises:
        ValueError: 파일명 형식이 올바르지 않은 경우
        FileNotFoundError: 파일이 존재하지 않는 경우
    """
```

**사용 예제**:
```python
parser = FileParser()
metadata = parser.parse("Attack on Titan S01E01 1080p.mkv")
print(metadata['title'])  # "Attack on Titan"
print(metadata['season'])  # 1
print(metadata['episode'])  # 1
print(metadata['quality'])  # "1080p"
```

##### extract_title
```python
def extract_title(self, filename: str) -> str:
    """
    파일명에서 제목을 추출합니다.

    Args:
        filename: 파일명

    Returns:
        추출된 제목
    """
```

##### extract_episode_info
```python
def extract_episode_info(self, filename: str) -> Tuple[int, int]:
    """
    파일명에서 시즌과 에피소드 정보를 추출합니다.

    Args:
        filename: 파일명

    Returns:
        (시즌 번호, 에피소드 번호) 튜플
    """
```

### TMDBClient

TMDB API와의 통신을 담당하는 클라이언트입니다.

#### 클래스 정의
```python
class TMDBClient:
    """TMDB API 클라이언트"""
```

#### 생성자
```python
def __init__(self, api_key: str, language: str = 'ko-KR'):
    """
    TMDBClient 초기화

    Args:
        api_key: TMDB API 키
        language: 검색 언어 (기본값: 'ko-KR')
    """
```

#### 주요 메서드

##### search_anime
```python
def search_anime(self, query: str, page: int = 1) -> List[Dict[str, Any]]:
    """
    TMDB에서 애니메이션을 검색합니다.

    Args:
        query: 검색어
        page: 페이지 번호 (기본값: 1)

    Returns:
        검색 결과 리스트
        [
            {
                'id': int,              # TMDB ID
                'title': str,           # 제목
                'original_title': str,  # 원제목
                'overview': str,        # 개요
                'poster_path': str,     # 포스터 경로
                'backdrop_path': str,   # 배경 이미지 경로
                'first_air_date': str,  # 첫 방영일
                'vote_average': float,  # 평점
                'media_type': str       # 미디어 타입
            },
            ...
        ]

    Raises:
        requests.RequestException: API 요청 실패
        ValueError: 잘못된 검색어
    """
```

**사용 예제**:
```python
client = TMDBClient("your_api_key")
results = client.search_anime("Attack on Titan")
for result in results:
    print(f"{result['title']} ({result['first_air_date']})")
```

##### get_details
```python
def get_details(self, tmdb_id: int) -> Dict[str, Any]:
    """
    TMDB ID로 상세 정보를 조회합니다.

    Args:
        tmdb_id: TMDB ID

    Returns:
        상세 정보 딕셔너리
    """
```

##### get_episodes
```python
def get_episodes(self, tmdb_id: int, season_number: int) -> List[Dict[str, Any]]:
    """
    특정 시즌의 에피소드 목록을 조회합니다.

    Args:
        tmdb_id: TMDB ID
        season_number: 시즌 번호

    Returns:
        에피소드 목록
    """
```

### FileManager

파일 관리 및 정리를 담당하는 클래스입니다.

#### 클래스 정의
```python
class FileManager:
    """파일 관리 및 정리 클래스"""
```

#### 생성자
```python
def __init__(self, destination_root: str = "", safe_mode: bool = True):
    """
    FileManager 초기화

    Args:
        destination_root: 대상 폴더 경로
        safe_mode: 안전 모드 활성화 여부
    """
```

#### 주요 메서드

##### organize_file
```python
def organize_file(self, source_path: str, metadata: Dict[str, Any],
                 operation: str = 'move') -> str:
    """
    파일을 정리합니다.

    Args:
        source_path: 원본 파일 경로
        metadata: 메타데이터
        operation: 작업 유형 ('move', 'copy', 'hardlink')

    Returns:
        정리된 파일의 새 경로

    Raises:
        FileNotFoundError: 원본 파일이 존재하지 않는 경우
        PermissionError: 권한 부족
        OSError: 파일 시스템 오류
    """
```

**사용 예제**:
```python
manager = FileManager("/path/to/destination")
new_path = manager.organize_file(
    "/path/to/source/Attack on Titan S01E01.mkv",
    {
        'title': 'Attack on Titan',
        'season': 1,
        'episode': 1
    },
    operation='move'
)
```

##### create_directory_structure
```python
def create_directory_structure(self, metadata: Dict[str, Any]) -> str:
    """
    메타데이터를 기반으로 디렉토리 구조를 생성합니다.

    Args:
        metadata: 메타데이터

    Returns:
        생성된 디렉토리 경로
    """
```

##### rename_file
```python
def rename_file(self, old_path: str, new_name: str) -> str:
    """
    파일명을 변경합니다.

    Args:
        old_path: 원본 파일 경로
        new_name: 새 파일명

    Returns:
        변경된 파일의 새 경로
    """
```

## 🖥️ GUI 컴포넌트 API

### MainWindow

메인 애플리케이션 윈도우입니다.

#### 클래스 정의
```python
class MainWindow(QMainWindow):
    """AnimeSorter 메인 윈도우"""
```

#### 주요 메서드

##### init_ui
```python
def init_ui(self):
    """UI 초기화"""
```

##### setup_connections
```python
def setup_connections(self):
    """시그널-슬롯 연결 설정"""
```

##### restore_session_state
```python
def restore_session_state(self):
    """이전 세션 상태 복원"""
```

### SettingsDialog

설정 편집 다이얼로그입니다.

#### 클래스 정의
```python
class SettingsDialog(QDialog):
    """설정 편집 다이얼로그"""
```

#### 시그널
```python
settingsChanged = pyqtSignal()  # 설정 변경 시그널
```

#### 주요 메서드

##### load_current_settings
```python
def load_current_settings(self):
    """현재 설정을 UI에 로드"""
```

##### save_settings
```python
def save_settings(self):
    """UI 설정을 저장"""
```

##### reset_to_defaults
```python
def reset_to_defaults(self):
    """기본값으로 초기화"""
```

## 🔌 플러그인 API

### MetadataProvider

메타데이터 제공자 플러그인의 기본 클래스입니다.

#### 클래스 정의
```python
class MetadataProvider(ABC):
    """메타데이터 제공자 기본 클래스"""
```

#### 추상 메서드

##### search
```python
@abstractmethod
def search(self, query: str) -> List[Dict[str, Any]]:
    """
    메타데이터를 검색합니다.

    Args:
        query: 검색어

    Returns:
        검색 결과 리스트
    """
```

##### get_details
```python
@abstractmethod
def get_details(self, item_id: str) -> Dict[str, Any]:
    """
    상세 정보를 조회합니다.

    Args:
        item_id: 아이템 ID

    Returns:
        상세 정보 딕셔너리
    """
```

#### 플러그인 구현 예제

```python
from src.plugins.base import MetadataProvider

class MyAnimeListProvider(MetadataProvider):
    """MyAnimeList 메타데이터 제공자"""

    def __init__(self):
        super().__init__()
        self.name = "MyAnimeList"
        self.version = "1.0.0"
        self.api_url = "https://api.myanimelist.net/v2"

    def search(self, query: str) -> List[Dict[str, Any]]:
        """MyAnimeList에서 검색"""
        # 구현 로직
        pass

    def get_details(self, item_id: str) -> Dict[str, Any]:
        """상세 정보 조회"""
        # 구현 로직
        pass
```

## 📊 데이터 모델

### ParsedItem

파싱된 파일 정보를 담는 데이터 클래스입니다.

```python
@dataclass
class ParsedItem:
    """파싱된 파일 정보"""
    file_path: str
    title: str
    season: int
    episode: int
    quality: str = ""
    audio: str = ""
    subtitle: str = ""
    group: str = ""
    year: Optional[int] = None
    original_filename: str = ""
    metadata: Optional[Dict[str, Any]] = None
```

### SearchResult

검색 결과를 담는 데이터 클래스입니다.

```python
@dataclass
class SearchResult:
    """검색 결과"""
    provider: str
    item_id: str
    title: str
    original_title: str = ""
    overview: str = ""
    poster_path: str = ""
    backdrop_path: str = ""
    first_air_date: str = ""
    vote_average: float = 0.0
    media_type: str = "tv"
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## ⚠️ 예외 처리

### AnimeSorterException

AnimeSorter의 기본 예외 클래스입니다.

```python
class AnimeSorterException(Exception):
    """AnimeSorter 기본 예외 클래스"""
    pass
```

### ParsingError

파싱 관련 오류를 나타내는 예외입니다.

```python
class ParsingError(AnimeSorterException):
    """파싱 오류"""
    pass
```

### TMDBError

TMDB API 관련 오류를 나타내는 예외입니다.

```python
class TMDBError(AnimeSorterException):
    """TMDB API 오류"""
    pass
```

### FileOperationError

파일 작업 관련 오류를 나타내는 예외입니다.

```python
class FileOperationError(AnimeSorterException):
    """파일 작업 오류"""
    pass
```

## ⚙️ 설정 API

### SettingsManager

애플리케이션 설정을 관리하는 클래스입니다.

#### 클래스 정의
```python
class SettingsManager:
    """설정 관리 클래스"""
```

#### 주요 메서드

##### get_setting
```python
def get_setting(self, key: str, default: Any = None) -> Any:
    """
    설정값을 조회합니다.

    Args:
        key: 설정 키
        default: 기본값

    Returns:
        설정값
    """
```

##### set_setting
```python
def set_setting(self, key: str, value: Any) -> None:
    """
    설정값을 저장합니다.

    Args:
        key: 설정 키
        value: 설정값
    """
```

##### save_settings
```python
def save_settings(self) -> None:
    """설정을 파일에 저장"""
```

##### load_settings
```python
def load_settings(self) -> None:
    """파일에서 설정을 로드"""
```

#### 기본 설정 항목

```python
DEFAULT_SETTINGS = {
    # TMDB 설정
    'tmdb_api_key': '',
    'tmdb_language': 'ko-KR',
    'tmdb_search_results': 10,

    # 파일 정리 설정
    'destination_root': '',
    'organize_mode': 'move',  # 'move', 'copy', 'hardlink'
    'naming_scheme': 'standard',  # 'standard', 'minimal', 'detailed'

    # 파싱 설정
    'file_extensions': ['.mp4', '.mkv', '.avi', '.mov'],
    'auto_detect_season': True,

    # 안전 모드 설정
    'safe_mode': True,
    'backup_location': '',
    'backup_retention_days': 30,

    # GUI 설정
    'remember_session': True,
    'window_geometry': '',
    'splitter_sizes': [],

    # 고급 설정
    'log_level': 'INFO',
    'cache_enabled': True,
    'cache_size': 100,
    'max_concurrent_requests': 5
}
```

## 📝 사용 예제

### 기본 사용법

```python
from src.core.file_parser import FileParser
from src.core.tmdb_client import TMDBClient
from src.core.file_manager import FileManager

# 컴포넌트 초기화
parser = FileParser()
client = TMDBClient("your_api_key")
manager = FileManager("/path/to/destination")

# 파일 파싱
metadata = parser.parse("Attack on Titan S01E01 1080p.mkv")

# TMDB 검색
results = client.search_anime(metadata['title'])

# 파일 정리
if results:
    selected_result = results[0]  # 첫 번째 결과 선택
    new_path = manager.organize_file(
        "Attack on Titan S01E01 1080p.mkv",
        {**metadata, 'tmdb_data': selected_result}
    )
```

### 플러그인 사용법

```python
from src.plugins.base import MetadataProvider

# 플러그인 등록
providers = [MyAnimeListProvider(), AniDBProvider()]

# 모든 제공자에서 검색
for provider in providers:
    try:
        results = provider.search("Attack on Titan")
        print(f"{provider.name}: {len(results)} results")
    except Exception as e:
        print(f"Error with {provider.name}: {e}")
```

### 설정 관리

```python
from src.core.settings_manager import SettingsManager

# 설정 관리자 초기화
settings = SettingsManager()

# 설정 조회
api_key = settings.get_setting('tmdb_api_key')

# 설정 저장
settings.set_setting('destination_root', '/new/path')
settings.save_settings()
```

---

**버전**: 2.0.0
**최종 업데이트**: 2024년 12월
**라이선스**: MIT License
