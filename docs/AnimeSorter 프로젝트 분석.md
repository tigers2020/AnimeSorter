📘 **Welcome to the Python Code Expert service.**  
Please state your Python coding query, and I will assist you with developing **production-quality solutions** that adhere to **Python best practices** and **object-oriented programming concepts.**

---

### 🧠 How to Code Efficiently and Write Great Python Code

Drawing from expert resources you've uploaded—like _Effective Python_, _Better Python Code_, _Expert Python Programming_, and _Design Patterns_—here's a synthesized, rules-based approach to efficient and high-quality Python development:

---

## ✅ 1. **Foundational Coding Practices**

### 🔹 Follow PEP 8
- Enforce consistent formatting and naming conventions.
- Use linters like `flake8`, `pylint`, or `black`.

### 🔹 Embrace Pythonic Idioms
- Use **list comprehensions**, `enumerate()`, `zip()`, `any()` and `all()`.
- Prefer **EAFP (Easier to Ask Forgiveness than Permission)** over **LBYL (Look Before You Leap)**.
- Use `with` statements for resource management.

---

## ✅ 2. **Code Structure and Design**

### 🔹 Write Modular and Maintainable Code
- One module = one responsibility.
- Separate concerns via functions, classes, and packages.

### 🔹 Prefer Composition Over Inheritance
- Use **design patterns** like Strategy, Factory, and Decorator from _GoF_ to promote flexibility and reuse.

### 🔹 Use Interfaces and Protocols
- Use **abstract base classes (ABCs)** or **typing.Protocol** to define interfaces.

---

## ✅ 3. **Performance Optimization**

### 🔹 Avoid Premature Optimization
- First write **clean and correct** code.
- Use `cProfile`, `line_profiler`, `timeit` to locate real bottlenecks.

### 🔹 Data Structure Choices Matter
- Use `deque` for fast FIFO queues.
- Use `defaultdict` or `Counter` for frequency-based operations.

---

## ✅ 4. **Robustness and Error Handling**

### 🔹 Raise Meaningful Exceptions
- Avoid returning `None` for errors—**raise exceptions** with context.

### 🔹 Define Custom Exceptions
- Group related errors under your own base exception class.

### 🔹 Use `try/except/else/finally` Properly
- Use `else` for the code that should only run if no exception occurs.

---

## ✅ 5. **Concurrency and Parallelism**

### 🔹 Choose the Right Model
- `asyncio` for I/O-bound tasks.
- `threading` for blocking I/O.
- `multiprocessing` or `concurrent.futures` for CPU-bound tasks.

---

## ✅ 6. **Testing and Quality Assurance**

### 🔹 Test Early, Test Often
- Use **pytest** for fast, expressive testing.
- Follow **Test-Driven Development (TDD)** where practical.

### 🔹 Use Property-Based and Parametric Testing
- Use `hypothesis` for auto-generated edge-case testing.
- Parameterize tests with `@pytest.mark.parametrize`.

### 🔹 Automate Code Quality
- Use tools like `tox`, `coverage.py`, `mypy`, and `pylint` in CI/CD pipelines.

---

## ✅ 7. **Documentation and Type Hints**

### 🔹 Always Add Docstrings
- Follow **Google style docstrings** for functions, classes, and modules.

### 🔹 Use Type Hints Everywhere
- Enforce them with `mypy` or Pyright.

---

## ✅ 8. **Package and Environment Management**

### 🔹 Use Virtual Environments
- Always isolate environments with `venv` or `poetry`.

### 🔹 Package Well
- Follow the **12-factor app** principles for deployment.

---

## ✅ 9. **Tools You Should Be Using**

| Purpose               | Recommended Tool |
|----------------------|------------------|
| Formatting            | `black`, `isort` |
| Linting               | `flake8`, `pylint` |
| Testing               | `pytest`, `tox` |
| Coverage              | `coverage.py`, `pytest-cov` |
| Debugging             | `pdb`, `ipdb`, `tracemalloc` |
| Profiling             | `cProfile`, `line_profiler` |
| Packaging             | `poetry`, `setuptools`, `twine` |
| Type Checking         | `mypy`, `pyright` |
| CI/CD                 | `GitHub Actions`, `Travis`, `GitLab CI` |

---

Would you like a **project template** with these principles baked in? I can generate a base Python project for you using modern tooling and best practices.

Let me know your use case (web app, CLI tool, API, data science, etc.)!

**ID: `ruleset-coding-efficiency-2025-03`**

Great question! 🧠  
In **industry-quality desktop applications**, ensuring the UI remains responsive while performing background work is **critical**. The UI "freezing" typically happens because the **main thread (UI thread)** is blocked by long-running operations.

---

## ✅ The Correct Industry-Standard Methods

### 🔹1. **Multi-threading (for I/O-bound tasks)**

For background tasks like:
- File I/O
- Database queries
- Web requests

Use Python’s `threading.Thread` or **QThread** (if you're using **PyQt/PySide**) to offload the task.

```python
from threading import Thread

def background_task():
    # heavy I/O work here
    ...

# Run in background
thread = Thread(target=background_task, daemon=True)
thread.start()
```

In PyQt/PySide:
```python
from PyQt5.QtCore import QThread, pyqtSignal, QObject

class Worker(QObject):
    finished = pyqtSignal()

    def run(self):
        # do work
        ...
        self.finished.emit()

class BackgroundThread(QThread):
    def __init__(self):
        super().__init__()
        self.worker = Worker()

    def run(self):
        self.worker.run()
```

---

### 🔹2. **Multiprocessing (for CPU-bound tasks)**

For CPU-heavy work like:
- Image processing
- Data parsing
- Machine learning inference

Use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor` to spawn separate processes.

```python
from concurrent.futures import ProcessPoolExecutor

def cpu_heavy_work(data):
    # intensive computation
    ...

with ProcessPoolExecutor() as executor:
    future = executor.submit(cpu_heavy_work, data)
```

---

### 🔹3. **Asynchronous Programming (for GUI frameworks that support it)**

In **async-compatible GUI frameworks** (like `asyncqt` or `tkinter` + `asyncio`), async tasks are efficient for I/O.

```python
import asyncio

async def background_task():
    await asyncio.sleep(1)  # Simulate I/O work

asyncio.run(background_task())
```

But: **Standard Qt GUIs require integration with event loop**, e.g., `QEventLoop` or libraries like `qasync`.

---

### 🔹4. **Worker Pattern with Signals (Best for PyQt/PySide)**

PyQt/PySide has **built-in support** for worker threads using `QObject`, `QThread`, and signals/slots.

- Keeps code organized
- Keeps thread-safe UI updates

---

## 🧠 Best Practices for Desktop Apps

| Practice | Why |
|---------|-----|
| **Never block the main thread** | UI must respond to events |
| **Use signals to update UI** | Thread-safe updates in Qt/GTK |
| **Daemon threads or cleanup** | Prevent resource leakage |
| **Use thread-safe queues** | Pass data safely between threads |
| **Use executors or thread pools** | Avoid creating too many threads |

---

### 🔨 Tools & Libraries

| GUI Toolkit | Recommended Background Method |
|-------------|-------------------------------|
| **PyQt / PySide** | `QThread` + Signals/Slots |
| **Tkinter** | `threading.Thread` + `after()` |
| **Kivy** | `threading` or `Clock.schedule_once()` |
| **wxPython** | `threading` + `wx.CallAfter()` |

---

Would you like me to scaffold an **example PyQt5 desktop app** with background threading and signal-based updates?

Or should I prepare examples for a different GUI toolkit you’re using?

**ID: `background-ui-threading-2025-03`**


That’s a fantastic and in-depth walkthrough of how to use **Cursor** with a `cursor.rules` file, showcasing both the **normal method** and the more powerful **step-by-step method** for building software projects—especially using AI agents to automate and incrementally implement functionality.

---

## 🔥 TL;DR – Key Takeaways on Coding with Cursor Efficiently

### ✅ **1. Normal Method – Quick Instructions**
- Place simple, directive instructions in the `cursor.rules` file.
- Cursor automatically reads and applies them in:
  - **Chat**
  - **Composer**
  - **Command-K**
- Great for small tasks or single-file changes.
- Less structured but fast and effective for rapid prototyping.

### ✅ **2. Step-by-Step Method – Structured Iteration**
- Use `Step 1`, `Step 2`, `Update Step 1`, etc., inside `cursor.rules`.
- Each step describes part of the app logic or UI (e.g., header, chat panel, backend).
- Lets you:
  - Build from **top-to-bottom**, **left-to-right**
  - Make iterative changes cleanly
  - Maintain a **clear app spec**

### ✅ **3. Why Step-by-Step Wins**
- More **robust**, **scalable**, and **debuggable**.
- Encourages:
  - **Modular thinking**
  - **Progressive enhancement**
  - Clear rollback to earlier states
- Empowers you to **fix**, **debug**, and **iterate** on small steps rather than starting over.

---

## 🚀 Pro Tip: Combine Cursor Rules + Error-Driven Dev

1. Implement features using steps (`Step 1: Header`, `Step 2: Chat panel`, etc.)
2. Log errors from your app (e.g., console or Python traceback)
3. Paste them into Composer and say:  
   🔧 _"Here’s the error, please fix."_  
4. Let the AI correct code in-place!

---

## 🎯 Best Practices for Using Cursor Rules

| Use Case                      | Best Method         |
|------------------------------|---------------------|
| Small fix / single command   | Normal              |
| Full app build               | Step-by-step        |
| Bug fixing                   | Inline in Composer  |
| Experimenting                | Chat or side panel  |
| Resetting project            | Use **Restore**     |
| Making global instructions   | Add to `rules for AI`|

---

## 💡 Advanced Tips

- Use `update step X` instead of re-implementing.
- Use **variables**, **agent mode**, and **modular instructions**.
- Store reusable steps for other apps and compose them together.

---

## Would You Like Help With:
- Structuring your own `cursor.rules` file?
- Generating reusable rule templates for faster app development?
- Automating desktop or terminal-based chat apps?

I’d be happy to walk you through that or even generate a best-practice project setup using this methodology.

**ID: `cursor-rules-methodology-2025-03`**


# AnimeSorter 프로젝트 개발 가이드 (Step-by-Step)

## 단계 0: 프로젝트 기획 및 설계

### 0.1 목표 정의
- **핵심 목표:** 다운로드된 애니메이션 파일(영상 및 자막)을 메타데이터 기반으로 자동으로 분류하여 체계적인 라이브러리 구조 생성.
- **주요 기능:**
    1.  **파일명 정제:** 불필요한 정보 제거 및 검색용 제목 추출.
    2.  **메타데이터 검색:** TMDB 등 외부 API를 이용한 정보 조회.
    3.  **파일 분류 및 이동:** 메타데이터 기반 폴더 생성 및 파일(원본명 유지, 자막 포함) 이동.
    4.  **캐싱:** API 중복 호출 방지.
    5.  **통합 GUI:** PyQt5 기반 단일 창 인터페이스 제공.
    6.  **플러그인 아키텍처:** 기능 확장성 확보.
- **대상 사용자:** 애니메이션 파일을 관리하려는 일반 사용자부터 파워 유저까지.
- **개발 환경:** Python 3.9+, PyQt5, Windows 11 (초기), 추후 크로스 플랫폼 고려.

### 0.2 아키텍처 설계
- **기본 흐름:** `UI → 파일 스캔 → (파일명 정제 → 캐시 확인 → API 검색 → 캐시 저장) → 폴더 경로 결정 → 파일 이동 → UI 업데이트`
- **모듈 구성:**
    - `main.py`: 애플리케이션 진입점, UI 및 코어 로직 초기화.
    - `src/app.py`: 핵심 로직 및 모듈 통합 관리 (AnimeSorter 클래스).
    - `src/ui/main_window.py`: PyQt5 기반 메인 UI.
    - `src/file_cleaner.py`: 파일명 정제 로직.
    - `src/plugin/tmdb/provider.py`: TMDB 메타데이터 제공자 (플러그인 형태).
    - `src/plugin/base.py`: 메타데이터 제공자 인터페이스.
    - `src/cache_db.py`: SQLite 기반 캐시 관리.
    - `src/file_manager.py`: 파일 스캔, 폴더 생성, 파일 이동 로직.
    - `src/config.py`: 설정(config.yaml) 관리.
    - `src/logger.py`: 로깅 설정.
    - `src/utils.py`: 공통 유틸리티.
    - `src/exceptions.py`: 사용자 정의 예외.
    - `tests/`: 단위/통합 테스트.
    - `docs/`: 문서.
- **플러그인 구조:** 메타데이터 소스, 분류 규칙 등을 플러그인으로 확장 가능하도록 설계.

### 0.3 기술 스택 선정
- **언어:** Python 3.9+
- **GUI:** PyQt5 (초기 버전, 이후 PySide6 전환 고려)
- **비동기:** asyncio, aiohttp (API 호출 및 백그라운드 작업)
- **데이터베이스:** SQLite (내장 모듈 활용)
- **설정:** PyYAML
- **로깅:** loguru
- **테스트:** pytest, pytest-asyncio, pytest-mock
- **포맷팅/린팅:** black, isort, flake8, mypy
- **패키징:** PyInstaller (초기), poetry (의존성 관리)

## 단계 1: 개발 환경 설정 및 프로젝트 구조 생성

### 1.1 가상 환경 설정
```bash
# Conda 사용 시
conda create -n animesorter python=3.12  # 프로젝트 요구사항에 맞춰 버전 지정
conda activate animesorter

# venv 사용 시
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
```

### 1.2 Git 저장소 초기화 및 브랜치 전략
```bash
git init
git branch develop  # 개발 브랜치 생성
git checkout develop
# 브랜치: main(stable), develop(dev), feature/*, bugfix/*, release/*
```

### 1.3 의존성 설치 및 관리
- `requirements.txt` 또는 `pyproject.toml` (poetry 사용 시) 파일 생성.
- 초기 필수 라이브러리 목록 작성 (PyQt5, aiohttp, PyYAML, loguru 등).
```bash
pip install -r requirements.txt
# 또는 poetry add <package>
```
- 개발용 의존성 추가 (pytest, black 등) 및 분리 관리.

### 1.4 프로젝트 디렉토리 구조 생성
- `0.2 아키텍처 설계`의 `상세 프로젝트 구조`에 따라 디렉토리 및 기본 `__init__.py` 파일 생성.

### 1.5 기본 설정 및 로깅 구현
- `src/config.py`: `config.yaml` 파일을 읽고 쓰는 기능 구현 (PyYAML 사용).
    - 초기 설정 항목 정의: `api_key`, `source_dir`, `target_dir`, `folder_template`, `log_level` 등.
- `src/logger.py`: `loguru`를 이용한 로깅 설정 함수 구현.
    - 파일 로깅 및 콘솔 로깅 설정.
    - 로그 레벨 설정 가능하도록 구현.
- `main.py`에서 설정 로드 및 로거 초기화 코드 추가.

## 단계 2: 핵심 기능 모듈 개발 (순차적 구현)

### 2.1 파일명 정제 모듈 (`src/file_cleaner.py`)
- **목표:** 파일명에서 검색용 제목, 시즌, 에피소드 정보 추출.
- **구현:**
    1.  `CleanResult` 데이터 클래스 정의 (title, season, episode, year, is_movie 등 포함).
    2.  정규식 패턴(`PATTERNS`) 정의: 릴리즈 그룹, 해상도, 코덱, 시즌, 에피소드, 연도, 영화/특별편 등.
    3.  `clean_filename(filename: str | Path) -> CleanResult` 함수 구현:
        - 입력 파일명에서 확장자 제거.
        - 정의된 패턴들을 순차적으로 적용하여 정보 추출 및 불필요 정보 제거.
        - 시즌/에피소드가 없으면 기본값 설정 (e.g., season=1).
        - 영화/특별편 키워드 감지.
        - 최종 정제된 제목 문자열 생성.
        - 추출된 정보를 `CleanResult` 객체로 반환.
    4.  **예외 처리:** 파싱 실패 시 원본 파일명을 title로 사용하고 로그 기록.
- **테스트 (`tests/test_file_cleaner.py`):**
    - 다양한 형식의 파일명 입력에 대한 예상 `CleanResult` 검증.
    - 경계값 테스트 (시즌/에피소드 번호 범위 등).
    - 파싱 실패 시 동작 검증.

### 2.2 캐시 데이터베이스 모듈 (`src/cache_db.py`)
- **목표:** API 검색 결과를 SQLite에 저장 및 조회하여 중복 호출 방지.
- **구현:**
    1.  `CacheDB` 클래스 구현.
    2.  `initialize()`: DB 파일 연결 및 `media_cache` 테이블 생성 (스키마: `title_key TEXT PRIMARY KEY, year INTEGER, metadata TEXT`). `metadata`는 JSON 문자열로 저장.
    3.  `get_cache(title_key: str) -> Optional[dict]`: `title_key`로 메타데이터 조회. 결과 있으면 JSON 파싱하여 dict 반환.
    4.  `set_cache(title_key: str, metadata: dict)`: 메타데이터를 JSON으로 변환하여 DB에 저장/갱신.
    5.  `_generate_key(title: str, year: Optional[int]) -> str`: 검색용 키 생성 로직 (e.g., `f"{title.lower()}_{year or 'any'}"`).
    6.  **예외 처리:** DB 연결/쿼리 실패 시 로그 기록 및 `None` 반환 (캐시 실패가 전체 동작을 막지 않도록).
- **테스트 (`tests/test_cache_db.py`):**
    - DB 초기화 및 테이블 생성 확인.
    - 캐시 저장 및 조회 기능 검증.
    - 키 생성 로직 검증.
    - DB 오류 발생 시 동작 검증.

### 2.3 플러그인 인터페이스 및 TMDB 플러그인 (`src/plugin/`)
- **목표:** 메타데이터 소스를 플러그인으로 관리하고, 초기 TMDB 플러그인 구현.
- **구현:**
    1.  `src/plugin/base.py`: `MetadataProvider` 추상 베이스 클래스 정의.
        - `async search(title: str, year: Optional[int]) -> Optional[dict]` 추상 메서드 정의.
        - `async get_details(media_id: Any, media_type: str) -> Optional[dict]` 추상 메서드 정의.
        - `initialize()`, `close()` 등 공통 메서드 정의.
    2.  `src/plugin/tmdb/api/client.py`: `TMDBClient` 클래스 구현 (aiohttp 사용).
        - `initialize()`, `close()`, `request()` 메서드 구현.
        - API 키, 언어 설정 관리.
        - 요청 제한(rate limiting) 고려 (간단한 `asyncio.sleep` 추가).
    3.  `src/plugin/tmdb/api/endpoints.py`: `TMDBEndpoints` 클래스 구현.
        - `/search/multi`, `/tv/{id}`, `/movie/{id}` 등 엔드포인트 호출 함수 구현.
        - `client.request()` 사용.
    4.  `src/plugin/tmdb/models/`: TMDB 응답 데이터 모델 정의 (pydantic 또는 dataclass 사용).
    5.  `src/plugin/tmdb/provider.py`: `TMDBProvider(MetadataProvider)` 클래스 구현.
        - `initialize()`: `TMDBClient` 초기화.
        - `search()`: `/search/multi` 호출, 결과 파싱 및 관련성 높은 항목 선택 로직.
        - `get_details()`: 선택된 항목의 ID와 타입으로 `/tv` 또는 `/movie` 상세 정보 호출.
        - **캐시 연동:** `search()` 또는 `get_details()` 호출 전후로 `CacheDB` 모듈 사용.
    6.  **예외 처리:** API 호출 실패, 결과 없음, 응답 파싱 오류 처리.
- **테스트 (`tests/test_tmdb_client.py`):**
    - API 클라이언트 초기화 및 종료 테스트.
    - `pytest-mock`을 이용한 API 응답 모킹 및 `search`, `get_details` 결과 검증.
    - 캐시 연동 동작 검증 (모킹된 캐시 사용).
    - API 오류 발생 시 예외 처리 검증.

### 2.4 파일 관리 모듈 (`src/file_manager.py`)
- **목표:** 파일 스캔, 메타데이터 기반 폴더 경로 결정, 파일/자막 이동.
- **구현:**
    1.  `FileManager` 클래스 구현.
        - `__init__`: source/target 디렉토리, 폴더 구조 템플릿(`folder_template`), 파일명 유지 옵션 등 설정.
    2.  `scan_directory(directory: str, recursive: bool) -> List[Path]`: 지정된 디렉토리에서 비디오/자막 파일 목록 스캔.
    3.  `_find_subtitle_files(video_file: Path) -> List[Path]`: 비디오 파일과 동일한 이름의 자막 파일 탐색.
    4.  `get_target_path(metadata: dict, source_file: Path) -> Path`: 메타데이터와 템플릿을 이용해 대상 폴더 경로 생성.
        - `src/utils.py`에 `clean_filename` 함수(경로용 문자열 정제) 구현 및 사용.
    5.  `process_file(file_path: Path, metadata: dict)` 비동기 함수 구현:
        - `get_target_path` 호출.
        - 대상 디렉토리 생성 (`os.makedirs(exist_ok=True)`).
        - `_find_subtitle_files` 호출.
        - `shutil.move`를 이용한 파일 이동 (비동기 I/O 라이브러리 `aiofiles` 사용 고려).
        - 이름 충돌 처리 (덮어쓰기 옵션 또는 이름 변경).
        - 자막 파일 이동.
    6.  **예외 처리:** 파일/디렉토리 접근 권한, 디스크 공간 부족, 경로 길이 제한 등 I/O 오류 처리.
- **테스트 (`tests/test_file_manager.py`):**
    - 파일 스캔 기능 검증 (재귀 옵션 포함).
    - 자막 파일 탐색 기능 검증.
    - 다양한 메타데이터 입력에 대한 경로 생성 로직 검증.
    - 임시 디렉토리/파일을 이용한 파일 이동 및 자막 연동 검증.
    - 이름 충돌 및 I/O 오류 발생 시 동작 검증.

## 단계 3: GUI 인터페이스 개발 (`src/ui/`)

### 3.1 메인 윈도우 설계 (`main_window.py`)
- **목표:** 사용자 친화적이고 직관적인 인터페이스 구현
- **구현:**
    1.  `MainWindow(QMainWindow)` 클래스 생성
    2.  **UI 컴포넌트:**
        - **상단 메뉴바 (`QMenuBar`):**
            - 파일 메뉴: 폴더 선택, 설정, 종료
            - 도움말 메뉴: 사용법, 정보
        - **도구 모음 (`QToolBar`):**
            - 자주 사용하는 기능의 빠른 접근용 아이콘 버튼
        - **메인 레이아웃 (`QVBoxLayout`):**
            - **경로 선택 영역 (`QGroupBox`):**
                - 소스/대상 폴더 선택 버튼 및 경로 표시 (`QLineEdit` + `QPushButton`)
                - 드래그 앤 드롭 지원 (`setAcceptDrops(True)`)
            - **파일 목록 영역 (`QSplitter`):**
                - 좌측: 소스 파일 트리뷰 (`QTreeView` + `QFileSystemModel`)
                - 우측: 처리될 파일 목록 (`QTableWidget`)
                    - 컬럼: 원본 파일명, 정제된 제목, 시즌, 에피소드, 상태
            - **메타데이터 미리보기 영역 (`QGroupBox`):**
                - 선택된 파일의 TMDB 검색 결과 표시
                - 포스터 이미지, 제목, 개요 등 (`QLabel` + `QTextEdit`)
            - **작업 제어 영역:**
                - 시작/중지 버튼 (`QPushButton`)
                - 진행률 표시 (`QProgressBar`)
                - 현재 작업 상태 표시 (`QLabel`)
    3.  **스타일링:**
        - Material Design 또는 Fluent Design 스타일 적용
        - 사용자 정의 테마 지원 (라이트/다크 모드)
        - 아이콘 및 색상 테마 일관성 유지
    4.  **사용자 경험 개선:**
        - 툴팁으로 기능 설명 제공
        - 키보드 단축키 지원
        - 상태바에 현재 상태 및 팁 표시
        - 작업 취소/되돌리기 기능

### 3.2 백그라운드 작업 처리
- **목표:** 효율적이고 안정적인 비동기 작업 처리
- **구현:**
    1.  **`WorkerSignals` 클래스 구현:**
        ```python
        class WorkerSignals(QObject):
            started = pyqtSignal()
            finished = pyqtSignal()
            progress = pyqtSignal(str, int)  # 메시지, 진행률
            error = pyqtSignal(str)
            metadata_found = pyqtSignal(dict)  # TMDB 메타데이터
            file_processed = pyqtSignal(str, bool)  # 파일경로, 성공여부
        ```
    
    2.  **`FileProcessWorker(QRunnable)` 클래스 구현:**
        ```python
        class FileProcessWorker(QRunnable):
            def __init__(self, files, config):
                super().__init__()
                self.signals = WorkerSignals()
                self.files = files
                self.config = config
                self._is_running = True
                
            def run(self):
                self.signals.started.emit()
                try:
                    for file in self.files:
                        if not self._is_running:
                            break
                        # 파일 처리 로직
                        self._process_single_file(file)
                finally:
                    self.signals.finished.emit()
                    
            def stop(self):
                self._is_running = False
        ```
    
    3.  **`QThreadPool` 활용:**
        ```python
        class MainWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                self.thread_pool = QThreadPool()
                self.thread_pool.setMaxThreadCount(1)  # 순차 처리
                
            def start_processing(self):
                worker = FileProcessWorker(self.files, self.config)
                worker.signals.progress.connect(self.update_progress)
                worker.signals.metadata_found.connect(self.update_metadata_preview)
                worker.signals.error.connect(self.show_error)
                worker.signals.finished.connect(self.on_processing_finished)
                self.thread_pool.start(worker)
        ```
    
    4.  **작업 상태 관리:**
        - 작업 큐 구현 (`collections.deque`)
        - 작업 우선순위 지원
        - 일시 중지/재개 기능
        - 메모리 사용량 모니터링
    
    5.  **오류 처리 및 복구:**
        - 네트워크 오류 시 자동 재시도
        - 파일 시스템 오류 복구
        - 작업 로그 저장
    
    6.  **성능 최적화:**
        - 파일 처리 배치화
        - 메타데이터 캐시 활용
        - 이미지 로딩 지연
        - 메모리 누수 방지

### 3.3 설정 관리 (`settings_dialog.py`)
- **구현:**
    1.  `SettingsDialog(QDialog)` 클래스:
        - 탭 기반 설정 UI (`QTabWidget`)
        - 설정 항목별 그룹화 (`QGroupBox`)
        - 설정 변경 실시간 저장
    2.  **설정 카테고리:**
        - 일반: 언어, 테마, 로그 레벨
        - 파일 처리: 이름 규칙, 자막 처리
        - TMDB: API 키, 언어, 지역
        - 성능: 동시 처리 수, 캐시 크기
    3.  **설정 저장/로드:**
        - YAML 파일 연동
        - 설정 유효성 검사
        - 기본값 복원 기능

## 단계 4: 통합, 테스트 및 개선

### 4.1 통합 테스트
- **목표:** 전체 시스템이 시나리오별로 정상 동작하는지 검증.
- **시나리오:**
    1.  정상 동작 (다양한 파일명, 자막 포함).
    2.  API 검색 실패 (존재하지 않는 제목, 네트워크 오류).
    3.  파일 이동 실패 (권한 없음, 디스크 공간 부족).
    4.  캐시 동작 확인 (동일 시리즈 반복 처리 시 API 호출 1회).
    5.  작업 중지 기능 확인.
    6.  대용량 파일 처리 성능 테스트.
- **방법:** 실제 파일을 이용한 수동 테스트 및 일부 자동화된 테스트 스크립트 작성.

### 4.2 성능 최적화
- **비동기 I/O:** 파일 이동 및 API 호출에 `aiohttp`, `aiofiles` 활용.
- **병렬 처리:** `asyncio.gather` 등을 이용한 동시 API 요청 (Rate Limit 주의).
- **캐싱:** 적극적 캐싱 활용.
- **메모리 사용:** 대용량 파일 목록 처리 시 메모리 사용량 점검.

### 4.3 오류 처리 및 사용자 피드백 개선
- 각 모듈 및 UI에서 발생하는 예외 상세 로깅.
- 사용자에게 친화적인 오류 메시지 제공.
- 작업 완료 후 성공/실패 요약 정보 제공.

## 단계 5: 문서화, 패키징 및 배포

### 5.1 문서화
- `README.md`: 프로젝트 개요, 설치 방법, 사용법.
- `docs/`: 사용자 가이드, 개발자 가이드, API 문서 (Sphinx 등 활용 고려).
- 코드 내 Docstring 및 주석 작성.

### 5.2 패키징
- `PyInstaller`를 이용한 Windows용 `.exe` 파일 생성.
    - `--onefile`, `--windowed`, 아이콘, 데이터 파일 포함 옵션 설정.
- (선택) macOS용 `.app`, Linux용 AppImage 등 크로스 플랫폼 패키징.

### 5.3 배포
- GitHub Releases를 통한 버전별 바이너리 및 소스 코드 배포.
- (선택) PyPI, Conda-Forge 등 패키지 저장소 등록.

## 단계 6: 유지보수 및 향후 개선

- 사용자 피드백 반영 및 버그 수정.
- `Project_Job_Description.md`의 '향후 개선 및 확장 계획' 참조:
    - 메타데이터 소스 확장 (AniDB, MAL 플러그인).
    - 머신러닝 기반 파일명 파싱 도입.
    - 사용자 확인 단계 추가 (반자동 모드).
    - 폴더 구조 커스터마이즈 기능.
    - 자막 다운로드, 포스터 저장 등 부가 기능.
    - 해시 기반 파일 매칭.
    - 성능 최적화 (멀티스레딩 등).
    - 크로스 플랫폼 지원 강화.

--- 

이 단계별 가이드는 프로젝트를 체계적으로 진행하는 데 도움이 될 것입니다. 각 단계별로 목표를 설정하고, 구현과 테스트를 반복하며 진행하는 것이 중요합니다. 