"""
TMDB 캐시 관리 모듈

TMDB API 응답을 위한 캐시 시스템을 관리합니다.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any


class TMDBCacheManager:
    """TMDB 캐시를 관리하는 클래스"""

    def __init__(self, cache_dir: Path, cache_expiry: int = 3600, memory_cache_size: int = 1000):
        """
        Args:
            cache_dir: 캐시 디렉토리 경로
            cache_expiry: 캐시 만료 시간 (초)
            memory_cache_size: 메모리 캐시 최대 크기
        """
        self.cache_dir = cache_dir
        self.cache_expiry = cache_expiry
        self.memory_cache_size = memory_cache_size

        # 캐시 설정
        self.cache_enabled = True
        self.memory_cache = {}  # 메모리 캐시 (빠른 접근용)
        self.cache_lock = threading.Lock()

        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"TMDB 캐시 관리자 초기화 완료: {cache_dir}")

    def get_cache(self, key: str) -> Any | None:
        """캐시에서 데이터 가져오기"""
        if not self.cache_enabled:
            return None

        # 메모리 캐시 확인 (빠른 접근)
        with self.cache_lock:
            if key in self.memory_cache:
                return self.memory_cache[key]

        # 디스크 캐시 확인
        try:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                # 캐시 만료 확인
                if time.time() - cache_file.stat().st_mtime < self.cache_expiry:
                    with cache_file.open(encoding="utf-8") as f:
                        data = json.load(f)

                        # 메모리 캐시에 추가
                        with self.cache_lock:
                            if len(self.memory_cache) >= self.memory_cache_size:
                                # LRU 방식으로 가장 오래된 항목 제거
                                oldest_key = next(iter(self.memory_cache))
                                del self.memory_cache[oldest_key]
                            self.memory_cache[key] = data

                        return data
                else:
                    # 만료된 캐시 삭제
                    cache_file.unlink()
        except Exception as e:
            self.logger.warning(f"캐시 읽기 오류: {e}")

        return None

    def set_cache(self, key: str, data: Any) -> None:
        """데이터를 캐시에 저장"""
        if not self.cache_enabled:
            return

        try:
            # 메모리 캐시에 저장
            with self.cache_lock:
                if len(self.memory_cache) >= self.memory_cache_size:
                    # LRU 방식으로 가장 오래된 항목 제거
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]
                self.memory_cache[key] = data

            # 디스크 캐시에 저장
            cache_file = self.cache_dir / f"{key}.json"
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.warning(f"캐시 저장 오류: {e}")

    def clear_cache(self) -> None:
        """캐시 초기화"""
        try:
            # 메모리 캐시 초기화
            with self.cache_lock:
                self.memory_cache.clear()

            # 디스크 캐시 초기화
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()

            self.logger.info("TMDB 캐시가 초기화되었습니다.")
        except Exception as e:
            self.logger.error(f"캐시 초기화 오류: {e}")

    def clear_expired_cache(self) -> int:
        """만료된 캐시 정리"""
        try:
            cleaned_count = 0
            current_time = time.time()

            for cache_file in self.cache_dir.glob("*.json"):
                if current_time - cache_file.stat().st_mtime > self.cache_expiry:
                    cache_file.unlink()
                    cleaned_count += 1

            if cleaned_count > 0:
                self.logger.info(f"만료된 캐시 {cleaned_count}개 정리 완료")

            return cleaned_count
        except Exception as e:
            self.logger.error(f"만료된 캐시 정리 오류: {e}")
            return 0

    def get_cache_info(self) -> dict[str, Any]:
        """캐시 정보 반환"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)

            with self.cache_lock:
                memory_cache_size = len(self.memory_cache)

            return {
                "cache_enabled": self.cache_enabled,
                "cache_dir": str(self.cache_dir),
                "file_count": len(cache_files),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "expiry_seconds": self.cache_expiry,
                "memory_cache_size": memory_cache_size,
                "memory_cache_max_size": self.memory_cache_size,
            }
        except Exception as e:
            return {"error": str(e)}

    def set_cache_enabled(self, enabled: bool) -> None:
        """캐시 활성화/비활성화"""
        self.cache_enabled = enabled
        self.logger.info(f"TMDB 캐시: {'활성화' if enabled else '비활성화'}")

    def set_cache_expiry(self, expiry_seconds: int) -> None:
        """캐시 만료 시간 설정"""
        self.cache_expiry = expiry_seconds
        self.logger.info(f"TMDB 캐시 만료 시간: {expiry_seconds}초")

    def set_memory_cache_size(self, size: int) -> None:
        """메모리 캐시 크기 설정"""
        with self.cache_lock:
            if size < len(self.memory_cache):
                # 크기를 줄이는 경우, 가장 오래된 항목들 제거
                while len(self.memory_cache) > size:
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]
            self.memory_cache_size = size

        self.logger.info(f"TMDB 메모리 캐시 크기: {size}")

    def get_cache_keys(self) -> list[str]:
        """캐시된 키 목록 반환"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            return [f.stem for f in cache_files]
        except Exception as e:
            self.logger.error(f"캐시 키 목록 조회 오류: {e}")
            return []

    def remove_cache(self, key: str) -> bool:
        """특정 키의 캐시 제거"""
        try:
            # 메모리 캐시에서 제거
            with self.cache_lock:
                self.memory_cache.pop(key, None)

            # 디스크 캐시에서 제거
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_file.unlink()
                self.logger.debug(f"캐시 제거 완료: {key}")
                return True

            return False
        except Exception as e:
            self.logger.error(f"캐시 제거 오류: {e}")
            return False

    def get_cache_stats(self) -> dict[str, Any]:
        """캐시 통계 정보 반환"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            current_time = time.time()

            # 만료된 캐시 개수 계산
            expired_count = sum(
                1 for f in cache_files if current_time - f.stat().st_mtime > self.cache_expiry
            )

            # 캐시 파일 크기별 분포
            size_distribution = {}
            for f in cache_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                if size_mb < 1:
                    size_distribution["<1MB"] = size_distribution.get("<1MB", 0) + 1
                elif size_mb < 5:
                    size_distribution["1-5MB"] = size_distribution.get("1-5MB", 0) + 1
                elif size_mb < 10:
                    size_distribution["5-10MB"] = size_distribution.get("5-10MB", 0) + 1
                else:
                    size_distribution[">10MB"] = size_distribution.get(">10MB", 0) + 1

            return {
                "total_files": len(cache_files),
                "expired_files": expired_count,
                "valid_files": len(cache_files) - expired_count,
                "size_distribution": size_distribution,
                "memory_cache_usage": len(self.memory_cache) / self.memory_cache_size,
            }
        except Exception as e:
            return {"error": str(e)}
