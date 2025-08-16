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

## 📁 프로젝트 구조

```
AnimeSorter/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 기능
│   ├── plugin/            # 플러그인 시스템
│   ├── ui/                # 사용자 인터페이스
│   ├── utils/             # 유틸리티 함수
│   ├── config/            # 설정 관리
│   └── exceptions/        # 예외 처리
├── tests/                 # 테스트 코드
├── docs/                  # 문서
├── config/                # 설정 파일
└── scripts/               # 유틸리티 스크립트
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