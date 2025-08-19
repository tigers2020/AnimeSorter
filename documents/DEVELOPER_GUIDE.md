# AnimeSorter 개발자 가이드

## 📖 목차
1. [아키텍처 개요](#아키텍처-개요)
2. [프로젝트 구조](#프로젝트-구조)
3. [개발 환경 설정](#개발-환경-설정)
4. [코드 스타일 가이드](#코드-스타일-가이드)
5. [핵심 모듈 설명](#핵심-모듈-설명)
6. [플러그인 개발](#플러그인-개발)
7. [테스트 가이드](#테스트-가이드)
8. [배포 가이드](#배포-가이드)

## 🏗️ 아키텍처 개요

AnimeSorter는 모듈화된 아키텍처를 기반으로 설계되었습니다. 각 컴포넌트는 명확한 책임을 가지며, 느슨하게 결합되어 있어 유지보수성과 확장성을 보장합니다.

### 핵심 컴포넌트

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GUI Layer     │    │  Business Logic │    │  Data Layer     │
│                 │    │                 │    │                 │
│ - MainWindow    │◄──►│ - FileParser    │◄──►│ - TMDBClient    │
│ - Components    │    │ - FileManager   │    │ - Settings      │
│ - Managers      │    │ - TMDBManager   │    │ - Cache         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 데이터 흐름

1. **파일 스캔**: GUI에서 폴더 선택 → FileManager가 파일 목록 생성
2. **파싱**: FileParser가 파일명에서 메타데이터 추출
3. **검색**: TMDBClient가 TMDB API에서 메타데이터 검색
4. **선택**: 사용자가 GUI에서 올바른 메타데이터 선택
5. **정리**: FileManager가 파일을 지정된 위치로 이동/복사

## 📁 프로젝트 구조

```
AnimeSorter/
├── src/                          # 소스 코드
│   ├── main.py                   # 애플리케이션 진입점
│   ├── core/                     # 핵심 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── file_parser.py        # 파일명 파싱 엔진
│   │   ├── file_manager.py       # 파일 관리 및 정리
│   │   ├── tmdb_client.py        # TMDB API 클라이언트
│   │   └── settings_manager.py   # 설정 관리
│   ├── gui/                      # GUI 컴포넌트
│   │   ├── __init__.py
│   │   ├── main_window.py        # 메인 윈도우
│   │   ├── components/           # UI 컴포넌트
│   │   │   ├── left_panel.py     # 왼쪽 패널
│   │   │   ├── right_panel.py    # 오른쪽 패널
│   │   │   ├── results_view.py   # 결과 표시
│   │   │   ├── main_toolbar.py   # 메인 툴바
│   │   │   └── settings_dialog.py # 설정 다이얼로그
│   │   ├── managers/             # GUI 관리자
│   │   │   ├── anime_data_manager.py
│   │   │   ├── tmdb_manager.py
│   │   │   ├── file_processing_manager.py
│   │   │   └── event_handler.py
│   │   └── table_models.py       # 테이블 모델
│   └── plugins/                  # 플러그인 시스템
│       ├── __init__.py
│       ├── base.py               # 플러그인 기본 클래스
│       └── providers/            # 메타데이터 제공자
│           ├── anidb_plugin.py
│           └── myanimelist_plugin.py
├── tests/                        # 테스트 코드
│   ├── test_file_parser.py
│   ├── test_file_manager.py
│   ├── test_tmdb_client.py
│   └── test_gui_components.py
├── documents/                    # 문서
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   └── API_REFERENCE.md
├── requirements.txt              # 의존성
├── run_tests.py                  # 테스트 실행 스크립트
└── README.md                     # 프로젝트 개요
```

## 🛠️ 개발 환경 설정

### 필수 도구

- **Python 3.8+**: 최신 Python 버전 권장
- **Git**: 버전 관리
- **IDE**: PyCharm, VS Code, 또는 Cursor 권장
- **가상환경**: 프로젝트별 의존성 격리

### 개발 환경 설정

1. **저장소 클론**
   ```bash
   git clone https://github.com/yourusername/AnimeSorter.git
   cd AnimeSorter
   ```

2. **가상환경 생성**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 또는
   venv\Scripts\activate     # Windows
   ```

3. **개발 의존성 설치**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # 개발 모드 설치
   ```

4. **환경 변수 설정**
   ```bash
   # .env 파일 생성
   TMDB_API_KEY=your_api_key_here
   DEBUG=True
   LOG_LEVEL=DEBUG
   ```

### IDE 설정

#### PyCharm 설정
- Python 인터프리터를 가상환경으로 설정
- 코드 스타일을 PEP 8로 설정
- 테스트 러너 설정

#### VS Code 설정
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black"
}
```

## 📝 코드 스타일 가이드

### Python 스타일 가이드

- **PEP 8** 준수
- **Black** 포맷터 사용
- **Pylint** 린터 사용
- **Type hints** 사용 권장

### 네이밍 컨벤션

```python
# 클래스명: PascalCase
class FileParser:
    pass

# 함수/변수명: snake_case
def parse_filename(file_path: str) -> dict:
    pass

# 상수: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 1024 * 1024 * 1024

# 모듈명: snake_case
file_parser.py
```

### 문서화

```python
def parse_filename(file_path: str) -> dict:
    """
    파일명에서 메타데이터를 추출합니다.
    
    Args:
        file_path (str): 파싱할 파일 경로
        
    Returns:
        dict: 추출된 메타데이터
            {
                'title': str,
                'season': int,
                'episode': int,
                'quality': str
            }
            
    Raises:
        ValueError: 파일명 형식이 올바르지 않은 경우
    """
    pass
```

### 예외 처리

```python
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Specific error occurred: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise CustomException("Operation failed") from e
```

## 🔧 핵심 모듈 설명

### FileParser

파일명 파싱을 담당하는 핵심 모듈입니다.

```python
from src.core.file_parser import FileParser

parser = FileParser()
metadata = parser.parse("Attack on Titan S01E01.mkv")
# 결과: {'title': 'Attack on Titan', 'season': 1, 'episode': 1}
```

**주요 메서드**:
- `parse(filename)`: 파일명 파싱
- `extract_title(filename)`: 제목 추출
- `extract_episode_info(filename)`: 에피소드 정보 추출

### TMDBClient

TMDB API와의 통신을 담당하는 클라이언트입니다.

```python
from src.core.tmdb_client import TMDBClient

client = TMDBClient(api_key="your_api_key")
results = client.search_anime("Attack on Titan")
```

**주요 메서드**:
- `search_anime(query)`: 애니메이션 검색
- `get_details(tmdb_id)`: 상세 정보 조회
- `get_episodes(tmdb_id, season_number)`: 에피소드 목록 조회

### FileManager

파일 관리 및 정리를 담당하는 모듈입니다.

```python
from src.core.file_manager import FileManager

manager = FileManager(destination_root="/path/to/destination")
manager.organize_file(source_path, metadata)
```

**주요 메서드**:
- `organize_file(source, metadata)`: 파일 정리
- `create_directory_structure(metadata)`: 디렉토리 구조 생성
- `rename_file(old_path, new_name)`: 파일명 변경

### 파일 정리 실행 시스템

파일 정리 실행은 새로운 컴포넌트들을 통해 구현됩니다.

#### OrganizePreflightDialog

정리 실행 전 프리플라이트 확인을 담당하는 다이얼로그입니다.

```python
from src.gui.components.organize_preflight_dialog import OrganizePreflightDialog

dialog = OrganizePreflightDialog(grouped_items, destination_directory, parent)
dialog.proceed_requested.connect(on_proceed)
result = dialog.exec_()
```

**주요 기능**:
- 그룹/파일 개수, 예상 크기 표시
- 샘플 대상 경로 미리보기
- 제목 재정제 로직 적용
- 진행/취소 선택

#### FileOrganizeWorker

백그라운드에서 파일 이동 작업을 수행하는 QThread 기반 Worker입니다.

```python
from src.gui.components.organize_progress_dialog import FileOrganizeWorker

worker = FileOrganizeWorker(grouped_items, destination_directory)
worker.progress_updated.connect(update_progress)
worker.file_processed.connect(log_file_processed)
worker.completed.connect(on_completed)
worker.start()
```

**주요 시그널**:
- `progress_updated(int, str)`: 진행률 및 현재 파일 업데이트
- `file_processed(str, str, bool)`: 파일 처리 결과 로그
- `completed(object)`: 작업 완료 시 OrganizeResult 전달

**주요 기능**:
- 그룹별 순차 처리
- 파일명 충돌 해결 (`파일 (n).확장자`)
- 경로 길이 제한 검증 (Windows 260자)
- 네트워크 드라이브 지원 (복사 후 삭제)
- 취소 가능한 작업 처리
- **자막 파일 자동 이동**: 비디오 파일과 연관된 자막 파일(.srt, .ass, .ssa, .sub, .vtt, .idx) 자동 감지 및 이동

**자막 파일 처리 로직**:
```python
def _find_subtitle_files(self, video_path: str) -> List[str]:
    """비디오 파일과 연관된 자막 파일들을 찾습니다"""
    # 지원하는 자막 확장자
    subtitle_extensions = {'.srt', '.ass', '.ssa', '.sub', '.vtt', '.idx', '.smi', '.sami', '.txt'}
    
    # 파일명 매칭 패턴:
    # 1. 정확히 일치: video.mkv ↔ video.srt
    # 2. 언어 코드 포함: video.mkv ↔ video.ko.srt
    # 3. 부분 일치: video.mkv ↔ video.ass
    # 4. 포함 관계: video.mkv ↔ video_subtitle.srt
```

**빈 디렉토리 정리 로직**:
```python
def _cleanup_empty_directories(self, source_directories: Set[str]) -> int:
    """파일 이동 후 빈 디렉토리들을 정리합니다"""
    # 재귀적으로 하위 디렉토리부터 상위 디렉토리 순으로 정리
    # os.rmdir()를 사용하여 빈 디렉토리만 삭제
    # 권한 오류나 다른 이유로 삭제 실패 시 로그 기록
```

#### OrganizeProgressDialog

파일 정리 진행 상황을 표시하는 다이얼로그입니다.

```python
from src.gui.components.organize_progress_dialog import OrganizeProgressDialog

dialog = OrganizeProgressDialog(grouped_items, destination_directory, parent)
dialog.start_organization()
result = dialog.exec_()
organize_result = dialog.get_result()
```

**주요 기능**:
- 실시간 진행률 표시
- 현재 처리 중인 파일명 표시
- 처리 로그 실시간 업데이트
- 작업 취소 기능
- 완료 후 결과 요약

#### OrganizeResult

파일 정리 결과를 담는 데이터 클래스입니다.

```python
from src.gui.components.organize_progress_dialog import OrganizeResult

result = OrganizeResult()
result.success_count = 10
result.error_count = 2
result.skip_count = 1
result.errors = ["파일1.mkv: 권한 오류", "파일2.mkv: 경로 너무 김"]
result.skipped_files = ["0바이트 파일: 파일3.mkv"]
```

**주요 속성**:
- `success_count`: 성공한 파일 수
- `error_count`: 실패한 파일 수
- `skip_count`: 건너뛴 파일 수
- `subtitle_count`: 이동된 자막 파일 수
- `errors`: 오류 메시지 목록
- `skipped_files`: 건너뛴 파일 목록

### 파일 정리 실행 흐름

1. **사용자 액션**: 툴바의 "정리 실행" 버튼 클릭
2. **프리플라이트**: OrganizePreflightDialog로 요약 정보 표시
3. **사용자 확인**: 진행 또는 취소 선택
4. **백그라운드 처리**: FileOrganizeWorker에서 파일 이동 실행
5. **진행률 표시**: OrganizeProgressDialog로 실시간 진행 상황 표시
6. **완료 처리**: OrganizeResult를 받아 최종 요약 표시

### 안전성 및 오류 처리

#### 경로 정제
```python
def _sanitize_title(self, representative):
    """제목 정제 및 검증"""
    # TMDB 매치 우선, 없으면 파싱된 제목 사용
    if hasattr(representative, 'tmdbMatch') and representative.tmdbMatch:
        raw_title = representative.tmdbMatch.name
    else:
        raw_title = representative.title or "Unknown"
    
    # 특수문자 제거 (알파벳, 숫자, 한글, 공백만 허용)
    safe_title = re.sub(r'[^a-zA-Z0-9가-힣\s]', '', raw_title)
    safe_title = re.sub(r'\s+', ' ', safe_title).strip()
    
    # 길이 제한 (100자)
    if len(safe_title) > 100:
        safe_title = safe_title[:100].strip()
    
    return safe_title or "Unknown"
```

#### 파일명 충돌 해결
```python
def _resolve_target_path(self, target_base_dir, filename):
    """대상 경로 결정 및 충돌 처리"""
    target_path = os.path.join(target_base_dir, filename)
    
    counter = 1
    original_target_path = target_path
    while os.path.exists(target_path):
        name, ext = os.path.splitext(original_target_path)
        target_path = f"{name} ({counter}){ext}"
        counter += 1
        
        # 무한 루프 방지
        if counter > 1000:
            break
    
    return target_path
```

#### 네트워크 드라이브 지원
```python
def _safe_move_file(self, source_path, target_path):
    """안전한 파일 이동"""
    try:
        shutil.move(source_path, target_path)
    except OSError as e:
        # 네트워크 드라이브나 교차 디스크 이동의 경우
        if "cross-device" in str(e).lower():
            shutil.copy2(source_path, target_path)
            os.remove(source_path)
        else:
            raise
```

### SettingsManager

애플리케이션 설정을 관리하는 모듈입니다.

```python
from src.core.settings_manager import SettingsManager

settings = SettingsManager()
api_key = settings.get_setting('tmdb_api_key')
settings.set_setting('destination_root', '/new/path')
```

## 🔌 플러그인 개발

### 플러그인 기본 구조

```python
from src.plugins.base import MetadataProvider

class MyCustomProvider(MetadataProvider):
    """사용자 정의 메타데이터 제공자"""
    
    def __init__(self):
        super().__init__()
        self.name = "My Custom Provider"
        self.version = "1.0.0"
    
    def search(self, query: str) -> list:
        """메타데이터 검색"""
        # 구현 로직
        pass
    
    def get_details(self, item_id: str) -> dict:
        """상세 정보 조회"""
        # 구현 로직
        pass
```

### 플러그인 등록

```python
# plugins/__init__.py
from .providers.my_custom_provider import MyCustomProvider

AVAILABLE_PROVIDERS = [
    MyCustomProvider,
]
```

### 플러그인 테스트

```python
def test_my_custom_provider():
    provider = MyCustomProvider()
    results = provider.search("Attack on Titan")
    assert len(results) > 0
    assert "title" in results[0]
```

## 🧪 테스트 가이드

### 테스트 실행

```bash
# 모든 테스트 실행
python run_tests.py

# 특정 테스트 실행
python -m pytest tests/test_file_parser.py

# 커버리지와 함께 실행
python -m pytest --cov=src tests/
```

### 테스트 작성 가이드

```python
import pytest
from src.core.file_parser import FileParser

class TestFileParser:
    def setup_method(self):
        """각 테스트 메서드 실행 전 호출"""
        self.parser = FileParser()
    
    def test_parse_standard_filename(self):
        """표준 파일명 파싱 테스트"""
        filename = "Attack on Titan S01E01.mkv"
        result = self.parser.parse(filename)
        
        assert result['title'] == "Attack on Titan"
        assert result['season'] == 1
        assert result['episode'] == 1
    
    def test_parse_invalid_filename(self):
        """잘못된 파일명 파싱 테스트"""
        filename = "invalid_filename.txt"
        
        with pytest.raises(ValueError):
            self.parser.parse(filename)
```

### Mock 사용

```python
from unittest.mock import Mock, patch

def test_tmdb_client_search():
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'results': [{'title': 'Test Anime'}]
        }
        
        client = TMDBClient("fake_api_key")
        results = client.search_anime("Test")
        
        assert len(results) == 1
        assert results[0]['title'] == 'Test Anime'
```

## 🚀 배포 가이드

### 릴리스 준비

1. **버전 업데이트**
   ```python
   # src/main.py
   app.setApplicationVersion("2.0.1")
   ```

2. **CHANGELOG 업데이트**
   ```markdown
   # CHANGELOG.md
   ## [2.0.1] - 2024-12-XX
   ### Added
   - 새로운 기능 추가
   
   ### Fixed
   - 버그 수정
   ```

3. **테스트 실행**
   ```bash
   python run_tests.py
   ```