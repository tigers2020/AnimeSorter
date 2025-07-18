"""
테스트 파일 생성 스크립트
"""

import os
from pathlib import Path
import random
import string
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging

# 테스트 파일 생성할 디렉토리 (프로젝트 외부)
SOURCE_DIR = Path("./../test_files/source")

# 애니메이션 시리즈 목록
SERIES = [
    {
        "title": "미래소년 코난",
        "episodes": 26,
        "format": "미래소년 코난 (Ep 제{ep:02d}-{ep2:02d}화)Ac3 2Ch Kor Cd{disk:02d}.avi"
    },
    {
        "title": "Z Gundam",
        "episodes": 50,
        "format": "[슈메이커] Z Gundam TV EP{ep:02d}.{ext}"
    },
    {
        "title": "건담 더블오",
        "episodes": 25,
        "format": "[Ohys-Raws] 기동전사 건담 00 제{ep:02d}화 (BD 1920x1080 x264 AAC).{ext}"
    },
    {
        "title": "나루토",
        "episodes": 220,
        "formats": [
            "[ASW] Naruto - {ep:03d} [BD 720p AAC].{ext}",
            "Naruto {ep:03d} [1080p].{ext}",
            "[HorribleSubs] Naruto - {ep:03d} [720p].{ext}"
        ]
    },
    {
        "title": "원피스",
        "episodes": 200,
        "formats": [
            "[Ohys-Raws] One Piece - {ep:03d} [BD 1920x1080 x264 AAC].{ext}",
            "One.Piece.E{ep:03d}.1080p.BluRay.x264.{ext}",
            "[SubsPlease] One Piece - {ep:03d} (BD 1080p).{ext}"
        ]
    },
    {
        "title": "블리치",
        "episodes": 150,
        "formats": [
            "[SubsPlease] BLEACH - {ep:03d} (BD 1080p).{ext}",
            "Bleach.{ep:03d}.BluRay.1080p.{ext}",
            "[Coalgirls] BLEACH - {ep:03d} (BD 1920x1080).{ext}"
        ]
    },
    {
        "title": "진격의 거인",
        "episodes": 25,
        "formats": [
            "[Erai-raws] Shingeki no Kyojin - {ep:02d} [1080p].{ext}",
            "Attack.on.Titan.S01E{ep:02d}.1080p.BluRay.{ext}",
            "[SubsPlease] 진격의 거인 - {ep:02d} [BD 1080p].{ext}"
        ]
    },
    {
        "title": "귀멸의 칼날",
        "episodes": 26,
        "formats": [
            "[Ohys-Raws] Kimetsu no Yaiba - {ep:02d} (BD 1080p).{ext}",
            "Demon.Slayer.S01.EP{ep:02d}.1080p.{ext}",
            "[SubsPlease] 귀멸의 칼날 {ep:02d} [BD 1080p].{ext}"
        ]
    },
    {
        "title": "주술회전",
        "episodes": 24,
        "formats": [
            "[SubsPlease] Jujutsu Kaisen - {ep:02d} [1080p].{ext}",
            "주술회전.E{ep:02d}.1080p.BluRay.{ext}",
            "[Erai-raws] 주술회전 - {ep:02d} (BD 1080p).{ext}"
        ]
    }
]

# 파일 확장자
EXTENSIONS = ["mkv", "mp4", "avi"]
SUB_EXTENSIONS = ["srt", "ass", "smi", "vtt", "idx", "sub"]

# 비등록 파일 타입 (추가적인 확장자)
OTHER_EXTENSIONS = ["txt", "jpg", "png", "nfo", "zip", "rar", "iso", "torrent", "pdf"]

# 비등록 파일 접두사 예시
UNREGISTERED_PREFIXES = [
    "Sample_", "Screenshot_", "Thumbnail_", "Info_", "ReadMe_", 
    "ETC_", "Temp_", "Download_", "Movie_", "Series_"
]

def generate_random_filename(length=10):
    """랜덤 파일명 생성"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_unregistered_files(num_files=15):
    """비등록 파일 생성"""
    log.debug("Creating unregistered files")
    for _ in range(num_files):
        # 파일 유형 결정 (1: 랜덤 이름, 2: 애니메이션 스타일이지만 등록 안됨)
        file_type = random.randint(1, 2)
        
        if file_type == 1:
            # 완전 랜덤 파일
            prefix = random.choice(UNREGISTERED_PREFIXES)
            filename = f"{prefix}{generate_random_filename()}.{random.choice(OTHER_EXTENSIONS + EXTENSIONS)}"
        else:
            # 애니메이션 스타일이지만 등록되지 않은 시리즈
            fake_series = [
                "[HorribleSubs] 가상 애니메이션 - {0:02d}.{1}",
                "Fake.Anime.S01E{0:02d}.{1}",
                "애니_미등록_{0:02d}화.{1}",
                "[Sub-Group] Random Show - Episode {0:02d} [720p].{1}",
                "Unknown.Series.{0:03d}.1080p.{1}",
                "[Fake-Subs] Test Anime {0:03d} [HD].{1}"
            ]
            template = random.choice(fake_series)
            ep = random.randint(1, 50)
            ext = random.choice(EXTENSIONS + OTHER_EXTENSIONS)
            filename = template.format(ep, ext)
        
        filepath = SOURCE_DIR / filename
        filepath.touch()
        log.debug(f"Created unregistered file: {filename}")

def create_additional_subtitle_files():
    """추가 자막 파일 생성 (기존 비디오와 매치되지 않는)"""
    log.debug("Creating additional subtitle files")
    
    for _ in range(10):
        series = random.choice(SERIES)
        ep = random.randint(1, series["episodes"])
        sub_ext = random.choice(SUB_EXTENSIONS)
        
        # 자막 파일 이름을 약간 다르게 만듦 (구분을 위해)
        if random.random() < 0.5:
            # 정상적인 자막 파일 형식이지만 다른 언어 표시 추가
            langs = ["KOR", "ENG", "JPN", "CHN", "ESP"]
            lang = random.choice(langs)
            
            if series["title"] == "미래소년 코난":
                ep2 = min(ep + 1, series["episodes"])
                disk = random.randint(1, 10)
                base_format = series["format"].replace(".avi", f".{sub_ext}")
                filename = base_format.format(ep=ep, ep2=ep2, disk=disk)
                # 파일명 중간에 언어 추가
                parts = filename.split('.')
                parts[0] = f"{parts[0]}_{lang}"
                filename = '.'.join(parts)
            else:
                format_template = series["formats"][0] if "formats" in series else series["format"]
                base_format = format_template.format(ep=ep, ext=sub_ext)
                # 파일명 중간에 언어 추가
                parts = base_format.split('.')
                parts[0] = f"{parts[0]}_{lang}"
                filename = '.'.join(parts)
        else:
            # 완전히 다른 형식의 자막 파일
            if series["title"] == "미래소년 코난":
                filename = f"Conan.E{ep:02d}.{sub_ext}"
            else:
                series_name = series["title"].replace(" ", "_")
                filename = f"{series_name}_ep{ep:03d}.{sub_ext}"
        
        filepath = SOURCE_DIR / filename
        filepath.touch()
        log.debug(f"Created additional subtitle file: {filename}")

def create_test_files():
    """테스트 파일 생성"""
    # 소스 디렉토리 생성
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    log.debug("Starting to create test files")
    
    # 각 시리즈별로 파일 생성
    for series in SERIES:
        log.debug(f"Creating files for series: {series['title']}")
        # 랜덤하게 에피소드 수 선택 (전체 에피소드의 20~80%)
        total_episodes = series["episodes"]
        num_episodes = random.randint(int(total_episodes * 0.2), int(total_episodes * 0.8))
        
        # 랜덤하게 에피소드 선택
        episodes = random.sample(range(1, total_episodes + 1), num_episodes)
        episodes.sort()
        
        # 확장자 선택
        main_ext = random.choice(EXTENSIONS)
        sub_ext = random.choice(SUB_EXTENSIONS)
        
        # 코난 시리즈는 특별 처리 (2화씩 묶음)
        if series["title"] == "미래소년 코난":
            for i in range(0, len(episodes), 2):
                if i + 1 < len(episodes):
                    ep1, ep2 = episodes[i], episodes[i + 1]
                    disk = (i // 2) + 1
                    filename = series["format"].format(ep=ep1, ep2=ep2, disk=disk)
                    filepath = SOURCE_DIR / filename
                    filepath.touch()
                    log.debug(f"Created file: {filename}")
        else:
            # 일반 시리즈
            for ep in episodes:
                # 여러 형식 중 하나 선택
                if "formats" in series:
                    format_template = random.choice(series["formats"])
                else:
                    format_template = series["format"]
                
                # 비디오 파일
                video_filename = format_template.format(ep=ep, ext=main_ext)
                video_filepath = SOURCE_DIR / video_filename
                video_filepath.touch()
                log.debug(f"Created video file: {video_filename}")
                
                # 자막 파일 (70% 확률로 생성)
                if random.random() < 0.7:
                    # 자막 파일은 비디오 파일과 동일한 이름으로 생성
                    sub_filename = video_filename.rsplit('.', 1)[0] + f".{sub_ext}"
                    sub_filepath = SOURCE_DIR / sub_filename
                    sub_filepath.touch()
                    log.debug(f"Created subtitle file: {sub_filename}")
    
    # 비등록 파일 생성
    create_unregistered_files(num_files=random.randint(15, 30))
    
    # 추가 자막 파일 생성
    create_additional_subtitle_files()
    
    log.debug("Test file creation completed")

if __name__ == "__main__":
    create_test_files() 