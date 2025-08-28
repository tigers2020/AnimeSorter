# AnimeSorter 파일 파싱 및 검색, 이동 알고리즘 개선 방안 리포트

## 📋 실행 요약

AnimeSorter의 파일 파싱, 검색, 이동 알고리즘을 분석한 결과, **중복 코드**, **책임 분산**, **일관성 부족** 등의 문제점을 발견했습니다. 이 리포트는 이러한 문제점들을 해결하고 코드 품질을 향상시키기 위한 구체적인 개선 방안을 제시합니다.

## 🔍 현재 상태 분석

### 1. 파일 관리 관련 클래스 구조

#### Core 레이어
- `FileManager` - 파일 정리, 이동, 복사 작업 관리
- `FileParser` - 애니메이션 파일명 파싱 엔진
- `FileHandler` - 기본 파일 작업 (복사, 이동, 이름 변경)
- `FileBackupManager` - 백업 관리
- `FileNamingManager` - 파일명 생성 규칙
- `FileValidator` - 파일 유효성 검사

#### GUI 레이어
- `FileProcessingManager` - 파일 처리 계획 수립 및 실행
- `AnimeDataManager` - 파싱된 애니메이션 데이터 관리
- `FileService` - GUI용 파일 서비스

#### App 서비스 레이어
- `FileOrganizationService` - 파일 정리 백그라운드 작업
- `FileScanService` - 파일 스캔 백그라운드 작업

### 2. 주요 문제점

#### 2.1 중복 코드 (Code Duplication)
- **파일 이동/복사 로직 중복**: `FileHandler`, `FileService`, `FileOrganizationTask`, `FileOrganizeWorker` 등에서 동일한 로직 반복
- **백업 생성 로직 중복**: 여러 클래스에서 비슷한 백업 로직 구현
- **디렉토리 생성 로직 중복**: `Path(destination).parent.mkdir(parents=True, exist_ok=True)` 패턴이 여러 곳에 반복

#### 2.2 책임 분산 (Responsibility Scattering)
- **파일 처리 책임 분산**: `FileManager`, `FileProcessingManager`, `FileOrganizationService`가 유사한 책임을 가짐
- **스캔 로직 분산**: `FileProcessingManager.scan_directory()`, `FileScanService.scan_directory()` 등이 동일한 기능 제공
- **파싱 로직 분산**: `FileParser`와 `AnimeDataManager`에서 파싱 관련 로직이 중복

#### 2.3 일관성 부족 (Inconsistency)
- **에러 처리 방식 불일치**: 일부는 `FileOperationResult` 반환, 일부는 예외 발생, 일부는 로깅만
- **백업 정책 불일치**: 안전 모드 설정이 클래스마다 다르게 적용
- **진행률 보고 방식 불일치**: 콜백, 이벤트, 시그널 등 다양한 방식 혼재

#### 2.4 성능 문제 (Performance Issues)
- **중복 파일 스캔**: 동일한 디렉토리를 여러 번 스캔하는 경우 발생
- **메모리 사용량**: 파싱 결과를 여러 곳에 중복 저장
- **캐시 미사용**: `FileParser`의 캐시 기능이 실제로 활용되지 않음

## 🚀 개선 방안

### 1. 아키텍처 재설계 (Architecture Redesign)

#### 1.1 계층별 책임 명확화
```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ MainWindow      │  │ ProgressDialog  │  │ Settings    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ FileOrchestrator│  │ ScanOrchestrator│  │ ParseOrche- │ │
│  │                 │  │                 │  │ strator     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ FileManager     │  │ FileParser      │  │ FileScanner │ │
│  │ (Unified)       │  │ (Enhanced)      │  │ (Unified)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 핵심 서비스 통합
- **`FileOrchestrator`**: 모든 파일 작업을 조율하는 단일 진입점
- **`ScanOrchestrator`**: 파일 스캔 작업을 통합 관리
- **`ParseOrchestrator`**: 파일 파싱 작업을 통합 관리

### 2. 중복 코드 제거 (Code Deduplication)

#### 2.1 공통 파일 작업 모듈 생성
```python
# src/core/file_operations.py
class FileOperations:
    """공통 파일 작업을 담당하는 유틸리티 클래스"""

    @staticmethod
    def safe_move_file(source: Path, destination: Path,
                      backup_manager: FileBackupManager) -> FileOperationResult:
        """안전한 파일 이동 (백업 포함)"""
        pass

    @staticmethod
    def safe_copy_file(source: Path, destination: Path,
                      backup_manager: FileBackupManager) -> FileOperationResult:
        """안전한 파일 복사 (백업 포함)"""
        pass

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """디렉토리 존재 확인 및 생성"""
        pass
```

#### 2.2 백업 정책 통합
```python
# src/core/backup_policy.py
class BackupPolicy:
    """통합된 백업 정책 관리"""

    def __init__(self, config: BackupConfig):
        self.config = config

    def should_create_backup(self, operation: str, file_size: int) -> bool:
        """백업 생성 여부 결정"""
        pass

    def create_backup(self, file_path: Path, operation_id: str) -> Path:
        """백업 생성"""
        pass
```

### 3. 성능 최적화 (Performance Optimization)

#### 3.1 스마트 캐싱 시스템
```python
# src/core/caching/file_cache.py
class FileCache:
    """파일 관련 정보를 캐싱하는 시스템"""

    def __init__(self, max_size: int = 1000):
        self.cache = LRUCache(max_size)

    def get_parsed_metadata(self, file_path: str) -> ParsedMetadata | None:
        """파싱된 메타데이터 캐시 조회"""
        pass

    def get_file_info(self, file_path: str) -> FileInfo | None:
        """파일 정보 캐시 조회"""
        pass
```

#### 3.2 배치 처리 최적화
```python
# src/core/batch_processor.py
class BatchProcessor:
    """파일 작업을 배치로 처리하여 성능 향상"""

    def __init__(self, max_batch_size: int = 100):
        self.max_batch_size = max_batch_size

    def process_files(self, files: list[Path],
                     operation: Callable) -> list[FileOperationResult]:
        """파일들을 배치로 처리"""
        pass
```

### 4. 에러 처리 및 로깅 표준화 (Error Handling & Logging Standardization)

#### 4.1 통합된 에러 처리 전략
```python
# src/core/error_handling.py
class FileOperationError(Exception):
    """파일 작업 관련 예외의 기본 클래스"""
    pass

class FileNotFoundError(FileOperationError):
    """파일을 찾을 수 없는 경우"""
    pass

class FileOperationResult:
    """모든 파일 작업의 결과를 표준화된 형태로 반환"""

    def __init__(self, success: bool, **kwargs):
        self.success = success
        self.error_code = kwargs.get('error_code')
        self.error_message = kwargs.get('error_message')
        self.retry_after = kwargs.get('retry_after')
```

#### 4.2 구조화된 로깅
```python
# src/core/logging/structured_logger.py
class StructuredLogger:
    """구조화된 로깅을 제공하는 클래스"""

    def log_file_operation(self, operation: str, source: Path,
                          destination: Path, result: FileOperationResult):
        """파일 작업 로깅"""
        pass

    def log_scan_progress(self, scanned: int, total: int,
                         current_file: Path):
        """스캔 진행률 로깅"""
        pass
```

### 5. 설정 관리 통합 (Configuration Management Integration)

#### 5.1 중앙화된 설정 시스템
```python
# src/core/config/file_config.py
class FileConfig:
    """파일 작업 관련 설정을 중앙에서 관리"""

    def __init__(self):
        self.safe_mode = True
        self.backup_enabled = True
        self.max_file_size = 50 * 1024 * 1024 * 1024  # 50GB
        self.supported_extensions = {'.mkv', '.mp4', '.avi', '.mov'}
        self.naming_scheme = 'standard'
        self.create_directories = True
        self.overwrite_existing = False
```

## 📝 구현 계획 (Implementation Plan)

### Phase 1: 기반 구조 정리 (1-2주)
1. **공통 모듈 생성**
   - `FileOperations` 유틸리티 클래스
   - `BackupPolicy` 통합 클래스
   - `FileCache` 캐싱 시스템

2. **기존 코드 분석 및 중복 식별**
   - 중복 메서드 매핑
   - 책임 분산 현황 파악
   - 성능 병목 지점 식별

### Phase 2: 핵심 서비스 통합 (2-3주)
1. **`FileOrchestrator` 구현**
   - 기존 `FileManager`, `FileProcessingManager` 통합
   - 단일 진입점으로 모든 파일 작업 조율

2. **`ScanOrchestrator` 구현**
   - 기존 `FileScanService` 통합
   - 중복 스캔 방지 및 스마트 캐싱

3. **`ParseOrchestrator` 구현**
   - 기존 `FileParser`와 `AnimeDataManager` 통합
   - 파싱 결과 캐싱 및 재사용

### Phase 3: 성능 최적화 (1-2주)
1. **배치 처리 시스템 구현**
   - 대용량 파일 목록 처리 최적화
   - 메모리 사용량 최적화

2. **캐싱 시스템 활성화**
   - 파싱 결과 캐싱
   - 파일 정보 캐싱
   - LRU 캐시 정책 적용

### Phase 4: 테스트 및 검증 (1주)
1. **통합 테스트 작성**
   - 새로운 아키텍처 테스트
   - 성능 향상 검증
   - 기존 기능 호환성 확인

2. **성능 벤치마크**
   - 파일 스캔 속도 측정
   - 메모리 사용량 측정
   - 처리량 향상 확인

## 🎯 기대 효과 (Expected Benefits)

### 1. 코드 품질 향상
- **중복 코드 제거**: 약 30-40% 코드량 감소 예상
- **유지보수성 향상**: 단일 책임 원칙 적용으로 수정 시 영향 범위 최소화
- **가독성 향상**: 명확한 계층 구조와 책임 분리

### 2. 성능 향상
- **스캔 속도**: 캐싱과 배치 처리로 2-3배 향상 예상
- **메모리 효율성**: 중복 데이터 제거로 20-30% 메모리 사용량 감소
- **처리량**: 배치 처리로 대용량 파일 목록 처리 시간 단축

### 3. 안정성 향상
- **에러 처리 일관성**: 표준화된 에러 처리로 예측 가능한 동작
- **백업 정책 통합**: 일관된 백업 정책으로 데이터 안전성 향상
- **로깅 표준화**: 구조화된 로깅으로 디버깅 및 모니터링 개선

## ⚠️ 주의사항 및 리스크 (Considerations & Risks)

### 1. 마이그레이션 리스크
- **기존 코드 호환성**: 기존 API 변경 시 하위 호환성 보장 필요
- **데이터 마이그레이션**: 기존 캐시나 설정 데이터 마이그레이션 계획 필요

### 2. 성능 리스크
- **초기 구현 오버헤드**: 새로운 아키텍처 초기 구현 시 성능 저하 가능성
- **캐시 메모리 사용량**: 캐시 크기 조정이 필요할 수 있음

### 3. 테스트 커버리지
- **기존 기능 테스트**: 리팩토링 후 모든 기존 기능이 정상 작동하는지 확인 필요
- **성능 테스트**: 다양한 파일 크기와 수량에 대한 성능 테스트 필요

## 📊 우선순위 및 일정 (Priority & Timeline)

### High Priority (즉시 시작)
1. **중복 코드 식별 및 매핑** (1주)
2. **공통 모듈 생성** (1주)
3. **기본 통합 구조 설계** (1주)

### Medium Priority (1-2개월 내)
1. **핵심 서비스 통합** (3-4주)
2. **성능 최적화** (2-3주)
3. **테스트 및 검증** (1-2주)

### Low Priority (3-6개월 내)
1. **고급 기능 추가** (캐시 정책, 배치 처리 최적화)
2. **모니터링 및 메트릭** 추가
3. **문서화 및 가이드** 작성

## 🏁 결론 (Conclusion)

AnimeSorter의 파일 파싱, 검색, 이동 알고리즘은 현재 **중복 코드**, **책임 분산**, **일관성 부족** 등의 문제로 인해 유지보수성과 성능이 저하되고 있습니다.

제안된 개선 방안을 통해 **아키텍처 재설계**, **중복 코드 제거**, **성능 최적화**를 단계적으로 구현하면, 코드 품질과 성능을 크게 향상시킬 수 있을 것으로 예상됩니다.

특히 **`FileOrchestrator`**를 중심으로 한 통합 아키텍처는 기존의 복잡하고 분산된 구조를 단순하고 일관된 구조로 개선하여, 향후 기능 확장과 유지보수를 훨씬 쉽게 만들 것입니다.

이 개선 작업은 **점진적 접근**을 통해 리스크를 최소화하면서 진행하는 것을 권장하며, 각 단계마다 충분한 테스트와 검증을 거쳐 안정성을 보장해야 합니다.
