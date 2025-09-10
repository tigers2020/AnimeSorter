"""
AnimeSorter 상수 정의

애플리케이션 전반에서 사용되는 상수들을 중앙 집중식으로 관리합니다.
"""

# 비디오 파일 확장자
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".3gp",
    ".ogv",
    ".ts",
    ".m2ts",
}

# 자막 파일 확장자
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".sub", ".vtt", ".idx", ".smi", ".sami", ".txt"}

# 기본 비디오 파일 확장자 (주로 사용되는 것들)
DEFAULT_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}

# 파일 크기 제한 (바이트)
DEFAULT_MIN_FILE_SIZE = 0
DEFAULT_MAX_FILE_SIZE = 0  # 0은 제한 없음

# 경로 길이 제한
DEFAULT_MAX_PATH_LENGTH = 260  # Windows 기본 경로 길이 제한

# 로그 레벨
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


# 이벤트 우선순위
class EventPriority:
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# 이벤트 카테고리
class EventCategory:
    APPLICATION = "application"
    USER = "user"
    SYSTEM = "system"
    TMDB = "tmdb"
    BACKGROUND = "background"
