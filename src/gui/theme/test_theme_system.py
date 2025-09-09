"""
테마 시스템 테스트 애플리케이션
PyQt5 애플리케이션에서 테마 시스템을 테스트합니다.
"""

import logging
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QComboBox, QGroupBox, QHBoxLayout,
                             QLabel, QMainWindow, QPushButton, QSlider,
                             QSpinBox, QVBoxLayout, QWidget)

# 테마 시스템 import
from src.gui.theme.engine.manager import ThemeManager
from src.gui.theme.engine.types import A11yOptions, ThemeMode

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThemeTestWindow(QMainWindow):
    """테마 시스템을 테스트하는 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.init_ui()
        self.apply_theme(ThemeMode.LIGHT)

    def init_ui(self):
        """UI를 초기화합니다."""
        self.setWindowTitle("테마 시스템 테스트")
        self.setGeometry(100, 100, 800, 600)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)

        # 테마 선택 그룹
        theme_group = QGroupBox("테마 선택")
        theme_layout = QHBoxLayout(theme_group)

        # 테마 모드 선택
        self.theme_combo = QComboBox()
        for mode in ThemeMode:
            self.theme_combo.addItem(mode.value, mode)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(QLabel("테마 모드:"))
        theme_layout.addWidget(self.theme_combo)

        # 테마 적용 버튼
        apply_btn = QPushButton("테마 적용")
        apply_btn.clicked.connect(self.apply_current_theme)
        theme_layout.addWidget(apply_btn)

        main_layout.addWidget(theme_group)

        # 접근성 옵션 그룹
        a11y_group = QGroupBox("접근성 옵션")
        a11y_layout = QVBoxLayout(a11y_group)

        # 폰트 스케일
        font_scale_layout = QHBoxLayout()
        font_scale_layout.addWidget(QLabel("폰트 스케일:"))
        self.font_scale_slider = QSlider(Qt.Horizontal)
        self.font_scale_slider.setRange(50, 200)
        self.font_scale_slider.setValue(100)
        self.font_scale_slider.valueChanged.connect(self.on_font_scale_changed)
        font_scale_layout.addWidget(self.font_scale_slider)

        self.font_scale_spin = QSpinBox()
        self.font_scale_spin.setRange(50, 200)
        self.font_scale_spin.setValue(100)
        self.font_scale_spin.valueChanged.connect(self.font_scale_slider.setValue)
        font_scale_layout.addWidget(self.font_scale_spin)
        a11y_layout.addLayout(font_scale_layout)

        # 색상 대비 향상
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("색상 대비 향상:"))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(100, 300)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        contrast_layout.addWidget(self.contrast_slider)

        self.contrast_spin = QSpinBox()
        self.contrast_spin.setRange(100, 300)
        self.contrast_spin.setValue(100)
        self.contrast_spin.valueChanged.connect(self.contrast_slider.setValue)
        contrast_layout.addWidget(self.contrast_spin)
        a11y_layout.addLayout(contrast_layout)

        # 접근성 옵션 적용 버튼
        a11y_apply_btn = QPushButton("접근성 옵션 적용")
        a11y_apply_btn.clicked.connect(self.apply_a11y_options)
        a11y_layout.addWidget(a11y_apply_btn)

        main_layout.addWidget(a11y_group)

        # 테스트 위젯들 그룹
        test_group = QGroupBox("테스트 위젯들")
        test_layout = QVBoxLayout(test_group)

        # 버튼들
        button_layout = QHBoxLayout()
        button_layout.addWidget(QPushButton("기본 버튼"))
        button_layout.addWidget(QPushButton("주요 버튼"))
        button_layout.addWidget(QPushButton("보조 버튼"))
        test_layout.addLayout(button_layout)

        # 입력 필드들
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("이름:"))
        input_layout.addWidget(QComboBox())
        input_layout.addWidget(QLabel("나이:"))
        input_layout.addWidget(QSpinBox())
        test_layout.addLayout(input_layout)

        # 테이블 시뮬레이션
        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("테이블 행:"))
        table_layout.addWidget(QSpinBox())
        table_layout.addWidget(QLabel("테이블 열:"))
        table_layout.addWidget(QSpinBox())
        test_layout.addLayout(table_layout)

        main_layout.addWidget(test_group)

        # 정보 표시 그룹
        info_group = QGroupBox("시스템 정보")
        info_layout = QVBoxLayout(info_group)

        # 현재 테마 정보
        self.theme_info_label = QLabel("현재 테마: Light")
        info_layout.addWidget(self.theme_info_label)

        # 성능 메트릭
        self.metrics_label = QLabel("성능 메트릭: 로딩 중...")
        info_layout.addWidget(self.metrics_label)

        # 검증 결과
        self.validation_label = QLabel("검증 결과: 확인되지 않음")
        info_layout.addWidget(self.validation_label)

        main_layout.addWidget(info_group)

        # 하단 버튼들
        bottom_layout = QHBoxLayout()

        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.refresh_theme)
        bottom_layout.addWidget(refresh_btn)

        validate_btn = QPushButton("테마 검증")
        validate_btn.clicked.connect(self.validate_theme)
        bottom_layout.addWidget(validate_btn)

        metrics_btn = QPushButton("성능 메트릭")
        metrics_btn.clicked.connect(self.show_metrics)
        bottom_layout.addWidget(metrics_btn)

        clear_cache_btn = QPushButton("캐시 정리")
        clear_cache_btn.clicked.connect(self.clear_cache)
        bottom_layout.addWidget(clear_cache_btn)

        main_layout.addLayout(bottom_layout)

    def on_theme_changed(self, index):
        """테마가 변경되었을 때 호출됩니다."""
        theme_mode = self.theme_combo.currentData()
        self.apply_theme(theme_mode)

    def apply_current_theme(self):
        """현재 선택된 테마를 적용합니다."""
        theme_mode = self.theme_combo.currentData()
        self.apply_theme(theme_mode)

    def apply_theme(self, theme_mode: ThemeMode):
        """테마를 적용합니다."""
        try:
            # 현재 접근성 옵션 가져오기
            a11y_options = A11yOptions(
                font_scale=self.font_scale_slider.value() / 100.0,
                contrast_boost=self.contrast_slider.value() / 100.0,
            )

            # 테마 적용
            success = self.theme_manager.apply(theme_mode, a11y_options)

            if success:
                self.theme_info_label.setText(f"현재 테마: {theme_mode.value}")
                logger.info(f"테마 적용 성공: {theme_mode.value}")
            else:
                logger.error(f"테마 적용 실패: {theme_mode.value}")

        except Exception as e:
            logger.error(f"테마 적용 중 오류: {e}")

    def on_font_scale_changed(self, value):
        """폰트 스케일이 변경되었을 때 호출됩니다."""
        self.font_scale_spin.setValue(value)

    def on_contrast_changed(self, value):
        """색상 대비가 변경되었을 때 호출됩니다."""
        self.contrast_spin.setValue(value)

    def apply_a11y_options(self):
        """접근성 옵션을 적용합니다."""
        try:
            a11y_options = A11yOptions(
                font_scale=self.font_scale_slider.value() / 100.0,
                contrast_boost=self.contrast_slider.value() / 100.0,
            )

            # 현재 테마에 접근성 옵션 적용
            current_mode = self.theme_combo.currentData()
            success = self.theme_manager.apply(current_mode, a11y_options)

            if success:
                logger.info("접근성 옵션 적용 성공")
            else:
                logger.error("접근성 옵션 적용 실패")

        except Exception as e:
            logger.error(f"접근성 옵션 적용 중 오류: {e}")

    def refresh_theme(self):
        """테마를 새로고침합니다."""
        try:
            current_mode = self.theme_combo.currentData()
            success = self.theme_manager.reload_theme()

            if success:
                logger.info("테마 새로고침 성공")
            else:
                logger.error("테마 새로고침 실패")

        except Exception as e:
            logger.error(f"테마 새로고침 중 오류: {e}")

    def validate_theme(self):
        """현재 테마를 검증합니다."""
        try:
            validation_result = self.theme_manager.validate_current_theme()

            if validation_result["is_valid"]:
                self.validation_label.setText("검증 결과: ✅ 유효함")
                logger.info("테마 검증 성공")
            else:
                errors = validation_result.get("errors", [])
                self.validation_label.setText(f"검증 결과: ❌ 오류 {len(errors)}개")
                logger.warning(f"테마 검증 실패: {errors}")

        except Exception as e:
            logger.error(f"테마 검증 중 오류: {e}")

    def show_metrics(self):
        """성능 메트릭을 표시합니다."""
        try:
            metrics = self.theme_manager.get_performance_metrics()

            # 메트릭 정보 표시
            metrics_text = "성능 메트릭:\n"
            if "token_loader" in metrics:
                token_metrics = metrics["token_loader"]
                if "hit_rate_percent" in token_metrics:
                    metrics_text += f"토큰 캐시 히트율: {token_metrics['hit_rate_percent']}%\n"

            if "template_loader" in metrics:
                template_metrics = metrics["template_loader"]
                if "template_stats" in template_metrics:
                    stats = template_metrics["template_stats"]
                    metrics_text += f"템플릿 렌더링: {stats.get('total_renders', 0)}회\n"

            self.metrics_label.setText(metrics_text)
            logger.info("성능 메트릭 표시 완료")

        except Exception as e:
            logger.error(f"성능 메트릭 표시 중 오류: {e}")

    def clear_cache(self):
        """캐시를 정리합니다."""
        try:
            self.theme_manager.clear_cache()
            logger.info("캐시 정리 완료")
        except Exception as e:
            logger.error(f"캐시 정리 중 오류: {e}")


def main():
    """메인 함수"""
    app = QApplication(sys.argv)

    # 테마 테스트 윈도우 생성
    window = ThemeTestWindow()
    window.show()

    # 애플리케이션 실행
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
