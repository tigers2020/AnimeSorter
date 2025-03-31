# AnimeSorter (애니메이션 분류기)

애니메이션 메타데이터 파일을 분석하고 정리하는 도구입니다.

## 소개

이 프로젝트는 다음과 같은 기능을 제공합니다:

1. 메타데이터 파일 분석 (analyze_json.py)
   - 파일 내 장르, 키워드, 연도 등 다양한 정보 분석
   - 애니메이션과 비애니메이션 구분
   - 분석 결과를 CSV와 JSON 형식으로 저장

2. 샘플 메타데이터 생성 (create_json_samples.py)
   - 테스트를 위한 다양한 메타데이터 파일 생성
   - 원피스, 기타 인기 애니메이션, 비애니메이션 콘텐츠 포함

3. 파일 분류 및 정리 (src/main.py, src/file_manager.py)
   - 메타데이터 기반 파일 자동 분류
   - 연도, 장르 기반 체계적인 디렉토리 구조 생성

## 설치 방법

```bash
# 저장소 클론
git clone https://github.com/username/AnimeSorter.git
cd AnimeSorter

# 필요한 패키지 설치
pip install pandas
```

## 사용 방법

### 메타데이터 분석

JSON 메타데이터 파일을 분석하여 통계를 생성합니다:

```bash
python analyze_json.py
```

분석 결과는 `analysis` 폴더에 저장됩니다:
- `series_data.csv`: 모든, 시리즈 상세 정보
- `genres.csv`: 장르 통계
- `keywords.csv`: 키워드 통계
- `years.csv`: 연도별 통계
- `languages.csv`: 언어별 통계
- `summary.csv`: 전체 요약 통계
- `analysis_results.json`: 모든 분석 데이터가 포함된 JSON 파일

### 샘플 메타데이터 생성

테스트를 위한 샘플 메타데이터 파일을 생성합니다:

```bash
python create_json_samples.py
```

다음과 같은 샘플이 생성됩니다:
- 원피스 에피소드 (여러 버전)
- 기타 인기 애니메이션 (귀멸의 칼날, 진격의 거인, 나루토)
- 비애니메이션 콘텐츠 (킹덤, 하이에나)

### 파일 분류 실행

메타데이터 기반으로 파일을 분류합니다:

```bash
python -m src.main
```

## 파일 구조

```
AnimeSorter/
├── analyze_json.py         # 메타데이터 분석 도구
├── create_json_samples.py  # 샘플 메타데이터 생성 도구
├── src/
│   ├── main.py             # 메인 애플리케이션 코드
│   ├── file_manager.py     # 파일 처리 및 이동 로직
│   └── metadata.py         # 메타데이터 처리 로직
├── test_files/
│   ├── source/             # 원본 파일 저장 위치
│   └── target/             # 분류된 파일 저장 위치
└── analysis/               # 분석 결과 저장 위치
```

## 분석 결과 예시

애니메이션 메타데이터 분석 결과 요약:

- 총 파일 수: 19개
- 애니메이션 파일 수: 17개
- 비애니메이션 파일 수: 2개
- 평균 평점: 7.92점

## 기여 방법

1. 이 저장소를 포크합니다.
2. 새로운 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`).
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 생성합니다.

## 기능

- 애니메이션 파일명 정제 및 검색용 키워드 추출
- TMDB API를 통한 애니메이션 메타데이터 검색
- 검색 결과 기반으로 파일 자동 정리 및 분류
- 자막 파일 연동 처리
- 메타데이터 캐싱으로 재검색 방지

## 설정

`config.json` 파일에서 다음 설정을 변경할 수 있습니다:

- API 키 및 언어 설정
- 소스/대상 디렉토리 경로
- 폴더 구조 설정 (연도/장르별 분류 등)
- 파일 조작 설정 (이동/복사, 자막 처리 등)

## 라이선스

MIT License 