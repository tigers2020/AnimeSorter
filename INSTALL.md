# 🚀 AnimeSorter 설치 가이드

## 📋 시스템 요구사항

### 필수 요구사항
- **Python**: 3.8 이상 (3.10 권장)
- **운영체제**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **메모리**: 최소 4GB RAM (8GB 권장)
- **저장공간**: 최소 1GB 여유 공간

### 권장 사양
- **CPU**: Intel i5/AMD Ryzen 5 이상
- **메모리**: 8GB RAM 이상
- **네트워크**: 안정적인 인터넷 연결 (TMDB API 사용)

## 🔧 설치 방법

### 1. Python 설치

#### Windows
1. [Python 공식 사이트](https://www.python.org/downloads/)에서 Python 3.10 이상 다운로드
2. 설치 시 "Add Python to PATH" 옵션 체크
3. 설치 완료 후 명령 프롬프트에서 확인:
   ```bash
   python --version
   ```

#### macOS
```bash
# Homebrew 사용
brew install python@3.10

# 또는 Python.org에서 다운로드
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv
```

### 2. 프로젝트 다운로드

```bash
# Git 사용
git clone https://github.com/your-username/AnimeSorter.git
cd AnimeSorter

# 또는 ZIP 다운로드 후 압축 해제
```

### 3. 가상환경 생성 (권장)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. 의존성 설치

#### 최소 설치 (실행용)
```bash
pip install -r requirements-minimal.txt
```

#### 전체 설치 (개발용)
```bash
pip install -r requirements.txt
```

#### 개발 도구 포함
```bash
pip install -r requirements-dev.txt
```

## 🔑 TMDB API 키 설정

1. [TMDB 웹사이트](https://www.themoviedb.org/)에서 계정 생성
2. [API 설정 페이지](https://www.themoviedb.org/settings/api)에서 API 키 발급
3. 다음 방법 중 하나로 API 키 설정:

### 방법 1: 환경 변수 (권장)
```bash
# Windows
set TMDB_API_KEY=your_api_key_here

# macOS/Linux
export TMDB_API_KEY=your_api_key_here
```

### 방법 2: 설정 파일
`config/animesorter_config.yaml` 파일에서 설정:
```yaml
tmdb:
  api_key: your_api_key_here
```

## 🚀 실행

```bash
# 기본 실행
python main.py

# 도움말 보기
python main.py --help

# 디버그 모드
python main.py --debug
```

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트만 실행
pytest tests/test_file_cleaner.py

# 커버리지 포함 테스트
pytest --cov=src
```

## 📦 배포용 실행 파일 생성

```bash
# PyInstaller 설치
pip install pyinstaller

# 실행 파일 생성
pyinstaller --onefile --windowed main.py

# 생성된 실행 파일은 dist/ 폴더에 위치
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. PyQt6 설치 오류
```bash
# Windows에서 Visual C++ 빌드 도구 필요
# Visual Studio Build Tools 설치 후 재시도
```

#### 2. TMDB API 오류
- API 키가 올바른지 확인
- 인터넷 연결 상태 확인
- API 사용량 한도 확인

#### 3. 파일 권한 오류
- 관리자 권한으로 실행
- 폴더 쓰기 권한 확인

#### 4. 메모리 부족
- 대용량 폴더 처리 시 배치 크기 조정
- 가상 메모리 증가

### 로그 확인

```bash
# 로그 파일 위치
logs/animesorter.log

# 실시간 로그 확인
tail -f logs/animesorter.log
```

## 📚 추가 정보

- [사용자 가이드](docs/USER_GUIDE.md)
- [개발자 문서](docs/DEVELOPER_GUIDE.md)
- [FAQ](docs/FAQ.md)
- [문제 해결](docs/TROUBLESHOOTING.md)

## 🤝 지원

- **Issues**: [GitHub Issues](https://github.com/your-username/AnimeSorter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/AnimeSorter/discussions)
- **Wiki**: [GitHub Wiki](https://github.com/your-username/AnimeSorter/wiki)

---

**버전**: 1.0.0  
**최종 업데이트**: 2024년 1월  
**라이선스**: MIT License 