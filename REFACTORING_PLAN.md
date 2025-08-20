# AnimeSorter 리팩토링 계획서

## 개요

거대 MainWindow 분해 + 의존성 주입(IOC) 도입 + EventBus/CommandInvoker 실사용으로 MVVM 완성.

파일 시스템 조작의 Undo/Redo 보장(저널링+스테이징).

테스트 용이성과 재현 가능한 빌드 파이프라인 강화(ruff/mypy/pytest-qt/GHA).

## 타깃 아키텍처 (최종 상태)

```
src/
  app/                  # 앱 조립(root composition) & DI Container
  ui/                   # PyQt5 Views (QMainWindow, Dialogs, Widgets)
  viewmodels/           # ViewModels (Qt signals/properties; no IO)
  domain/               # 순수 로직(entities, value objects, policies)
  services/             # Use-cases (ScanService, MetadataService, OrganizeService, ExportService)
  infra/                # TMDBClient, FileSystem(ops+journal), Cache, Settings
  platform/             # EventBus, CommandInvoker(QUndoStack bridge), ErrorBus, Logging
```

## Cross-cutting Concerns

- **EventBus**: 타입이 있는 이벤트(dataclass)로 publish/subscribe
- **CommandInvoker ↔ QUndoStack 브리지**: 실행/취소/재실행 관리
- **DI Container**: 의존성 그래프를 한 곳에서 조립(테스트에서 쉽게 대체)

## MVVM 패턴

- **View ⇄ ViewModel**: Qt 시그널/프로퍼티 바인딩(간단 바인딩 헬퍼)
- **ViewModel ⇄ Service/Domain**: 순수 파이썬 호출(비동기 작업은 시그널로 UI 갱신)

## 단계별 실행 계획

### Phase 0: 기반 정리 (0.5주)

#### 작업
- 린터/포매터/타입체커 도입: ruff, black, mypy(strict 모드 점진 적용)
- 테스트 러너: pytest, GUI는 pytest-qt
- CI: GitHub Actions에서 3 OS 매트릭스 + 캐시 + 아티팩트
- 빌드 파이프라인: 현재 pyproject.toml/AnimeSorter.spec 활용, 의존성 고정

#### 수용 기준
- `make test` 한 줄로 통과
- PR 게이트: lint/type/test 100% 통과

### Phase 1: 핵심 아키텍처 개선 (1–2주, 높은 우선순위)

#### 1.1 MainWindow 분리
- **작업**: MainWindow를 View/UI 전용으로 축소. 현재 거대 클래스는 Controller·상태·IO를 제거
- **수용 기준**: 기존 화면 기능 유지(회귀 테스트 통과), MainWindow 파일 400줄 이하로 축소

#### 1.2 DI Container 도입
- **작업**: app/container.py에 단순 컨테이너 구현 또는 dependency-injector 채택
- **수용 기준**: main.py 또는 app/bootstrap.py에서 컨테이너 1곳에서만 조립

#### 1.3 이벤트 기반 아키텍처 활성화
- **작업**: 이벤트 정의(platform/events.py), 서비스는 직접 UI 갱신 금지 → EventBus publish
- **수용 기준**: 기존 "직접 호출" 경로 제거, 이벤트로 흐름 확인 가능

### Phase 2: MVVM 완성 (1–2주, 중간 우선순위)

#### 2.1 ViewModel 분리
- **작업**: viewmodels/scan_vm.py, metadata_vm.py, organize_vm.py, settings_vm.py 등 생성
- **수용 기준**: View 코드에서 비즈니스 로직 호출 제거(바인딩 또는 VM 메서드만 호출)

#### 2.2 데이터 바인딩 유틸
- **작업**: 간단 바인딩 헬퍼(platform/binding.py)로 위젯<->VM 시그널 연결 표준화

### Phase 3: 명령 패턴 + Undo/Redo (1주, 중간 우선순위)

#### 3.1 핵심 명령 구현
- **작업**: 파일 이동/이름변경/폴더 생성/삭제 등 모든 변경을 Command로 래핑
- **수용 기준**: 파일 조작은 반드시 Command 경유(직접 FS 호출 금지) + Undo/Redo 동작

#### 3.2 CommandInvoker 활성화
- **작업**: 기존 CommandInvoker를 QUndoStack 위에 얹는 어댑터로 재구성

### Phase 4: 설정·에러 처리·로깅 (1주, 낮은 우선순위)

#### 작업
- Settings: pydantic-settings로 계층화(ENV > YAML > 기본값)
- ErrorBus: 예외를 이벤트로 승격, 전역 핸들러에서 사용자 친화 메시지 & 로깅
- 로깅: 구조화 로깅(JSON 핸들러) + 회전(롤링) 설정

#### 수용 기준
- 치명 예외도 앱이 죽지 않고 사용자 피드백 제공 + 로그 남김

## 상세 작업 목록

### 우선순위 기준
- **P0**: 블로커. 지연 시 전체 일정 영향
- **P1**: 핵심 기능 품질/안정성 직결
- **P2**: 품질 향상/확장성 개선
- **P3**: 미관/편의성

### 마스터 To-Do 리스트

| ID | Task | Priority | Impact | Effort | Dependencies | 메모/수용 기준 |
|---|---|---|---|---|---|---|
| T0.1 | Lint/Format/Type 도입(ruff/black/mypy) + 기본 설정 | P0 | High | S | — | CI에서 전부 통과 |
| T0.2 | 테스트 러너/픽스처 정비(pytest, pytest-qt) | P0 | High | S | T0.1 | 최소 1개 GUI/1개 Service 테스트 통과 |
| T0.3 | CI(GitHub Actions) 3 OS 매트릭스 + 캐시 | P0 | High | S | T0.1 | Pull Request Gate 동작 |
| T0.4 | 빌드 재현성 점검(pyproject 잠금/스펙 동기화) | P1 | High | M | T0.1 | 로컬=CI 동일 해시/의존 버전 |
| T1.1 | DI Container(AppContainer) 추가 및 엔트리포인트 단일화 | P0 | High | M | T0.* | 서비스/클라이언트 생성이 컨테이너 단일 지점 |
| T1.2 | EventBus 타입 정의/퍼블리셔-서브스크라이버 골격 | P0 | High | S | T1.1 | 주요 이벤트 3종 이상 정의/테스트 |
| T1.3 | MainWindow 분리(Scan 화면 MVVM 1차 전환) | P0 | High | M | T1.1–T1.2 | MainWindow 400줄↓, 기능 회귀 없음 |
| T1.4 | Scanner 서비스→EventBus 발행, ViewModel 구독 | P1 | High | M | T1.2–T1.3 | 직접 UI 갱신 제거, 이벤트 기반 동작 |
| T1.5 | 백그라운드 실행 인프라(QThreadPool/qasync) | P1 | High | M | T1.2 | 장시간 작업에도 UI 프리즈 없음 |
| T1.6 | ParserChain(Anitopy→GuessIt 폴백) 및 스코어링 | P1 | Med | M | T1.1 | 파싱 정확도 리그레션 테스트 추가 |
| T2.1 | Metadata/Organize/Settings ViewModel 분리 | P1 | High | M | T1.3–T1.5 | UI↔로직 완전 분리(직접 호출 제거) |
| T2.2 | 바인딩 헬퍼(Widget↔VM 시그널/프로퍼티) | P2 | Med | S | T2.1 | 반복 바인딩 코드 30%↓ |
| T2.3 | QAbstractListModel로 그룹/파일 목록 모델화 | P1 | High | M | T2.1 | 정렬/필터 성능/일관성 확보 |
| T2.4 | 나머지 화면 MVVM 전환(MainWindow 슬림화 완료) | P1 | High | M | T2.1–T2.3 | View 파일별 비즈니스 로직 0 |
| T2.5 | TMDB 연동 비동기화 + VCR 녹화 테스트 | P2 | Med | M | T1.5 | 네트워크 불안정성 제거 |
| T3.1 | FileSystem 저널/스테이징 레이어 도입 | P0 | High | M | T1.1 | 모든 변경 기록/복구 단위 테스트 |
| T3.2 | Command 베이스 + Move/Rename/Create/Delete | P0 | High | M | T3.1 | 각 명령 Undo/Redo 보장 |
| T3.3 | CommandInvoker↔QUndoStack 브리지 | P1 | High | S | T3.2 | 메뉴/툴바로 Undo/Redo 동작 |
| T3.4 | UI 액션→Command 경유(직접 FS 호출 제거) | P1 | High | S | T3.3 | 직접 호출 0건, 회귀 테스트 통과 |
| T3.5 | 트랜잭션 커밋/롤백 시나리오 테스트 | P1 | High | S | T3.2–T3.4 | 예외 상황도 데이터 일관성 유지 |
| T4.1 | Settings 계층화(pydantic-settings + QSettings) | P2 | Med | S | T1.1 | ENV/YAML/기본값 우선순위 검증 |
| T4.2 | ErrorBus + 전역 예외 핸들러/사용자 메시지 | P2 | Med | S | T1.2 | 크래시 없이 경고/로그 남김 |
| T4.3 | 구조화 로깅(JSON + 롤링) | P2 | Med | S | T1.1 | 파일/콘솔 핸들러/회전 설정 |
| T4.4 | 문서화(architecture/contributing/testing/release) | P3 | Med | M | 전 단계 | 문서 PR 체커 통과 |
| T4.5 | 죽은 코드/직접 의존 제거 및 모듈 재배치 | P3 | Low | S | 전 단계 | import 그래프 단순화(사이클 0) |

## 의존성 (핵심 흐름/크리티컬 패스)

### Phase 0: T0.1 → T0.2 → T0.3 → (T0.4 병행 가능)
### Phase 1: T1.1 → T1.2 → T1.3 → T1.4 → T1.5 (Scan 화면 기준)
### Phase 2: T2.1 → T2.3 → T2.4 (T2.2는 가속, T2.5는 병행)
### Phase 3: T3.1 → T3.2 → T3.3 → T3.4 → T3.5
### Phase 4: T4.1/T4.2/T4.3 → T4.4 → T4.5

**크리티컬 패스**: T0.1→T0.2→T0.3→T1.1→T1.2→T1.3→T1.4→T1.5→T2.1→T2.3→T2.4→T3.1→T3.2→T3.3→T3.4→T3.5

## 실행 보드 (스프린트/칸반)

### Sprint 1 (주 1)
- **P0**: T0.1, T0.2, T0.3, T1.1
- **P1**: T0.4(병행), T1.2
- **Done 기준**: PR 게이트/컨테이너 생성 및 단위 테스트 통과

### Sprint 2 (주 2)
- **P0**: T1.3
- **P1**: T1.4, T1.5
- **P1**: T1.6(ParserChain, 병행 가능)
- **Done 기준**: Scan 화면 MVVM 전환, UI 프리즈 제거

### Sprint 3 (주 3)
- **P1**: T2.1, T2.3
- **P2**: T2.2
- **Done 기준**: 주요 화면 VM 분리 및 모델화

### Sprint 4 (주 4)
- **P1**: T2.4
- **P2**: T2.5
- **Done 기준**: MVVM 전면 완료

### Sprint 5 (주 5)
- **P0**: T3.1, T3.2
- **P1**: T3.3
- **Done 기준**: Undo/Redo 인프라 완비

### Sprint 6 (주 6)
- **P1**: T3.4, T3.5
- **P2**: T4.1, T4.2, T4.3
- **P3**: T4.4, T4.5
- **Done 기준**: Command 경유 100%, 품질/문서 마감

## 관리 지표

기본은 **Priority(P) + Impact(I) + Effort(E)**로 관리.

필요 시 Score = (I 가중치 2) − Effort로 가볍게 수치화하여 칸반 정렬.

안정성 관련 항목(T3.*)은 Impact 가중치 상향.

## 체크리스트 (Definition of Done)

- **아키텍처**: View에 비즈니스 로직 없음, 서비스/클라이언트는 DI로 주입
- **이벤트**: UI 업데이트는 EventBus→ViewModel 시그널 경유만 허용
- **커맨드**: 파일 변경 경로는 100% Command 경유, Undo/Redo 동작
- **테스트**: 핵심 레이어(services/domain/platform) 커버리지 ≥ 90%
- **성능/UX**: 장시간 작업 중 UI 입력/애니메이션 정상, Busy 인디케이터 표시
- **문서**: 아키텍처/기여 가이드/테스트 가이드 갱신

## 주요 설계 디테일

### 1) Event 타입 (예시)
```python
@dataclass(frozen=True)
class FilesScanned:
    groups: list[MediaGroup]
    duration: float

@dataclass(frozen=True)
class MetadataSynced:
    groups: list[MediaGroup]
    failures: list[str]

@dataclass(frozen=True)
class FileOperationPlanned:
    ops: list[FileOperation]

@dataclass(frozen=True)
class FileOperationApplied:
    summary: OperationSummary

@dataclass(frozen=True)
class OperationFailed:
    message: str
    exc: Exception | None = None
```

### 2) 파일 시스템 안전성
- **저널링**: 모든 조작을 JSON 라인 로그로 남김
- **스테이징 디렉토리**: 실 파일 이동은 스테이징→커밋. Undo는 스테이징에서 복원
- **충돌 정책**: overwrite/rename 규칙을 정책 객체로 분리(테스트 가능)

### 3) ParserChain
Anitopy → GuessIt 폴백 체인 + 휴리스틱 스코어(가중치)로 최종 결정.

파서 출력은 Domain Entity로 수렴(MediaGroup, MediaFile).

### 4) 성능/비동기
QThreadPool + QRunnable 또는 qasync(선호)로 IO/네트워크를 비동기화.

UI 갱신은 EventBus → ViewModel 시그널 경유(스레드 안전).

## 일정 (보수적)

- **주 1–2**: Phase0–1 (도구/DI/EventBus/Scan MVVM)
- **주 3–4**: Phase2 (MVVM 전면 전환 + 바인딩 유틸)
- **주 5**: Phase3 (Command + Undo/Redo + 저널링/스테이징)
- **주 6**: Phase4 (설정/에러/로깅 + 문서화/청소)

## 기대 효과

- **유지보수성**: UI↔로직 분리로 변경 영향 축소
- **테스트성**: DI로 서비스/클라이언트 모킹 용이
- **안정성**: Undo/Redo + 저널링으로 안전한 파일 조작
- **확장성**: 이벤트로 기능 추가 시 결합도 최소화

## 부록: 최소 구현 스니펫

### EventBus
```python
# platform/event_bus.py
from typing import TypeVar, Callable, Any
from collections import defaultdict

T = TypeVar("T")

class EventBus:
    def __init__(self):
        self._subs: dict[type, list[Callable[[Any], None]]] = defaultdict(list)

    def publish(self, event: Any) -> None:
        for cb in list(self._subs.get(type(event), [])):
            cb(event)

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        self._subs[event_type].append(handler)
```

### 바인딩 유틸
```python
# platform/binding.py
from PyQt5.QtWidgets import QPushButton, QLineEdit
from PyQt5.QtCore import pyqtSignal

def bind_click(btn: QPushButton, vm_method: Callable[..., None]):
    btn.clicked.connect(vm_method)

def bind_text(line: QLineEdit, getter: Callable[[], str], setter: Callable[[str], None], changed: pyqtSignal):
    line.setText(getter())
    line.textChanged.connect(setter)
    changed.connect(lambda: line.setText(getter()))
```

## 마이그레이션/PR 쪼개기 (제안)

1. **Phase0-Tooling**: ruff/mypy/pytest/GHA 추가
2. **DI+EventBus 도입**: 컨테이너, 이벤트 타입만 추가—기존 경로 유지
3. **MainWindow 분해 ①**: Scan 화면만 MVVM 전환
4. **MainWindow 분해 ②**: Metadata/Settings 전환
5. **Command/Undo 인프라**: QUndoStack 브리지 + Move/Rename 명령
6. **FS 저널/스테이징**: 안전한 롤백 경로 확보
7. **오류·설정 통합**: ErrorBus, Settings, 로깅
8. **죽은 코드/직접 의존 제거**: 문서/개발자 가이드 업데이트

각 PR은 사용자 기능 회귀 없음을 전제로 작은 단위로 병합.
