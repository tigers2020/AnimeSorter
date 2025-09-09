"""
성능 모니터

이 모듈은 테마 엔진의 성능을 측정하고 모니터링하는
PerformanceMonitor 클래스를 제공합니다.
"""

import json
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import psutil

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """메트릭 타입"""

    TIMING = "timing"
    MEMORY = "memory"
    CPU = "cpu"
    CACHE = "cache"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"


class PerformanceLevel(Enum):
    """성능 레벨"""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """성능 메트릭"""

    name: str
    value: float
    unit: str
    timestamp: float
    metric_type: MetricType
    tags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "metric_type": self.metric_type.value,
            "tags": self.tags,
        }


@dataclass
class PerformanceSnapshot:
    """성능 스냅샷"""

    timestamp: float
    metrics: list[PerformanceMetric]
    system_info: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "system_info": self.system_info,
        }


@dataclass
class PerformanceThreshold:
    """성능 임계값"""

    metric_name: str
    warning_threshold: float
    critical_threshold: float
    operator: str = ">"  # >, <, >=, <=, ==, !=

    def check_threshold(self, value: float) -> PerformanceLevel:
        """임계값을 확인합니다"""
        try:
            if self.operator == ">":
                if value > self.critical_threshold:
                    return PerformanceLevel.CRITICAL
                elif value > self.warning_threshold:
                    return PerformanceLevel.POOR
            elif self.operator == "<":
                if value < self.critical_threshold:
                    return PerformanceLevel.CRITICAL
                elif value < self.warning_threshold:
                    return PerformanceLevel.POOR
            elif self.operator == ">=":
                if value >= self.critical_threshold:
                    return PerformanceLevel.CRITICAL
                elif value >= self.warning_threshold:
                    return PerformanceLevel.POOR
            elif self.operator == "<=":
                if value <= self.critical_threshold:
                    return PerformanceLevel.CRITICAL
                elif value <= self.warning_threshold:
                    return PerformanceLevel.POOR
            elif self.operator == "==":
                if value == self.critical_threshold:
                    return PerformanceLevel.CRITICAL
                elif value == self.warning_threshold:
                    return PerformanceLevel.POOR
            elif self.operator == "!=":
                if value != self.critical_threshold:
                    return PerformanceLevel.CRITICAL
                elif value != self.warning_threshold:
                    return PerformanceLevel.POOR

            if value > self.warning_threshold * 0.8:
                return PerformanceLevel.ACCEPTABLE
            elif value > self.warning_threshold * 0.6:
                return PerformanceLevel.GOOD
            else:
                return PerformanceLevel.EXCELLENT

        except Exception as e:
            logger.error(f"임계값 확인 실패: {str(e)}")
            return PerformanceLevel.ACCEPTABLE


class PerformanceMonitor:
    """테마 엔진의 성능을 모니터링하는 클래스"""

    def __init__(self, theme_manager=None):
        """
        PerformanceMonitor 초기화

        Args:
            theme_manager: ThemeManager 인스턴스 (선택사항)
        """
        self.theme_manager = theme_manager

        # 성능 메트릭 저장소
        self.metrics: list[PerformanceMetric] = []
        self.snapshots: list[PerformanceSnapshot] = []

        # 임계값 설정
        self.thresholds: dict[str, PerformanceThreshold] = {}
        self._setup_default_thresholds()

        # 모니터링 설정
        self.settings = {
            "enabled": True,
            "auto_monitoring": True,
            "monitoring_interval": 5.0,  # 5초
            "max_metrics_history": 10000,
            "max_snapshots_history": 1000,
            "enable_system_monitoring": True,
            "enable_performance_alerts": True,
            "performance_alert_callbacks": [],
        }

        # 모니터링 상태
        self.is_monitoring = False
        self.monitoring_thread = None
        self.stop_monitoring_event = threading.Event()

        # 성능 통계
        self.performance_stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "average_response_time": 0.0,
            "peak_memory_usage": 0,
            "peak_cpu_usage": 0.0,
        }

        # 시작 시간
        self.start_time = time.time()

    def _setup_default_thresholds(self) -> None:
        """기본 임계값을 설정합니다"""
        try:
            # 응답 시간 임계값 (밀리초)
            self.thresholds["response_time"] = PerformanceThreshold(
                metric_name="response_time",
                warning_threshold=100.0,  # 100ms
                critical_threshold=500.0,  # 500ms
                operator=">",
            )

            # 메모리 사용량 임계값 (MB)
            self.thresholds["memory_usage"] = PerformanceThreshold(
                metric_name="memory_usage",
                warning_threshold=100.0,  # 100MB
                critical_threshold=500.0,  # 500MB
                operator=">",
            )

            # CPU 사용률 임계값 (%)
            self.thresholds["cpu_usage"] = PerformanceThreshold(
                metric_name="cpu_usage",
                warning_threshold=70.0,  # 70%
                critical_threshold=90.0,  # 90%
                operator=">",
            )

            # 캐시 히트율 임계값 (%)
            self.thresholds["cache_hit_rate"] = PerformanceThreshold(
                metric_name="cache_hit_rate",
                warning_threshold=80.0,  # 80%
                critical_threshold=60.0,  # 60%
                operator="<",
            )

            # 처리량 임계값 (ops/sec)
            self.thresholds["throughput"] = PerformanceThreshold(
                metric_name="throughput",
                warning_threshold=100.0,  # 100 ops/sec
                critical_threshold=50.0,  # 50 ops/sec
                operator="<",
            )

            logger.info("기본 성능 임계값 설정 완료")

        except Exception as e:
            logger.error(f"기본 임계값 설정 실패: {str(e)}")

    def start_monitoring(self) -> bool:
        """성능 모니터링을 시작합니다"""
        try:
            if self.is_monitoring:
                logger.warning("이미 모니터링이 실행 중입니다")
                return False

            if not self.settings["enabled"]:
                logger.warning("성능 모니터링이 비활성화되어 있습니다")
                return False

            self.is_monitoring = True
            self.stop_monitoring_event.clear()

            # 모니터링 스레드 시작
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()

            logger.info("성능 모니터링이 시작되었습니다")
            return True

        except Exception as e:
            logger.error(f"성능 모니터링 시작 실패: {str(e)}")
            return False

    def stop_monitoring(self) -> bool:
        """성능 모니터링을 중지합니다"""
        try:
            if not self.is_monitoring:
                logger.warning("모니터링이 실행 중이 아닙니다")
                return False

            self.is_monitoring = False
            self.stop_monitoring_event.set()

            # 모니터링 스레드 종료 대기
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)

            logger.info("성능 모니터링이 중지되었습니다")
            return True

        except Exception as e:
            logger.error(f"성능 모니터링 중지 실패: {str(e)}")
            return False

    def _monitoring_loop(self) -> None:
        """모니터링 루프"""
        try:
            while self.is_monitoring and not self.stop_monitoring_event.is_set():
                # 성능 스냅샷 생성
                self._create_performance_snapshot()

                # 임계값 확인 및 알림
                self._check_thresholds_and_alert()

                # 대기
                self.stop_monitoring_event.wait(self.settings["monitoring_interval"])

        except Exception as e:
            logger.error(f"모니터링 루프 실행 실패: {str(e)}")
            self.is_monitoring = False

    def _create_performance_snapshot(self) -> None:
        """성능 스냅샷을 생성합니다"""
        try:
            timestamp = time.time()
            metrics = []

            # 시스템 정보 수집
            system_info = self._collect_system_info()

            # 기본 성능 메트릭 수집
            if self.theme_manager:
                # ThemeManager 성능 메트릭
                compiler_metrics = self.theme_manager.get_compiler_performance_metrics()
                for component, component_metrics in compiler_metrics.items():
                    for metric_name, metric_value in component_metrics.items():
                        if isinstance(metric_value, (int, float)):
                            metric = PerformanceMetric(
                                name=f"{component}_{metric_name}",
                                value=float(metric_value),
                                unit=self._get_metric_unit(metric_name),
                                timestamp=timestamp,
                                metric_type=self._get_metric_type(metric_name),
                                tags={"component": component},
                            )
                            metrics.append(metric)

            # 시스템 성능 메트릭
            if self.settings["enable_system_monitoring"]:
                system_metrics = self._collect_system_metrics()
                metrics.extend(system_metrics)

            # 스냅샷 생성
            snapshot = PerformanceSnapshot(
                timestamp=timestamp, metrics=metrics, system_info=system_info
            )

            # 스냅샷 저장
            self.snapshots.append(snapshot)

            # 히스토리 크기 제한
            if len(self.snapshots) > self.settings["max_snapshots_history"]:
                self.snapshots.pop(0)

            # 메트릭 저장
            self.metrics.extend(metrics)

            # 히스토리 크기 제한
            if len(self.metrics) > self.settings["max_metrics_history"]:
                self.metrics = self.metrics[-self.settings["max_metrics_history"] :]

            logger.debug(f"성능 스냅샷 생성 완료: {len(metrics)}개 메트릭")

        except Exception as e:
            logger.error(f"성능 스냅샷 생성 실패: {str(e)}")

    def _collect_system_info(self) -> dict[str, Any]:
        """시스템 정보를 수집합니다"""
        try:
            info = {
                "platform": psutil.sys.platform,
                "python_version": psutil.sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": (
                    psutil.disk_usage("/").percent if hasattr(psutil, "disk_usage") else 0
                ),
            }

            return info

        except Exception as e:
            logger.error(f"시스템 정보 수집 실패: {str(e)}")
            return {}

    def _collect_system_metrics(self) -> list[PerformanceMetric]:
        """시스템 성능 메트릭을 수집합니다"""
        try:
            metrics = []
            timestamp = time.time()

            # CPU 사용률
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                metrics.append(
                    PerformanceMetric(
                        name="cpu_usage",
                        value=cpu_percent,
                        unit="%",
                        timestamp=timestamp,
                        metric_type=MetricType.CPU,
                    )
                )
            except Exception:
                pass

            # 메모리 사용량
            try:
                memory = psutil.virtual_memory()
                memory_mb = memory.used / (1024 * 1024)
                metrics.append(
                    PerformanceMetric(
                        name="memory_usage",
                        value=memory_mb,
                        unit="MB",
                        timestamp=timestamp,
                        metric_type=MetricType.MEMORY,
                    )
                )
            except Exception:
                pass

            # 디스크 I/O
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    read_mb = disk_io.read_bytes / (1024 * 1024)
                    write_mb = disk_io.write_bytes / (1024 * 1024)

                    metrics.append(
                        PerformanceMetric(
                            name="disk_read",
                            value=read_mb,
                            unit="MB",
                            timestamp=timestamp,
                            metric_type=MetricType.THROUGHPUT,
                        )
                    )

                    metrics.append(
                        PerformanceMetric(
                            name="disk_write",
                            value=write_mb,
                            unit="MB",
                            timestamp=timestamp,
                            metric_type=MetricType.THROUGHPUT,
                        )
                    )
            except Exception:
                pass

            return metrics

        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {str(e)}")
            return []

    def _get_metric_unit(self, metric_name: str) -> str:
        """메트릭의 단위를 반환합니다"""
        try:
            unit_mapping = {
                "time": "ms",
                "parse_time": "ms",
                "compile_time": "ms",
                "optimize_time": "ms",
                "generation_time": "ms",
                "total_time": "ms",
                "memory": "bytes",
                "memory_saved": "bytes",
                "cache_hits": "count",
                "cache_misses": "count",
                "nodes_processed": "count",
                "rules_executed": "count",
                "styles_generated": "count",
                "conditions_evaluated": "count",
            }

            for key, unit in unit_mapping.items():
                if key in metric_name.lower():
                    return unit

            return "count"

        except Exception:
            return "count"

    def _get_metric_type(self, metric_name: str) -> MetricType:
        """메트릭의 타입을 반환합니다"""
        try:
            if any(keyword in metric_name.lower() for keyword in ["time", "duration"]):
                return MetricType.TIMING
            elif any(keyword in metric_name.lower() for keyword in ["memory", "bytes"]):
                return MetricType.MEMORY
            elif any(keyword in metric_name.lower() for keyword in ["cpu", "usage"]):
                return MetricType.CPU
            elif any(keyword in metric_name.lower() for keyword in ["cache", "hit", "miss"]):
                return MetricType.CACHE
            elif any(keyword in metric_name.lower() for keyword in ["throughput", "ops", "count"]):
                return MetricType.THROUGHPUT
            else:
                return MetricType.THROUGHPUT

        except Exception:
            return MetricType.THROUGHPUT

    def _check_thresholds_and_alert(self) -> None:
        """임계값을 확인하고 알림을 발생시킵니다"""
        try:
            if not self.settings["enable_performance_alerts"]:
                return

            # 최신 스냅샷의 메트릭들 확인
            if not self.snapshots:
                return

            latest_snapshot = self.snapshots[-1]

            for metric in latest_snapshot.metrics:
                if metric.name in self.thresholds:
                    threshold = self.thresholds[metric.name]
                    performance_level = threshold.check_threshold(metric.value)

                    # 경고 수준 이상인 경우 알림
                    if performance_level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                        self._trigger_performance_alert(metric, threshold, performance_level)

        except Exception as e:
            logger.error(f"임계값 확인 및 알림 실패: {str(e)}")

    def _trigger_performance_alert(
        self, metric: PerformanceMetric, threshold: PerformanceThreshold, level: PerformanceLevel
    ) -> None:
        """성능 알림을 발생시킵니다"""
        try:
            alert_message = {
                "timestamp": datetime.now().isoformat(),
                "level": level.value,
                "metric_name": metric.name,
                "current_value": metric.value,
                "unit": metric.unit,
                "warning_threshold": threshold.warning_threshold,
                "critical_threshold": threshold.critical_threshold,
                "message": f"성능 메트릭 '{metric.name}'이 임계값을 초과했습니다: "
                f"{metric.value}{metric.unit} (경고: {threshold.warning_threshold}, "
                f"위험: {threshold.critical_threshold})",
            }

            logger.warning(f"성능 알림: {alert_message['message']}")

            # 콜백 함수들 호출
            for callback in self.settings["performance_alert_callbacks"]:
                try:
                    callback(alert_message)
                except Exception as e:
                    logger.error(f"성능 알림 콜백 실행 실패: {str(e)}")

        except Exception as e:
            logger.error(f"성능 알림 발생 실패: {str(e)}")

    def add_performance_alert_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """성능 알림 콜백을 추가합니다"""
        try:
            if callback not in self.settings["performance_alert_callbacks"]:
                self.settings["performance_alert_callbacks"].append(callback)
                logger.info("성능 알림 콜백이 추가되었습니다")

        except Exception as e:
            logger.error(f"성능 알림 콜백 추가 실패: {str(e)}")

    def remove_performance_alert_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """성능 알림 콜백을 제거합니다"""
        try:
            if callback in self.settings["performance_alert_callbacks"]:
                self.settings["performance_alert_callbacks"].remove(callback)
                logger.info("성능 알림 콜백이 제거되었습니다")

        except Exception as e:
            logger.error(f"성능 알림 콜백 제거 실패: {str(e)}")

    def record_operation(
        self, operation_name: str, start_time: float, success: bool = True, error_message: str = ""
    ) -> None:
        """작업을 기록합니다"""
        try:
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # 밀리초로 변환

            # 메트릭 생성
            metric = PerformanceMetric(
                name=f"{operation_name}_duration",
                value=duration,
                unit="ms",
                timestamp=end_time,
                metric_type=MetricType.TIMING,
                tags={"operation": operation_name, "success": success},
            )

            self.metrics.append(metric)

            # 통계 업데이트
            self.performance_stats["total_operations"] += 1
            if success:
                self.performance_stats["successful_operations"] += 1
            else:
                self.performance_stats["failed_operations"] += 1

            # 평균 응답 시간 업데이트
            total_successful = self.performance_stats["successful_operations"]
            if total_successful > 0:
                current_avg = self.performance_stats["average_response_time"]
                new_avg = (current_avg * (total_successful - 1) + duration) / total_successful
                self.performance_stats["average_response_time"] = new_avg

            # 피크 값 업데이트
            if duration > self.performance_stats.get("peak_response_time", 0):
                self.performance_stats["peak_response_time"] = duration

            # 히스토리 크기 제한
            if len(self.metrics) > self.settings["max_metrics_history"]:
                self.metrics = self.metrics[-self.settings["max_metrics_history"] :]

        except Exception as e:
            logger.error(f"작업 기록 실패: {str(e)}")

    def get_performance_summary(self) -> dict[str, Any]:
        """성능 요약을 반환합니다"""
        try:
            if not self.metrics:
                return {}

            # 메트릭별 통계
            metric_stats = defaultdict(list)
            for metric in self.metrics:
                metric_stats[metric.name].append(metric.value)

            summary = {
                "monitoring_duration": time.time() - self.start_time,
                "total_metrics": len(self.metrics),
                "total_snapshots": len(self.snapshots),
                "performance_stats": self.performance_stats.copy(),
                "metric_summaries": {},
            }

            # 각 메트릭의 통계 계산
            for metric_name, values in metric_stats.items():
                if values:
                    summary["metric_summaries"][metric_name] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "average": sum(values) / len(values),
                        "latest": values[-1] if values else 0,
                    }

            return summary

        except Exception as e:
            logger.error(f"성능 요약 생성 실패: {str(e)}")
            return {}

    def export_performance_report(self, output_path: Optional[Path] = None) -> str:
        """성능 리포트를 내보냅니다"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "performance_summary": self.get_performance_summary(),
                "recent_snapshots": [
                    snapshot.to_dict() for snapshot in self.snapshots[-10:]
                ],  # 최근 10개
                "thresholds": {
                    name: {
                        "warning_threshold": threshold.warning_threshold,
                        "critical_threshold": threshold.critical_threshold,
                        "operator": threshold.operator,
                    }
                    for name, threshold in self.thresholds.items()
                },
                "settings": self.settings.copy(),
            }

            report_json = json.dumps(report, indent=2, ensure_ascii=False)

            if output_path:
                output_path.write_text(report_json, encoding="utf-8")
                logger.info(f"성능 리포트가 내보내졌습니다: {output_path}")

            return report_json

        except Exception as e:
            logger.error(f"성능 리포트 내보내기 실패: {str(e)}")
            return ""

    def clear_history(self) -> None:
        """성능 히스토리를 정리합니다"""
        try:
            self.metrics.clear()
            self.snapshots.clear()
            self.performance_stats = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "average_response_time": 0.0,
                "peak_memory_usage": 0,
                "peak_cpu_usage": 0.0,
            }

            logger.info("성능 히스토리가 정리되었습니다")

        except Exception as e:
            logger.error(f"성능 히스토리 정리 실패: {str(e)}")

    def update_settings(self, new_settings: dict[str, Any]) -> None:
        """모니터링 설정을 업데이트합니다"""
        try:
            self.settings.update(new_settings)
            logger.info("성능 모니터링 설정이 업데이트되었습니다")

        except Exception as e:
            logger.error(f"설정 업데이트 실패: {str(e)}")


# 편의 함수들
def create_performance_monitor(theme_manager=None) -> PerformanceMonitor:
    """PerformanceMonitor 인스턴스를 생성합니다"""
    return PerformanceMonitor(theme_manager)


def measure_operation(monitor: PerformanceMonitor, operation_name: str):
    """작업 측정 데코레이터"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                monitor.record_operation(operation_name, start_time, success=True)
                return result
            except Exception as e:
                monitor.record_operation(
                    operation_name, start_time, success=False, error_message=str(e)
                )
                raise

        return wrapper

    return decorator
