"""
품질 메트릭 대시보드 - Phase 5.4
수집된 품질 메트릭을 시각적으로 표시하고 모니터링합니다.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class QualityDashboard:
    """품질 메트릭 대시보드 클래스"""

    def __init__(self, metrics_file: str = ".taskmaster/quality_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics_data = {}
        self.load_metrics_data()

    def load_metrics_data(self):
        """메트릭 데이터 로드"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, encoding="utf-8") as f:
                    self.metrics_data = json.load(f)
                print(f"📊 메트릭 데이터 로드됨: {self.metrics_file}")
            except Exception as e:
                print(f"⚠️ 메트릭 데이터 로드 실패: {e}")
                self.metrics_data = {}
        else:
            print(f"❌ 메트릭 파일을 찾을 수 없음: {self.metrics_file}")

    def display_summary_dashboard(self):
        """요약 대시보드 표시"""
        if not self.metrics_data:
            print("❌ 표시할 메트릭 데이터가 없습니다.")
            return

        print("=" * 80)
        print("🎯 AnimeSorter 품질 메트릭 대시보드")
        print("=" * 80)
        print(f"📅 마지막 업데이트: {self.metrics_file.stat().st_mtime}")
        print(f"📊 총 메트릭: {self.metrics_data.get('total_metrics', 0)}개")
        print("")

        # 상태별 요약
        self._display_status_summary()
        print("")

        # 카테고리별 요약
        self._display_category_summary()
        print("")

        # 상세 메트릭
        self._display_detailed_metrics()
        print("")

        # 트렌드 분석
        self._display_trends()
        print("")

        # 품질 점수 계산
        self._display_quality_score()

    def _display_status_summary(self):
        """상태별 요약 표시"""
        print("📊 상태별 요약:")
        print("-" * 40)

        current_metrics = self.metrics_data.get("metrics", [])
        if not current_metrics:
            print("  표시할 메트릭이 없습니다.")
            return

        # 상태별 카운트
        status_counts = {}
        for metric in current_metrics:
            status = metric.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1

        # 상태별 이모지와 색상
        status_icons = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "UNKNOWN": "❓"}

        for status, count in status_counts.items():
            icon = status_icons.get(status, "❓")
            print(f"  {icon} {status}: {count}개")

    def _display_category_summary(self):
        """카테고리별 요약 표시"""
        print("📁 카테고리별 요약:")
        print("-" * 40)

        current_metrics = self.metrics_data.get("metrics", [])
        if not current_metrics:
            print("  표시할 메트릭이 없습니다.")
            return

        # 카테고리별 그룹화
        categories = {}
        for metric in current_metrics:
            category = metric.get("category", "Unknown")
            if category not in categories:
                categories[category] = {"total": 0, "pass": 0, "warning": 0, "fail": 0}

            categories[category]["total"] += 1
            status = metric.get("status", "UNKNOWN")
            if status in categories[category]:
                categories[category][status] += 1

        # 카테고리별 표시
        for category, counts in categories.items():
            total = counts["total"]
            pass_rate = (counts["pass"] / total) * 100 if total > 0 else 0

            # 통과율에 따른 이모지
            if pass_rate >= 80:
                icon = "🟢"
            elif pass_rate >= 60:
                icon = "🟡"
            else:
                icon = "🔴"

            print(f"  {icon} {category}: {pass_rate:.1f}% 통과 ({counts['pass']}/{total})")

    def _display_detailed_metrics(self):
        """상세 메트릭 표시"""
        print("🔍 상세 메트릭:")
        print("-" * 40)

        current_metrics = self.metrics_data.get("metrics", [])
        if not current_metrics:
            print("  표시할 메트릭이 없습니다.")
            return

        # 카테고리별로 그룹화하여 표시
        categories = {}
        for metric in current_metrics:
            category = metric.get("category", "Unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(metric)

        for category, metrics in categories.items():
            print(f"  📁 {category}:")

            for metric in metrics:
                name = metric.get("metric_name", "Unknown")
                value = metric.get("value", 0)
                unit = metric.get("unit", "")
                status = metric.get("status", "UNKNOWN")
                threshold = metric.get("threshold", 0)
                trend = metric.get("trend", "STABLE")
                details = metric.get("details", "")

                # 상태별 이모지
                status_icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "UNKNOWN": "❓"}.get(
                    status, "❓"
                )

                # 트렌드별 이모지
                trend_icon = {"IMPROVING": "📈", "STABLE": "➡️", "DECLINING": "📉"}.get(trend, "❓")

                print(f"    {status_icon} {name}: {value:.1f} {unit}")
                print(f"      기준: {threshold:.1f} {unit} | 트렌드: {trend_icon} {trend}")
                print(f"      상세: {details}")
                print("")

    def _display_trends(self):
        """트렌드 분석 표시"""
        trends = self.metrics_data.get("trends", [])
        if not trends:
            print("📈 트렌드 분석:")
            print("-" * 40)
            print("  아직 트렌드 데이터가 충분하지 않습니다.")
            return

        print("📈 트렌드 분석:")
        print("-" * 40)

        for trend in trends:
            metric_name = trend.get("metric_name", "Unknown")
            current = trend.get("current_value", 0)
            previous = trend.get("previous_value", 0)
            change_percent = trend.get("change_percentage", 0)
            direction = trend.get("trend_direction", "STABLE")
            strength = trend.get("trend_strength", "UNKNOWN")

            # 방향별 이모지
            direction_icon = {"UP": "📈", "DOWN": "📉", "STABLE": "➡️"}.get(direction, "❓")

            # 강도별 이모지
            strength_icon = {"STRONG": "🔥", "MODERATE": "⚡", "WEAK": "💨"}.get(strength, "❓")

            print(f"  {direction_icon} {metric_name}:")
            print(f"    변화율: {change_percent:+.1f}% | 강도: {strength_icon} {strength}")
            print(f"    {previous:.1f} → {current:.1f}")
            print("")

    def _display_quality_score(self):
        """품질 점수 계산 및 표시"""
        print("🎯 품질 점수 계산:")
        print("-" * 40)

        current_metrics = self.metrics_data.get("metrics", [])
        if not current_metrics:
            print("  계산할 메트릭이 없습니다.")
            return

        # 각 메트릭별 점수 계산
        total_score = 0
        max_score = len(current_metrics) * 10  # 각 메트릭당 최대 10점

        for metric in current_metrics:
            status = metric.get("status", "UNKNOWN")
            if status == "PASS":
                total_score += 10
            elif status == "WARNING":
                total_score += 6
            elif status == "FAIL":
                total_score += 2
            else:
                total_score += 5  # UNKNOWN 상태

        quality_percentage = (total_score / max_score) * 100

        # 품질 등급 결정
        if quality_percentage >= 90:
            grade = "🏆 A+ (우수)"
            grade_icon = "🏆"
        elif quality_percentage >= 80:
            grade = "✅ A (양호)"
            grade_icon = "✅"
        elif quality_percentage >= 70:
            grade = "⚠️ B (보통)"
            grade_icon = "⚠️"
        elif quality_percentage >= 60:
            grade = "🔧 C (개선 필요)"
            grade_icon = "🔧"
        else:
            grade = "❌ D (긴급 개선)"
            grade_icon = "❌"

        print(f"  {grade_icon} 전체 품질 점수: {quality_percentage:.1f}% ({grade})")
        print(f"  📊 세부 점수: {total_score}/{max_score}점")

        # 개선 권장사항
        if quality_percentage < 80:
            print("  🚨 품질 개선이 필요합니다!")
            print("  💡 목표: 80% 이상 달성")

        print("")

    def display_improvement_recommendations(self):
        """개선 권장사항 표시"""
        print("🚀 품질 개선 권장사항:")
        print("-" * 40)

        current_metrics = self.metrics_data.get("metrics", [])
        if not current_metrics:
            print("  표시할 권장사항이 없습니다.")
            return

        # FAIL 상태 메트릭 찾기
        failed_metrics = [m for m in current_metrics if m.get("status") == "FAIL"]
        warning_metrics = [m for m in current_metrics if m.get("status") == "WARNING"]

        if failed_metrics:
            print("🔴 즉시 개선 필요:")
            for metric in failed_metrics:
                name = metric.get("metric_name", "Unknown")
                details = metric.get("details", "")
                print(f"  • {name}: {details}")
            print("")

        if warning_metrics:
            print("🟡 단기 개선 계획:")
            for metric in warning_metrics:
                name = metric.get("metric_name", "Unknown")
                details = metric.get("details", "")
                print(f"  • {name}: {details}")
            print("")

        # 일반적인 권장사항
        print("💡 일반적인 품질 개선 제안:")
        print("  1. 🔍 정기적인 코드 리뷰 프로세스 구축")
        print("  2. 🧪 테스트 커버리지 90% 이상 유지")
        print("  3. 📏 코드 스타일 가이드 준수 강화")
        print("  4. 🔧 자동화된 품질 검사 도구 활용")
        print("  5. 📚 개발자 교육 및 모범 사례 공유")

    def export_dashboard_data(self) -> dict[str, Any]:
        """대시보드 데이터 export"""
        return {
            "dashboard_info": {
                "generated_at": datetime.now().isoformat(),
                "metrics_file": str(self.metrics_file),
                "total_metrics": len(self.metrics_data.get("metrics", [])),
                "data_source": "quality_metrics.json",
            },
            "summary": self.metrics_data.get("summary", {}),
            "current_metrics": self.metrics_data.get("current_metrics", []),
            "trends": self.metrics_data.get("trends", []),
        }


def main():
    """메인 실행 함수"""
    print("🎯 품질 메트릭 대시보드 시작...")

    # 대시보드 생성
    dashboard = QualityDashboard()

    # 요약 대시보드 표시
    dashboard.display_summary_dashboard()

    # 개선 권장사항 표시
    dashboard.display_improvement_recommendations()

    # 대시보드 데이터 export
    dashboard_data = dashboard.export_dashboard_data()

    print("\n📊 대시보드 요약:")
    print(f"  • 메트릭 파일: {dashboard_data['dashboard_info']['metrics_file']}")
    print(f"  • 총 메트릭: {dashboard_data['dashboard_info']['total_metrics']}개")
    print(f"  • 생성 시간: {dashboard_data['dashboard_info']['generated_at']}")

    print("\n✅ 품질 메트릭 대시보드 완료!")


if __name__ == "__main__":
    main()
