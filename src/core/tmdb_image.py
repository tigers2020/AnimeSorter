"""
TMDB 이미지 다운로드 모듈

TMDB 포스터, 배경 이미지 등의 다운로드를 관리합니다.
"""

import logging
import threading
from pathlib import Path
from typing import Optional

import aiohttp
import requests


class TMDBImageManager:
    """TMDB 이미지를 관리하는 클래스"""

    def __init__(self, poster_cache_dir: Path):
        """
        Args:
            poster_cache_dir: 포스터 이미지 캐시 디렉토리
        """
        self.poster_cache_dir = poster_cache_dir
        self.poster_cache_dir.mkdir(exist_ok=True)

        # 비동기 세션 관리
        self.async_session = None
        self.async_lock = threading.Lock()

        # 동기 세션 설정
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3,
            pool_block=False,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "User-Agent": "AnimeSorter/2.0.0",
                "Accept": "image/*",
                "Connection": "keep-alive",
            }
        )

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"TMDB 이미지 관리자 초기화 완료: {poster_cache_dir}")

    async def _get_async_session(self) -> aiohttp.ClientSession:
        """비동기 세션 가져오기 (싱글톤 패턴)"""
        if self.async_session is None or self.async_session.closed:
            async with self.async_lock:
                if self.async_session is None or self.async_session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=20,  # 동시 연결 제한
                        limit_per_host=10,  # 호스트당 연결 제한
                        ttl_dns_cache=300,  # DNS 캐시 TTL
                        use_dns_cache=True,
                    )
                    timeout = aiohttp.ClientTimeout(total=10, connect=5)
                    self.async_session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout,
                        headers={"User-Agent": "AnimeSorter/2.0.0", "Accept": "image/*"},
                    )
        return self.async_session

    async def close_async_session(self):
        """비동기 세션 종료"""
        if self.async_session and not self.async_session.closed:
            await self.async_session.close()

    async def download_poster_async(self, poster_path: str, size: str = "w185") -> Optional[str]:
        """TMDB 포스터 이미지 비동기 다운로드"""
        if not poster_path:
            return None

        try:
            # TMDB 이미지 URL 구성
            base_url = "https://image.tmdb.org/t/p"
            image_url = f"{base_url}/{size}{poster_path}"

            # 캐시 파일명 생성
            filename = poster_path.split("/")[-1]
            cache_filename = f"{size}_{filename}"
            cache_path = self.poster_cache_dir / cache_filename

            # 이미 캐시된 경우 반환
            if cache_path.exists():
                return str(cache_path)

            # 비동기 세션 가져오기
            session = await self._get_async_session()

            # 이미지 다운로드
            async with session.get(image_url) as response:
                response.raise_for_status()
                content = await response.read()

            # 캐시에 저장
            with cache_path.open("wb") as f:
                f.write(content)

            self.logger.info(f"포스터 다운로드 완료: {cache_filename}")
            return str(cache_path)

        except Exception as e:
            self.logger.error(f"포스터 다운로드 실패: {e}")
            return None

    def download_poster(self, poster_path: str, size: str = "w185") -> Optional[str]:
        """TMDB 포스터 이미지 다운로드 (동기 버전)"""
        if not poster_path:
            return None

        try:
            # TMDB 이미지 URL 구성
            base_url = "https://image.tmdb.org/t/p"
            image_url = f"{base_url}/{size}{poster_path}"

            # 캐시 파일명 생성
            filename = poster_path.split("/")[-1]
            cache_filename = f"{size}_{filename}"
            cache_path = self.poster_cache_dir / cache_filename

            # 이미 캐시된 경우 반환
            if cache_path.exists():
                return str(cache_path)

            # 이미지 다운로드
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()

            # 캐시에 저장
            with cache_path.open("wb") as f:
                f.write(response.content)

            self.logger.info(f"포스터 다운로드 완료: {cache_filename}")
            return str(cache_path)

        except Exception as e:
            self.logger.error(f"포스터 다운로드 실패: {e}")
            return None

    def download_backdrop(self, backdrop_path: str, size: str = "w1280") -> Optional[str]:
        """TMDB 배경 이미지 다운로드"""
        if not backdrop_path:
            return None

        try:
            # TMDB 이미지 URL 구성
            base_url = "https://image.tmdb.org/t/p"
            image_url = f"{base_url}/{size}{backdrop_path}"

            # 캐시 파일명 생성
            filename = backdrop_path.split("/")[-1]
            cache_filename = f"backdrop_{size}_{filename}"
            cache_path = self.poster_cache_dir / cache_filename

            # 이미 캐시된 경우 반환
            if cache_path.exists():
                return str(cache_path)

            # 이미지 다운로드
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()

            # 캐시에 저장
            with cache_path.open("wb") as f:
                f.write(response.content)

            self.logger.info(f"배경 이미지 다운로드 완료: {cache_filename}")
            return str(cache_path)

        except Exception as e:
            self.logger.error(f"배경 이미지 다운로드 실패: {e}")
            return None

    def download_profile(self, profile_path: str, size: str = "w185") -> Optional[str]:
        """TMDB 프로필 이미지 다운로드"""
        if not profile_path:
            return None

        try:
            # TMDB 이미지 URL 구성
            base_url = "https://image.tmdb.org/t/p"
            image_url = f"{base_url}/{size}{profile_path}"

            # 캐시 파일명 생성
            filename = profile_path.split("/")[-1]
            cache_filename = f"profile_{size}_{filename}"
            cache_path = self.poster_cache_dir / cache_filename

            # 이미 캐시된 경우 반환
            if cache_path.exists():
                return str(cache_path)

            # 이미지 다운로드
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()

            # 캐시에 저장
            with cache_path.open("wb") as f:
                f.write(response.content)

            self.logger.info(f"프로필 이미지 다운로드 완료: {cache_filename}")
            return str(cache_path)

        except Exception as e:
            self.logger.error(f"프로필 이미지 다운로드 실패: {e}")
            return None

    def get_poster_path(self, poster_path: str, size: str = "w185") -> Optional[str]:
        """포스터 이미지 경로 반환 (다운로드 포함)"""
        if not poster_path:
            return None

        # 이미지 다운로드 시도
        return self.download_poster(poster_path, size)

    def get_backdrop_path(self, backdrop_path: str, size: str = "w1280") -> Optional[str]:
        """배경 이미지 경로 반환 (다운로드 포함)"""
        if not backdrop_path:
            return None

        # 이미지 다운로드 시도
        return self.download_backdrop(backdrop_path, size)

    def get_profile_path(self, profile_path: str, size: str = "w185") -> Optional[str]:
        """프로필 이미지 경로 반환 (다운로드 포함)"""
        if not profile_path:
            return None

        # 이미지 다운로드 시도
        return self.download_profile(profile_path, size)

    def get_image_url(self, image_path: str, size: str = "w185") -> str:
        """TMDB 이미지 URL 생성"""
        if not image_path:
            return ""

        base_url = "https://image.tmdb.org/t/p"
        return f"{base_url}/{size}{image_path}"

    def clear_image_cache(self) -> int:
        """이미지 캐시 정리"""
        try:
            image_files = list(self.poster_cache_dir.glob("*"))
            cleaned_count = 0

            for image_file in image_files:
                if image_file.is_file():
                    image_file.unlink()
                    cleaned_count += 1

            self.logger.info(f"이미지 캐시 {cleaned_count}개 정리 완료")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"이미지 캐시 정리 오류: {e}")
            return 0

    def get_image_cache_info(self) -> dict:
        """이미지 캐시 정보 반환"""
        try:
            image_files = list(self.poster_cache_dir.glob("*"))
            total_size = sum(f.stat().st_size for f in image_files if f.is_file())

            # 이미지 타입별 분류
            image_types = {}
            for image_file in image_files:
                if image_file.is_file():
                    filename = image_file.name
                    if (
                        filename.startswith("w185_")
                        or filename.startswith("w342_")
                        or filename.startswith("w500_")
                    ):
                        image_types["poster"] = image_types.get("poster", 0) + 1
                    elif filename.startswith("backdrop_"):
                        image_types["backdrop"] = image_types.get("backdrop", 0) + 1
                    elif filename.startswith("profile_"):
                        image_types["profile"] = image_types.get("profile", 0) + 1
                    else:
                        image_types["other"] = image_types.get("other", 0) + 1

            return {
                "cache_dir": str(self.poster_cache_dir),
                "total_files": len(image_files),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "image_types": image_types,
            }

        except Exception as e:
            return {"error": str(e)}

    def set_poster_cache_dir(self, new_dir: Path) -> bool:
        """포스터 캐시 디렉토리 변경"""
        try:
            new_dir.mkdir(exist_ok=True)
            self.poster_cache_dir = new_dir
            self.logger.info(f"포스터 캐시 디렉토리 변경: {new_dir}")
            return True
        except Exception as e:
            self.logger.error(f"포스터 캐시 디렉토리 변경 실패: {e}")
            return False
