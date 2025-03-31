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

Use Python's `threading.Thread` or **QThread** (if you're using **PyQt/PySide**) to offload the task.

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

Or should I prepare examples for a different GUI toolkit you're using?

**ID: `background-ui-threading-2025-03`**


That's a fantastic and in-depth walkthrough of how to use **Cursor** with a `cursor.rules` file, showcasing both the **normal method** and the more powerful **step-by-step method** for building software projects—especially using AI agents to automate and incrementally implement functionality.

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
   🔧 _"Here's the error, please fix."_  
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

I'd be happy to walk you through that or even generate a best-practice project setup using this methodology.

**ID: `cursor-rules-methodology-2025-03`**

---

# AnimeSorter 프로젝트를 위한 Cursor AI Rules

## Python 코딩 규칙

```cursor.rules
# AnimeSorter Python 코딩 규칙

## 기본 규칙
- PEP 8 형식을 따릅니다
- 파일, 클래스, 함수에 타입 힌트와 독스트링을 추가합니다
- 모든 예외는 적절히 처리합니다
- 백그라운드 작업은 스레드 또는 비동기로 처리합니다

## Step 1: 프로젝트 구조 설계
- 단일 책임 원칙을 따라 모듈을 설계합니다
- 각 폴더/파일이 명확한 책임을 갖도록 합니다
- 관련 기능은 동일한 패키지에 배치합니다

## Step 2: 데이터 구조 설계
- 데이터 클래스나 Pydantic 모델을 사용합니다
- 컨테이너 타입은 collections 모듈(defaultdict, Counter, deque 등)을 활용합니다
- 불변 객체를 선호합니다

## Step 3: 코드 최적화
- 성능 병목을 먼저 파악한 후 최적화합니다
- I/O 작업은 비동기(asyncio)로 처리합니다
- CPU 집약적 작업은 multiprocessing으로 처리합니다

## Step 4: 에러 처리 및 로깅
- 커스텀 예외 계층 구조를 구현합니다
- try/except 블록에서 구체적인 예외를 처리합니다
- 로깅은 다양한 레벨(DEBUG, INFO, WARNING, ERROR)을 적절히 사용합니다

## Step 5: GUI 및 스레딩 구현
- 메인 스레드는 UI 작업만 수행합니다
- QRunnable과 QThreadPool을 사용하여 백그라운드 작업을 처리합니다
- 신호(Signals)와 슬롯(Slots)으로 스레드 간 통신합니다

## Step 6: 테스트 및 품질 보증
- 모든 기능에 단위 테스트를 작성합니다
- pytest를 사용하여 테스트를 자동화합니다
- CI/CD 파이프라인에 flake8, pylint, mypy를 통합합니다

## Best Practices
- 리스트 컴프리헨션, enumerate(), zip(), any(), all() 사용
- 컨텍스트 매니저(with 문)로 리소스 관리
- 상속보다 합성을 선호
- 함수형 프로그래밍 패턴 활용
- 명시적인 변수/함수/클래스 이름 사용
```

## 스레딩 및 동시성 규칙

```cursor.rules
# AnimeSorter 스레딩 및 동시성 규칙

## Step 1: 작업 유형 분류
- I/O 바운드 작업(API 호출, 파일 처리, DB 쿼리): asyncio 또는 threading 사용
- CPU 바운드 작업(이미지 처리, 복잡한 계산): multiprocessing 사용
- 작업 특성에 따라 최적의 동시성 모델 선택

## Step 2: GUI 스레딩 패턴
- UI 스레드(메인 스레드)는 절대 차단하지 않음
- QRunnable/QThreadPool 패턴 사용:
  ```python
  class WorkerSignals(QObject):
      finished = pyqtSignal()
      result = pyqtSignal(object)
      progress = pyqtSignal(int, str)
      error = pyqtSignal(str)

  class Worker(QRunnable):
      def __init__(self, fn, *args, **kwargs):
          super().__init__()
          self.fn = fn
          self.args = args
          self.kwargs = kwargs
          self.signals = WorkerSignals()
      
      def run(self):
          try:
              result = self.fn(*self.args, **self.kwargs)
              self.signals.result.emit(result)
          except Exception as e:
              self.signals.error.emit(str(e))
          finally:
              self.signals.finished.emit()
  ```

## Step 3: 스레드 간 통신
- Signal/Slot 패턴으로 UI 업데이트
- 스레드 안전한 큐(Queue) 사용
- 공유 상태 최소화

## Step 4: 리소스 관리
- 모든 스레드는 daemon=True 또는 명시적으로 종료
- ThreadPoolExecutor 사용하여 스레드 관리
- 컨텍스트 매니저 패턴 활용

## Step 5: asyncio 통합
- qasync 또는 QEventLoop로 Qt와 asyncio 통합
- 비동기 작업은 async/await 패턴 사용
- 코루틴 체인으로 복잡한 작업 구성

## 성능 최적화 규칙
- 데이터 구조: defaultdict, Counter, deque 적극 활용
- 캐싱: functools.lru_cache 또는 캐시 DB 사용
- 지연 평가(lazy evaluation)와 제너레이터 활용
- 고비용 작업은 프로파일링 후 최적화

## 오류 처리 규칙
- EAFP 패턴 사용 (Look Before You Leap 대신)
- 백그라운드 작업 오류는 항상 메인 스레드로 전파
- 모든 예외는 로깅하고 사용자에게 적절한 메시지 제공
- 오류 복구 메커니즘 구현 (재시도, 롤백 등)

## 테스트 규칙
- 스레드 코드는 mock으로 격리하여 테스트
- 경쟁 상태 및 데드락 시나리오 테스트
- QSignalSpy로 신호 테스트
- CPU/메모리 사용량 모니터링 테스트
```

**ID: `animesorter-dev-rules-2023-07`**
