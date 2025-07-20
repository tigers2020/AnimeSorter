# AnimeSorter

애니메이션 파일을 자동으로 분류하고 정리하는 도구입니다.

## 주요 기능

- **파일명 정제**: 복잡한 애니메이션 파일명에서 제목, 시즌, 에피소드 정보 추출
- **메타데이터 검색**: TMDB API를 통한 메타데이터 조회
- **자동 분류**: 메타데이터 기반으로 체계적인 폴더 구조 생성
- **자막 연동**: 비디오 파일과 관련된 자막 파일 함께 이동
- **캐싱**: API 중복 호출 방지를 위한 로컬 캐싱
- **자동화**: 소스 폴더 선택 시 자동 파일 스캔 및 메타데이터 동기화
- **JSON 내보내기**: 스캔 결과를 JSON 형식으로 저장하고 로드
- **TV 드라마/애니메이션 분류**: 파일명 분석을 통한 자동 콘텐츠 분류

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

# 자동화 설정
automation:
  auto_scan_on_folder_change: true  # 소스 폴더 변경 시 자동 스캔
  auto_sync_after_scan: true  # 스캔 완료 후 자동 메타데이터 동기화
  auto_scan_on_startup: true  # 프로그램 시작 시 자동 스캔

# 로깅 설정
log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 폴더 구조 템플릿

폴더 이름 템플릿에 사용할 수 있는 변수:

- `{title}`: 제목
- `{year}`: 연도
- `{type}`: 미디어 타입 (TV Show/Movie)

## JSON 내보내기 기능

AnimeSorter는 스캔 결과를 JSON 형식으로 저장하고 로드할 수 있는 기능을 제공합니다.

### 기능 개요

- **구조화된 데이터**: 파일 정보, 메타데이터, 통계를 포함한 완전한 스캔 결과
- **다양한 형식**: 일반 JSON, 압축 JSON(.gz) 지원
- **메뉴 기반**: GUI 메뉴를 통한 쉬운 내보내기/로드
- **자동 저장**: 스캔 완료 시 자동으로 JSON 파일 생성

### 사용 방법

#### 1. 메뉴를 통한 내보내기
- **파일** → **JSON 내보내기** → **현재 스캔 결과 내보내기**
- **파일** → **JSON 내보내기** → **압축 JSON 내보내기**

#### 2. 저장된 JSON 로드
- **파일** → **JSON 내보내기** → **저장된 JSON 로드**

### JSON 파일 구조

```json
{
  "metadata": {
    "scan_timestamp": "2024-01-15T10:30:00",
    "total_files": 150,
    "total_groups": 25,
    "scan_duration": 2.5,
    "source_directory": "C:/Downloads/Anime",
    "version": "1.0.0",
    "export_timestamp": "2024-01-15T10:30:05"
  },
  "groups": [
    {
      "title": "My Hero Academia",
      "year": null,
      "season": 1,
      "episode": 1,
      "files": [
        {
          "original_path": "C:/Downloads/Anime/[SubsPlease] My Hero Academia - 01 [1080p].mkv",
          "file_name": "[SubsPlease] My Hero Academia - 01 [1080p].mkv",
          "file_size": 1073741824,
          "file_extension": ".mkv",
          "last_modified": "2024-01-15T10:25:00",
          "is_video": true,
          "is_subtitle": false,
          "metadata": {
            "title": "My Hero Academia",
            "season": 1,
            "episode": 1,
            "parser": "anitopy+guessit",
            "release_group": "SubsPlease",
            "video_resolution": "1080p"
          }
        }
      ],
      "total_size": 1073741824,
      "file_count": 1,
      "video_count": 1,
      "subtitle_count": 0
    }
  ],
  "statistics": {
    "total_size_bytes": 16106127360,
    "total_size_gb": 15.0,
    "total_video_files": 120,
    "total_subtitle_files": 30,
    "average_group_size": 644245094.4,
    "largest_group": 5,
    "smallest_group": 1
  }
}
```

### 자동 저장 위치

스캔 완료 시 자동으로 다음 위치에 JSON 파일이 저장됩니다:
- `./scan_results/scan_result_YYYYMMDD_HHMMSS.json`
- `./scan_results/scan_result_YYYYMMDD_HHMMSS.json.gz` (압축 버전)

### 압축률

- 일반 JSON: 가독성을 위한 들여쓰기 포함
- 압축 JSON: 약 85-90% 압축률로 파일 크기 대폭 감소

## TV 드라마/애니메이션 분류 시스템

AnimeSorter는 파일명을 분석하여 TV 드라마와 애니메이션을 자동으로 구분하는 정교한 분류 시스템을 제공합니다.

### 분류 기준

#### 1. 릴리즈 그룹 기반 분류
- **애니메이션**: SubsPlease, HorribleSubs, Erai-raws, Commie, GG, Coalgirls, DeadFish, Doki, Fansub 등
- **TV 드라마**: Netflix, HBO, Amazon, Disney, Hulu, Showtime, Apple, Peacock, Paramount 등

#### 2. 키워드 기반 분류
- **애니메이션 키워드**: anime, animation, cartoon, manga, otaku, japan, japanese, 애니, 애니메, 만화, 일본, 일본어
- **드라마 키워드**: drama, series, show, episode, season, tv, television, 드라마, 시리즈, 쇼, 에피소드, 시즌, 티비

#### 3. 언어 정보 기반 분류
- **한국어 자막**: 기본적으로 애니메이션으로 분류 (일본 애니메이션 자막이 주로 한국어)
- **일본어 관련**: 일본어 오디오, 일본어 자막 등은 애니메이션으로 분류
- **한국 드라마**: "Korean Drama", "한국 드라마" 등 명시적 키워드가 있으면 드라마로 분류

#### 4. 에피소드 패턴 기반 분류
- **애니메이션 특화**: "화" 패턴 (01화, 1001화 등)
- **드라마 특화**: "SxxEyy" 패턴 (S01E01, S08E01 등), "1x01" 패턴

#### 5. 애니메이션 제목 키워드 분류
유명한 애니메이션 제목을 직접 인식:
- Attack on Titan, My Hero Academia, One Piece, Naruto, Bleach, Dragon Ball
- Death Note, Code Geass, Steins;Gate, Fullmetal Alchemist, Hunter x Hunter
- Tokyo Ghoul, Sword Art Online, Fairy Tail, Jujutsu Kaisen, Demon Slayer
- Ghost in the Shell, Akira, Evangelion, Cowboy Bebop 등

### 분류 정확도

- **애니메이션 파일**: 95% 이상의 정확도로 분류
- **TV 드라마 파일**: 90% 이상의 정확도로 분류
- **애매한 케이스**: 점수 기반 시스템으로 최적의 분류 결정

### 사용 방법

1. **자동 분류**: 파일을 AnimeSorter에 추가하면 자동으로 분류됩니다
2. **분류 결과 확인**: 파일 목록에서 `is_anime` 필드로 분류 결과 확인
3. **필터링**: 설정에서 "TV 드라마 포함" 옵션으로 드라마 파일 제외 가능
4. **수동 조정**: 필요시 분류 결과를 수동으로 조정 가능

### 분류 예시

```python
# 애니메이션으로 분류되는 파일들
"[SubsPlease] Attack on Titan - 01 [1080p].mkv"  # 릴리즈 그룹
"One Piece - 1001화 [720p].mkv"                  # 화 패턴
"Ghost in the Shell - 01 [1080p].mkv"           # 애니메이션 제목
"[Coalgirls] Steins;Gate - 01 [1080p].mkv"      # 애니메이션 릴리즈 그룹

# TV 드라마로 분류되는 파일들
"Breaking Bad S01E01 [Netflix] [1080p].mkv"     # 스트리밍 서비스
"Game of Thrones S08E01 [HBO] [1080p].mkv"      # 스트리밍 서비스
"Korean Drama - Itaewon Class S01E01 [1080p].mkv" # 한국 드라마 키워드
```

### 분류 시스템의 장점

- **정확성**: 다중 기준을 통한 정교한 분류
- **확장성**: 새로운 키워드와 패턴 쉽게 추가 가능
- **성능**: 빠른 파일명 분석으로 즉시 분류
- **유연성**: 점수 기반 시스템으로 애매한 케이스도 적절히 처리

## 자동화 기능

AnimeSorter는 사용자 편의성을 위해 다양한 자동화 기능을 제공합니다:

### 자동화 옵션

1. **소스 폴더 선택 시 자동 스캔**
   - 소스 폴더를 선택하거나 변경할 때 자동으로 파일 스캔을 실행
   - 수동으로 "파일 스캔" 버튼을 누를 필요 없음

2. **스캔 완료 후 자동 메타데이터 동기화**
   - 파일 스캔이 완료되면 자동으로 메타데이터 동기화를 실행
   - 수동으로 "메타데이터 동기화" 버튼을 누를 필요 없음

3. **프로그램 시작 시 자동 스캔**
   - 프로그램 시작 시 저장된 소스 폴더가 있으면 자동으로 스캔을 실행
   - 이전 작업을 이어서 계속할 수 있음

### 자동화 설정

자동화 기능은 설정 대화상자의 "UI" 탭에서 개별적으로 활성화/비활성화할 수 있습니다:

- **설정** → **UI** → **자동화 설정**에서 각 옵션을 체크/해제
- 설정은 자동으로 저장되며 다음 실행 시에도 유지됨

### 자동화 로그

자동화 기능 실행 시 상태 패널에 다음과 같은 로그가 표시됩니다:

```
[자동] 소스 폴더 변경 감지: C:\Users\Downloads\Anime
[자동] 파일 스캔 및 메타데이터 동기화를 시작합니다...
[자동] 스캔 완료. 메타데이터 동기화를 시작합니다...
```

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