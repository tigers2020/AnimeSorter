# AnimeSorter 빠른 시작 가이드

## 🚀 5분 만에 시작하기

이 가이드는 AnimeSorter를 처음 사용하는 사용자를 위한 빠른 시작 안내서입니다.

## 📋 필수 요구사항

- **Python 3.8 이상**
- **인터넷 연결** (TMDB 메타데이터 검색용)
- **TMDB API 키** (무료로 발급 가능)

## ⚡ 빠른 설치

### 1. 저장소 다운로드
```bash
git clone https://github.com/yourusername/AnimeSorter.git
cd AnimeSorter
```

### 2. 가상환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. TMDB API 키 발급
1. [TMDB 웹사이트](https://www.themoviedb.org/settings/api) 접속
2. 계정 생성 또는 로그인
3. API 키 발급 (무료)
4. 발급받은 API 키 복사

## 🎯 첫 실행

### 1. 애플리케이션 시작
```bash
python src/main.py
```

### 2. API 키 설정
- 애플리케이션 시작 후 **설정** 버튼 클릭
- **TMDB** 탭에서 API 키 입력
- **확인** 버튼 클릭

### 3. 폴더 선택
- **폴더 선택** 버튼 클릭
- 정리할 애니메이션 파일이 있는 폴더 선택

### 4. 자동 처리
- 애플리케이션이 자동으로 파일을 스캔하고 파싱
- TMDB에서 메타데이터 검색
- 검색 결과에서 올바른 항목 선택

### 5. 파일 정리
- **정리 시작** 버튼 클릭
- 파일이 설정된 폴더로 자동 정리

## 📁 파일명 형식 예제

AnimeSorter는 다양한 파일명 형식을 지원합니다:

### 지원되는 형식
```
Attack on Titan S01E01.mkv
Attack.on.Titan.S01E01.1080p.mkv
Attack_on_Titan_S01E01_1080p.mkv
Attack on Titan - S01E01 - Episode Title.mkv
Attack on Titan Season 1 Episode 01.mkv
```

### 권장 형식
```
제목 S01E01 - 에피소드명.mkv
```

## ⚙️ 기본 설정

### 파일 정리 설정
- **대상 폴더**: 정리된 파일이 저장될 폴더
- **정리 모드**: 이동 (기본값)
- **파일명 방식**: Standard (기본값)

### 안전 모드
- **기본값**: 활성화
- **기능**: 파일 이동 전 자동 백업
- **권장**: 항상 활성화 유지

## 🔧 문제 해결

### 일반적인 문제

#### 1. "TMDB API 키가 설정되지 않았습니다"
**해결방법**: 설정에서 TMDB API 키를 입력하세요.

#### 2. 파일이 파싱되지 않음
**해결방법**: 파일명이 "제목 S01E01" 형식인지 확인하세요.

#### 3. 검색 결과가 없음
**해결방법**: 
- 영문 제목으로 검색해보세요
- 검색어를 수정해보세요
- 다른 검색어로 재검색해보세요

## 📚 다음 단계

기본 사용법을 익혔다면 다음 문서들을 참조하세요:

- **[사용자 가이드](USER_GUIDE.md)**: 상세한 기능 설명
- **[문제 해결](USER_GUIDE.md#문제-해결)**: 고급 문제 해결 방법
- **[설정 가이드](USER_GUIDE.md#설정)**: 고급 설정 옵션

## 🆘 도움말

문제가 발생하면 다음을 확인하세요:

1. **로그 파일**: `logs/animesorter_YYYYMMDD.log`
2. **설정 확인**: 모든 필수 설정이 올바르게 입력되었는지 확인
3. **파일 권한**: 대상 폴더에 쓰기 권한이 있는지 확인

---

**버전**: 2.0.0  
**최종 업데이트**: 2024년 12월
