"""
해상도 정규화 유틸리티

애니메이션 파일의 해상도 정보를 표준 형식으로 정규화하는 기능을 제공합니다.
"""

import re


class ResolutionNormalizer:
    """해상도 정규화 클래스"""

    # 표준 해상도 매핑
    RESOLUTION_MAPPING = {
        # 4K 해상도
        "4k": "4K",
        "2160p": "4K",
        "2160": "4K",
        "3840x2160": "4K",
        "2160x3840": "4K",
        "uhd": "4K",
        "ultra hd": "4K",
        # 2K 해상도
        "2k": "2K",
        "1440p": "2K",
        "1440": "2K",
        "2560x1440": "2K",
        "1440x2560": "2K",
        "qhd": "2K",
        "quad hd": "2K",
        # 1080p 해상도
        "1080p": "1080p",
        "1080": "1080p",
        "1920x1080": "1080p",
        "1080x1920": "1080p",
        "fhd": "1080p",
        "full hd": "1080p",
        "080p": "1080p",  # 잘못된 형식 보정
        # 720p 해상도
        "720p": "720p",
        "720": "720p",
        "1280x720": "720p",
        "720x1280": "720p",
        "hd": "720p",
        "20p": "720p",  # 잘못된 형식 보정
        # 480p 해상도
        "480p": "480p",
        "480": "480p",
        "854x480": "480p",
        "480x854": "480p",
        "640x480": "480p",
        "sd": "480p",
        "80p": "480p",  # 잘못된 형식 보정 (720p와 구분 필요)
    }

    # 해상도 우선순위 (높을수록 우선)
    RESOLUTION_PRIORITY = {"4K": 5, "2K": 4, "1080p": 3, "720p": 2, "480p": 1, "Unknown": 0}

    @classmethod
    def normalize(cls, resolution: str) -> str:
        """
        해상도를 표준 형식으로 정규화

        Args:
            resolution: 원본 해상도 문자열

        Returns:
            정규화된 해상도 문자열 (4K, 2K, 1080p, 720p, 480p, Unknown)
        """
        if not resolution:
            return "Unknown"

        # 문자열 정리
        normalized = str(resolution).strip().lower()

        # 특수문자 제거 (공백, 대시, 언더스코어 등)
        normalized = re.sub(r"[^\w]", "", normalized)

        # 매핑에서 찾기
        for key, value in cls.RESOLUTION_MAPPING.items():
            if key in normalized:
                return value

        # 숫자 패턴으로 직접 매칭
        if re.search(r"3840.*2160|2160.*3840", normalized):
            return "4K"
        if re.search(r"2560.*1440|1440.*2560", normalized):
            return "2K"
        if re.search(r"1920.*1080|1080.*1920", normalized):
            return "1080p"
        if re.search(r"1280.*720|720.*1280", normalized):
            return "720p"
        if re.search(r"854.*480|480.*854|640.*480", normalized):
            return "480p"

        # p로 끝나는 패턴
        if re.search(r"\d{3,4}p$", normalized):
            height = re.search(r"(\d{3,4})p$", normalized)
            if height:
                h = int(height.group(1))
                if h >= 2160:
                    return "4K"
                if h >= 1440:
                    return "2K"
                if h >= 1080:
                    return "1080p"
                if h >= 720:
                    return "720p"
                if h >= 480:
                    return "480p"

        return "Unknown"

    @classmethod
    def get_priority(cls, resolution: str) -> int:
        """
        해상도의 우선순위 반환

        Args:
            resolution: 해상도 문자열

        Returns:
            우선순위 값 (높을수록 우선)
        """
        normalized = cls.normalize(resolution)
        return cls.RESOLUTION_PRIORITY.get(normalized, 0)

    @classmethod
    def get_best_resolution(cls, resolutions: list[str]) -> str:
        """
        여러 해상도 중 가장 좋은 해상도 선택

        Args:
            resolutions: 해상도 문자열 리스트

        Returns:
            가장 좋은 해상도 문자열
        """
        if not resolutions:
            return "Unknown"

        # 정규화하고 우선순위로 정렬
        normalized_resolutions = [(cls.normalize(r), r) for r in resolutions]
        normalized_resolutions.sort(key=lambda x: cls.get_priority(x[0]), reverse=True)

        return normalized_resolutions[0][0]

    @classmethod
    def is_valid_resolution(cls, resolution: str) -> bool:
        """
        해상도가 유효한지 확인

        Args:
            resolution: 해상도 문자열

        Returns:
            유효한 해상도인지 여부
        """
        normalized = cls.normalize(resolution)
        return normalized != "Unknown"


# 편의 함수들
def normalize_resolution(resolution: str) -> str:
    """해상도를 정규화하는 편의 함수"""
    return ResolutionNormalizer.normalize(resolution)


def get_resolution_priority(resolution: str) -> int:
    """해상도 우선순위를 반환하는 편의 함수"""
    return ResolutionNormalizer.get_priority(resolution)


def get_best_resolution(resolutions: list[str]) -> str:
    """가장 좋은 해상도를 선택하는 편의 함수"""
    return ResolutionNormalizer.get_best_resolution(resolutions)
