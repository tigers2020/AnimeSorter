# AnimeSorter

AnimeSorter는 애니메이션 파일을 자동으로 정리하고 메타데이터를 관리하는 Python 기반 도구입니다.

## 🚀 주요 기능

- **파일명 파싱**: 다양한 형식의 애니메이션 파일명을 자동으로 파싱
- **TMDB 통합**: The Movie Database API를 통한 메타데이터 검색
- **다중 해상도 지원**: 1080p, 720p 등 다양한 해상도 파일 처리
- **안전 모드**: 파일 이동 전 백업 및 롤백 기능
- **GUI**: 그래픽 사용자 인터페이스 제공
- **플러그인 시스템**: 확장 가능한 메타데이터 제공자 시스템

## 📋 요구사항

- Python 3.8+
- PyQt5 (GUI)
- tmdbsimple (TMDB API)
- 기타 의존성은 `requirements.txt` 참조

## 🛠️ 설치

```bash
# 저장소 클론
git clone https://github.com/yourusername/AnimeSorter.git
cd AnimeSorter

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

## 🚀 사용법

### GUI 모드
```bash
python src/main.py --gui
```

## 📚 문서

### 사용자 가이드
- [사용자 가이드](documents/USER_GUIDE.md) - 애플리케이션 사용법 및 기능 설명
- [문제 해결](documents/USER_GUIDE.md#문제-해결) - 일반적인 문제 해결 방법
- [FAQ](documents/USER_GUIDE.md#faq) - 자주 묻는 질문

### 개발자 문서
- [개발자 가이드](documents/DEVELOPER_GUIDE.md) - 개발 환경 설정 및 코드 스타일
- [API 참조](documents/API_REFERENCE.md) - 모든 공개 API 문서
- [플러그인 개발](documents/DEVELOPER_GUIDE.md#플러그인-개발) - 플러그인 시스템 가이드

### 프로젝트 문서
- [개발 계획](documents/DEVELOPMENT_PLAN.md) - 프로젝트 개발 계획
- [개발 일정](documents/DEVELOPMENT_SCHEDULE.md) - 개발 일정 및 마일스톤

## 🧪 테스트

### 모든 테스트 실행
```bash
python run_tests.py
```

### 특정 테스트 실행
```bash
python run_tests.py test_file_manager
python run_tests.py test_file_parser
python run_tests.py test_tmdb_client
```

### 개별 테스트 파일 실행
```bash
python tests/test_file_manager.py
python tests/test_file_parser.py
python tests/test_tmdb_client.py
```

## 📁 프로젝트 구조

```
AnimeSorter/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 기능
│   │   ├── file_parser.py        # 파일명 파싱 엔진
│   │   ├── file_manager.py       # 파일 관리 및 정리
│   │   ├── tmdb_client.py        # TMDB API 클라이언트
│   │   └── unified_config.py     # 설정 관리
│   ├── gui/               # GUI 컴포넌트
│   │   ├── main_window.py        # 메인 윈도우
│   │   ├── components/           # UI 컴포넌트
│   │   ├── managers/             # GUI 관리자
│   │   └── table_models.py       # 테이블 모델
│   └── plugins/           # 플러그인 시스템
│       ├── base.py               # 플러그인 기본 클래스
│       └── providers/            # 메타데이터 제공자
├── tests/                 # 테스트 코드
│   ├── test_file_manager.py
│   ├── test_file_parser.py
│   ├── test_tmdb_client.py
│   └── ... (기타 테스트 파일들)
├── documents/             # 문서
│   ├── USER_GUIDE.md      # 사용자 가이드
│   ├── DEVELOPER_GUIDE.md # 개발자 가이드
│   ├── API_REFERENCE.md   # API 참조
│   ├── DEVELOPMENT_PLAN.md # 개발 계획
│   └── DEVELOPMENT_SCHEDULE.md # 개발 일정
├── requirements.txt       # 의존성
├── run_tests.py          # 테스트 실행 스크립트
└── README.md             # 프로젝트 개요
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 연락처

프로젝트 링크: [https://github.com/yourusername/AnimeSorter](https://github.com/yourusername/AnimeSorter)

## 🙏 감사의 말

- [The Movie Database (TMDB)](https://www.themoviedb.org/) - 메타데이터 제공
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI 프레임워크
- [tmdbsimple](https://github.com/celiao/tmdbsimple) - TMDB API 클라이언트
