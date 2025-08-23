"""
TMDB API 요청 속도 제한 관리 모듈

TMDB API 요청의 속도 제한을 관리하고 요청 간격을 조절합니다.
"""

import logging
import time
from collections import deque
from datetime import datetime
from typing import Any


class TMDBRateLimiter:
    """TMDB API 요청 속도 제한을 관리하는 클래스"""

    def __init__(self, requests_per_second: int = 10, burst_limit: int = 20):
        """
        Args:
            requests_per_second: 초당 최대 요청 수
            burst_limit: 버스트 허용 최대 요청 수
        """
        self.requests_per_second = requests_per_second
        self.burst_limit = burst_limit

        # 요청 기록 관리
        self.request_times: deque[float] = deque()
        self.last_request_time: float | None = None

        # 에러 및 재시도 관리
        self.error_count = 0
        self.last_error_time: float | None = None
        self.backoff_multiplier = 1.0

        # 통계 정보
        self.total_requests = 0
        self.total_delays = 0
        self.total_delay_time = 0.0

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(
            f"TMDB 속도 제한 관리자 초기화: {requests_per_second} req/s, 버스트: {burst_limit}"
        )

    def can_make_request(self) -> bool:
        """요청 가능 여부 확인"""
        current_time = time.time()

        # 버스트 제한 확인
        if len(self.request_times) >= self.burst_limit:
            return False

        # 시간 기반 제한 확인
        if self.request_times:
            # 1초 이내 요청 수 확인
            cutoff_time = current_time - 1.0
            while self.request_times and self.request_times[0] < cutoff_time:
                self.request_times.popleft()

            if len(self.request_times) >= self.requests_per_second:
                return False

        return True

    def wait_if_needed(self) -> float:
        """필요한 경우 대기하고 대기 시간 반환"""
        current_time = time.time()
        delay_time = 0.0

        if not self.can_make_request():
            # 다음 요청 가능 시간 계산
            if self.request_times:
                oldest_request = self.request_times[0]
                time_since_oldest = current_time - oldest_request

                if time_since_oldest < 1.0:
                    # 1초 이내에 요청이 있었으면 대기
                    wait_time = 1.0 - time_since_oldest
                    delay_time = wait_time

                    # 백오프 적용
                    if self.error_count > 0:
                        wait_time *= self.backoff_multiplier
                        delay_time = wait_time

                    time.sleep(wait_time)
                    current_time = time.time()

            # 버스트 제한으로 인한 대기
            elif len(self.request_times) >= self.burst_limit:
                # 가장 오래된 요청이 1초 지날 때까지 대기
                if self.request_times:
                    oldest_request = self.request_times[0]
                    wait_time = 1.0 - (current_time - oldest_request)
                    if wait_time > 0:
                        delay_time = wait_time
                        time.sleep(wait_time)
                        current_time = time.time()

        return delay_time

    def record_request(self, success: bool = True, response_time: float | None = None) -> None:
        """요청 기록"""
        current_time = time.time()

        # 요청 시간 기록
        self.request_times.append(current_time)
        self.total_requests += 1

        # 응답 시간 기록
        if response_time is not None:
            self.total_delay_time += response_time
            self.total_delays += 1

        # 성공/실패 처리
        if success:
            # 성공 시 백오프 리셋
            if self.error_count > 0:
                self.error_count = 0
                self.backoff_multiplier = 1.0
                self.logger.info("API 요청 성공으로 백오프 리셋")
        else:
            # 실패 시 백오프 증가
            self.error_count += 1
            self.last_error_time = current_time

            # 지수 백오프 (최대 8배)
            if self.backoff_multiplier < 8.0:
                self.backoff_multiplier = min(8.0, self.backoff_multiplier * 2)

            self.logger.warning(
                f"API 요청 실패: 백오프 {self.backoff_multiplier:.1f}x, 총 실패: {self.error_count}"
            )

    def get_wait_time(self) -> float:
        """다음 요청까지 대기해야 할 시간 반환"""
        current_time = time.time()

        if not self.request_times:
            return 0.0

        # 1초 이내 요청 수 확인
        cutoff_time = current_time - 1.0
        recent_requests = [t for t in self.request_times if t >= cutoff_time]

        if len(recent_requests) < self.requests_per_second:
            return 0.0

        # 가장 오래된 요청이 1초 지날 때까지 대기
        oldest_request = min(recent_requests)
        wait_time = 1.0 - (current_time - oldest_request)

        # 백오프 적용
        if self.error_count > 0:
            wait_time *= self.backoff_multiplier

        return max(0.0, wait_time)

    def get_status(self) -> dict[str, Any]:
        """현재 상태 정보 반환"""
        current_time = time.time()

        # 최근 요청 통계
        recent_requests = [t for t in self.request_times if current_time - t <= 60.0]  # 1분 이내

        # 에러 통계
        error_stats = {}
        if self.last_error_time:
            time_since_error = current_time - self.last_error_time
            error_stats = {
                "last_error_time": datetime.fromtimestamp(self.last_error_time).isoformat(),
                "time_since_error_seconds": time_since_error,
                "error_count": self.error_count,
                "backoff_multiplier": self.backoff_multiplier,
            }

        return {
            "requests_per_second": self.requests_per_second,
            "burst_limit": self.burst_limit,
            "current_queue_size": len(self.request_times),
            "recent_requests_1min": len(recent_requests),
            "total_requests": self.total_requests,
            "average_response_time": (
                self.total_delay_time / self.total_delays if self.total_delays > 0 else 0.0
            ),
            "can_make_request": self.can_make_request(),
            "wait_time_seconds": self.get_wait_time(),
            "error_stats": error_stats,
        }

    def reset(self) -> None:
        """속도 제한 관리자 초기화"""
        self.request_times.clear()
        self.last_request_time = None
        self.error_count = 0
        self.last_error_time = None
        self.backoff_multiplier = 1.0
        self.total_requests = 0
        self.total_delays = 0
        self.total_delay_time = 0.0

        self.logger.info("TMDB 속도 제한 관리자 초기화 완료")

    def set_rate_limit(self, requests_per_second: int, burst_limit: int | None = None) -> None:
        """속도 제한 설정 변경"""
        old_rate = self.requests_per_second
        self.requests_per_second = max(1, requests_per_second)

        if burst_limit is not None:
            self.burst_limit = max(self.requests_per_second, burst_limit)
        else:
            self.burst_limit = max(self.requests_per_second * 2, self.burst_limit)

        self.logger.info(
            f"속도 제한 변경: {old_rate} → {self.requests_per_second} req/s, 버스트: {self.burst_limit}"
        )

    def cleanup_old_requests(self, max_age_seconds: int = 300) -> None:
        """오래된 요청 기록 정리"""
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        initial_count = len(self.request_times)
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()

        cleaned_count = initial_count - len(self.request_times)
        if cleaned_count > 0:
            self.logger.debug(f"오래된 요청 기록 {cleaned_count}개 정리 완료")

    def get_recommended_delay(self) -> float:
        """권장 대기 시간 반환 (에러 상황 고려)"""
        base_delay = self.get_wait_time()

        # 에러 상황에 따른 추가 대기
        if self.error_count > 0:
            # 에러 수에 따른 추가 대기 (0.1초 ~ 1초)
            additional_delay = min(1.0, self.error_count * 0.1)
            base_delay += additional_delay

        return base_delay

    def is_healthy(self) -> bool:
        """API 상태가 정상인지 확인"""
        # 너무 많은 에러가 발생한 경우
        if self.error_count > 10:
            return False

        # 최근 에러가 너무 자주 발생한 경우
        if self.last_error_time:
            time_since_error = time.time() - self.last_error_time
            if time_since_error < 60.0 and self.error_count > 5:  # 1분 이내 5회 이상 에러
                return False

        return True

    def get_health_status(self) -> dict[str, Any]:
        """상태 정보 반환"""
        return {
            "healthy": self.is_healthy(),
            "status": self.get_status(),
            "recommended_delay": self.get_recommended_delay(),
            "queue_health": {
                "current_size": len(self.request_times),
                "max_size": self.burst_limit,
                "utilization_percent": (len(self.request_times) / self.burst_limit) * 100,
            },
        }
