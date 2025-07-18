# AnimeSorter

애니메이션 파일을 자동으로 분류하고 정리하는 도구입니다.

## 주요 기능

- **파일명 정제**: 복잡한 애니메이션 파일명에서 제목, 시즌, 에피소드 정보 추출
- **메타데이터 검색**: TMDB API를 통한 메타데이터 조회
- **자동 분류**: 메타데이터 기반으로 체계적인 폴더 구조 생성
- **자막 연동**: 비디오 파일과 관련된 자막 파일 함께 이동
- **캐싱**: API 중복 호출 방지를 위한 로컬 캐싱

## 시작하기

### 필수 조건

- Python 3.9 이상
- TMDB API 키 ([TMDB 사이트](https://www.themoviedb.org/)에서 발급)

### 설치

1. 저장소 클론
   ```
   git clone https://github.com/yourusername/AnimeSorter.git
   cd AnimeSorter
   ```

2. 가상 환경 생성 및 활성화
   ```
   conda create -n animesorter python=3.12
   conda activate animesorter
   ```

3. 필요한 패키지 설치
   ```
   pip install -r requirements.txt
   ```

4. 설정 파일 수정 (선택사항)
   - `config.yaml` 파일을 열어 TMDB API 키와 소스/대상 디렉토리 설정
   - 또는 환경 변수 `TMDB_API_KEY`로 API 키 설정

### 사용법

기본 사용법:
```
python main.py
```

## 설정 옵션

### 설정 방법

#### 1. 외부 설정 파일 (기본)
`config.yaml` 파일에서 다양한 설정을 변경할 수 있습니다:

#### 2. 내장 설정 (권장)
- 외부 파일 없이 애플리케이션 내부에 설정 포함
- exe 파일에 모든 설정이 포함됨

#### 3. 환경 변수
- `TMDB_API_KEY` 또는 `ANIMESORTER_API_KEY` 환경 변수로 API 키 설정
- 가장 안전한 방법

### API 키 설정 방법

#### 방법 1: 코드에 직접 포함 (개발용)
```python
# src/config/config_manager.py에서
DEFAULT_API_KEY = "your_actual_tmdb_api_key_here"
```

#### 방법 2: 환경 변수 사용 (권장)
```bash
# Windows
set TMDB_API_KEY=your_api_key_here

# Linux/Mac
export TMDB_API_KEY=your_api_key_here
```

#### 방법 3: 설정 대화상자에서 입력
- 애플리케이션 실행 후 "설정" 메뉴에서 API 키 입력

### 설정 옵션

```yaml
# API 키 설정
api_key: "your_tmdb_api_key"

# 언어 설정
language: "ko-KR"

# 디렉토리 설정
source_dir: "C:/Users/Downloads"  # 소스 디렉토리
target_dir: "C:/Users/Videos/Anime"  # 대상 디렉토리

# 폴더 구조 설정
folder_template: "{title} ({year})"  # 폴더 템플릿

# 파일 처리 설정
keep_original_name: true  # 원본 파일명 유지 여부
overwrite_existing: false  # 기존 파일 덮어쓰기 여부 (true: 덮어쓰기, false: 파일명 변경)

# 로깅 설정
log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 폴더 구조 템플릿

폴더 이름 템플릿에 사용할 수 있는 변수:

- `{title}`: 제목
- `{year}`: 연도
- `{type}`: 미디어 타입 (TV Show/Movie)

## 파일 중복 처리

AnimeSorter는 파일 이동 시 중복 파일을 다음과 같이 처리합니다:

### 폴더 중복
- 폴더가 이미 존재하면 자동으로 기존 폴더를 사용
- 상위 디렉토리가 없으면 자동 생성

### 파일 중복
- **덮어쓰기 비활성화** (기본값): 파일명에 `(1)`, `(2)` 등을 추가하여 중복 방지
  - 예: `anime.mp4` → `anime (1).mp4`
- **덮어쓰기 활성화**: 기존 파일을 덮어쓰기
- 설정은 `config.yaml`의 `overwrite_existing` 옵션이나 UI 설정에서 변경 가능

## 라이선스

MIT 라이선스

## 기여하기

이슈나 PR을 통해 기여해주세요. 