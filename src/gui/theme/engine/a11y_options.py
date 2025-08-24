"""
접근성 옵션 및 검증 시스템

이 모듈은 테마 시스템의 접근성을 관리하고 WCAG 2.1 AA/AAA 기준 준수를 검증합니다.
고대비 모드, 폰트 크기 조정, 색상 대비 강화 등의 기능을 제공합니다.
"""

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from .color_utils import ColorUtils
from .token_loader import TokenLoader

logger = logging.getLogger(__name__)


class AccessibilityLevel(Enum):
    """접근성 수준 열거형"""

    NONE = "none"
    AA = "aa"  # WCAG 2.1 AA 기준
    AAA = "aaa"  # WCAG 2.1 AAA 기준


class FontSizeLevel(Enum):
    """폰트 크기 수준 열거형"""

    SMALL = "small"
    NORMAL = "normal"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


@dataclass
class AccessibilitySettings:
    """접근성 설정 데이터 클래스"""

    # 기본 접근성 설정
    enabled: bool = True
    level: AccessibilityLevel = AccessibilityLevel.AA

    # 고대비 모드
    high_contrast_enabled: bool = False
    high_contrast_threshold: float = 7.0  # AAA 기준

    # 폰트 크기 조정
    font_size_level: FontSizeLevel = FontSizeLevel.NORMAL
    font_size_multiplier: float = 1.0
    min_font_size: int = 12
    max_font_size: int = 24

    # 색상 대비 강화
    color_contrast_enhancement: bool = False
    min_contrast_ratio: float = 4.5  # AA 기준
    target_contrast_ratio: float = 7.0  # AAA 기준

    # 포커스 및 네비게이션
    focus_indicators_enabled: bool = True
    focus_indicator_color: str = "#0078d4"
    focus_indicator_width: int = 2

    # 스크린 리더 지원
    screen_reader_support: bool = True
    accessible_names_enabled: bool = True

    # 테마 검증
    theme_validation_enabled: bool = True
    auto_fix_contrast: bool = False


class A11yOptions(QObject):
    """접근성 옵션 관리 클래스"""

    # 시그널 정의
    accessibility_changed = pyqtSignal(bool)  # 접근성 모드 변경
    high_contrast_changed = pyqtSignal(bool)  # 고대비 모드 변경
    font_size_changed = pyqtSignal(str)  # 폰트 크기 변경
    contrast_enhanced = pyqtSignal(bool)  # 색상 대비 강화 변경
    validation_completed = pyqtSignal(dict)  # 검증 완료

    def __init__(self, app: QApplication = None, config_path: Optional[Union[str, Path]] = None):
        super().__init__()
        self.app = app or QApplication.instance()
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(__file__).parent.parent / "config" / "a11y.json"
        )

        # 유틸리티 클래스들
        self.color_utils = ColorUtils()
        self.token_loader = TokenLoader()

        # 설정 및 상태
        self.settings = AccessibilitySettings()
        self.qsettings = QSettings("AnimeSorter", "ThemeEngine")

        # 테마 검증 결과 캐시
        self._validation_cache: dict[str, dict[str, Any]] = {}

        # 초기화
        self._load_settings()
        self._setup_defaults()
        logger.info("A11yOptions 초기화 완료")

    def _load_settings(self) -> None:
        """설정 파일에서 접근성 옵션 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as f:
                    config_data = json.load(f)
                    self._apply_config(config_data)
                    logger.info(f"접근성 설정 로드 완료: {self.config_path}")
            else:
                logger.info("접근성 설정 파일이 없습니다. 기본값을 사용합니다.")
        except Exception as e:
            logger.error(f"접근성 설정 로드 실패: {e}")

    def _save_settings(self) -> None:
        """현재 설정을 파일에 저장"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Enum 값을 문자열로 변환하여 JSON 직렬화 가능하게 함
            settings_dict = asdict(self.settings)
            for key, value in settings_dict.items():
                if isinstance(value, Enum):
                    settings_dict[key] = value.value

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"접근성 설정 저장 완료: {self.config_path}")
        except Exception as e:
            logger.error(f"접근성 설정 저장 실패: {e}")

    def _apply_config(self, config_data: dict[str, Any]) -> None:
        """설정 데이터를 클래스에 적용"""
        try:
            # 기본 설정
            if "enabled" in config_data:
                self.settings.enabled = config_data["enabled"]

            if "level" in config_data:
                self.settings.level = AccessibilityLevel(config_data["level"])

            # 고대비 모드
            if "high_contrast_enabled" in config_data:
                self.settings.high_contrast_enabled = config_data["high_contrast_enabled"]

            if "high_contrast_threshold" in config_data:
                self.settings.high_contrast_threshold = config_data["high_contrast_threshold"]

            # 폰트 크기
            if "font_size_level" in config_data:
                self.settings.font_size_level = FontSizeLevel(config_data["font_size_level"])

            if "font_size_multiplier" in config_data:
                self.settings.font_size_multiplier = config_data["font_size_multiplier"]

            # 색상 대비
            if "color_contrast_enhancement" in config_data:
                self.settings.color_contrast_enhancement = config_data["color_contrast_enhancement"]

            if "min_contrast_ratio" in config_data:
                self.settings.min_contrast_ratio = config_data["min_contrast_ratio"]

            if "target_contrast_ratio" in config_data:
                self.settings.target_contrast_ratio = config_data["target_contrast_ratio"]

            # 포커스 표시
            if "focus_indicators_enabled" in config_data:
                self.settings.focus_indicators_enabled = config_data["focus_indicators_enabled"]

            if "focus_indicator_color" in config_data:
                self.settings.focus_indicator_color = config_data["focus_indicator_color"]

            if "focus_indicator_width" in config_data:
                self.settings.focus_indicator_width = config_data["focus_indicator_width"]

            # 스크린 리더
            if "screen_reader_support" in config_data:
                self.settings.screen_reader_support = config_data["screen_reader_support"]

            if "accessible_names_enabled" in config_data:
                self.settings.accessible_names_enabled = config_data["accessible_names_enabled"]

            # 테마 검증
            if "theme_validation_enabled" in config_data:
                self.settings.theme_validation_enabled = config_data["theme_validation_enabled"]

            if "auto_fix_contrast" in config_data:
                self.settings.auto_fix_contrast = config_data["auto_fix_contrast"]

        except Exception as e:
            logger.error(f"설정 적용 실패: {e}")

    def _setup_defaults(self) -> None:
        """기본 설정 초기화"""
        # QSettings에서 저장된 값 로드
        self.settings.enabled = self.qsettings.value("a11y/enabled", True, type=bool)
        self.settings.high_contrast_enabled = self.qsettings.value(
            "a11y/high_contrast_enabled", False, type=bool
        )
        self.settings.font_size_level = FontSizeLevel(
            self.qsettings.value("a11y/font_size_level", "normal")
        )
        self.settings.color_contrast_enhancement = self.qsettings.value(
            "a11y/color_contrast_enhancement", False, type=bool
        )

        # 폰트 크기 배수 계산
        self._update_font_size_multiplier()

    def _update_font_size_multiplier(self) -> None:
        """폰트 크기 수준에 따른 배수 업데이트"""
        size_multipliers = {
            FontSizeLevel.SMALL: 0.8,
            FontSizeLevel.NORMAL: 1.0,
            FontSizeLevel.LARGE: 1.2,
            FontSizeLevel.EXTRA_LARGE: 1.5,
        }
        self.settings.font_size_multiplier = size_multipliers.get(
            self.settings.font_size_level, 1.0
        )

    def get_settings(self) -> AccessibilitySettings:
        """현재 접근성 설정 반환"""
        return self.settings

    def update_settings(self, **kwargs) -> bool:
        """접근성 설정 업데이트"""
        try:
            settings_changed = False

            for key, value in kwargs.items():
                if hasattr(self.settings, key):
                    old_value = getattr(self.settings, key)
                    setattr(self.settings, key, value)

                    if old_value != value:
                        settings_changed = True
                        logger.info(f"접근성 설정 변경: {key} = {value}")

            if settings_changed:
                # 폰트 크기 배수 업데이트
                if "font_size_level" in kwargs:
                    self._update_font_size_multiplier()

                # 설정 저장
                self._save_settings()

                # QSettings에 저장
                for key, value in kwargs.items():
                    if hasattr(self.settings, key):
                        self.qsettings.setValue(f"a11y/{key}", value)

                # 시그널 발생
                self.accessibility_changed.emit(self.settings.enabled)

                if "high_contrast_enabled" in kwargs:
                    self.high_contrast_changed.emit(self.settings.high_contrast_enabled)

                if "font_size_level" in kwargs:
                    self.font_size_changed.emit(self.settings.font_size_level.value)

                if "color_contrast_enhancement" in kwargs:
                    self.contrast_enhanced.emit(self.settings.color_contrast_enhancement)

            return True

        except Exception as e:
            logger.error(f"접근성 설정 업데이트 실패: {e}")
            return False

    def is_high_contrast_enabled(self) -> bool:
        """고대비 모드 활성화 여부 확인"""
        return self.settings.enabled and self.settings.high_contrast_enabled

    def get_font_size_multiplier(self) -> float:
        """현재 폰트 크기 배수 반환"""
        return self.settings.font_size_multiplier

    def get_min_contrast_ratio(self) -> float:
        """최소 색상 대비 비율 반환"""
        if self.settings.high_contrast_enabled:
            return self.settings.high_contrast_threshold
        return self.settings.min_contrast_ratio

    def get_target_contrast_ratio(self) -> float:
        """목표 색상 대비 비율 반환"""
        if self.settings.high_contrast_enabled:
            return self.settings.high_contrast_threshold
        return self.settings.target_contrast_ratio

    def validate_color_contrast(
        self, foreground: Union[str, QColor], background: Union[str, QColor]
    ) -> dict[str, Any]:
        """색상 대비 검증"""
        try:
            # QColor를 문자열로 변환
            if isinstance(foreground, QColor):
                foreground = foreground.name()
            if isinstance(background, QColor):
                background = background.name()

            # 대비 비율 계산
            contrast_ratio = self.color_utils.contrast_ratio(foreground, background)

            # WCAG 기준 준수 여부 확인
            passes_aa = contrast_ratio >= 4.5
            passes_aaa = contrast_ratio >= 7.0
            passes_current = contrast_ratio >= self.get_min_contrast_ratio()

            result = {
                "foreground": foreground,
                "background": background,
                "contrast_ratio": contrast_ratio,
                "passes_aa": passes_aa,
                "passes_aaa": passes_aaa,
                "passes_current": passes_current,
                "level": self.settings.level.value,
                "min_required": self.get_min_contrast_ratio(),
                "target": self.get_target_contrast_ratio(),
            }

            return result

        except Exception as e:
            logger.error(f"색상 대비 검증 실패: {e}")
            return {"error": str(e), "foreground": str(foreground), "background": str(background)}

    def enhance_color_contrast(
        self, foreground: Union[str, QColor], background: Union[str, QColor]
    ) -> Optional[Union[str, QColor]]:
        """색상 대비 강화"""
        if not self.settings.color_contrast_enhancement:
            return None

        try:
            target_ratio = self.get_target_contrast_ratio()
            enhanced_color = self.color_utils.find_accessible_color(
                foreground, background, target_ratio
            )

            if enhanced_color:
                logger.info(f"색상 대비 강화 완료: {foreground} -> {enhanced_color}")
                return enhanced_color
            else:
                logger.warning(f"색상 대비 강화 실패: {foreground} vs {background}")
                return None

        except Exception as e:
            logger.error(f"색상 대비 강화 실패: {e}")
            return None

    def get_accessible_color_palette(
        self, base_color: Union[str, QColor], theme: str = "light"
    ) -> dict[str, str]:
        """접근성을 고려한 색상 팔레트 생성"""
        try:
            palette = self.color_utils.generate_color_palette(base_color)
            accessible_palette = {}

            # 배경색 결정 (테마에 따라)
            if theme == "dark":
                background_color = "#121212"
            elif theme == "high-contrast":
                background_color = "#000000"
            else:
                background_color = "#ffffff"

            # 각 색상에 대해 접근성 검증
            for name, color in palette.items():
                contrast_result = self.validate_color_contrast(color, background_color)

                if contrast_result.get("passes_current", False):
                    accessible_palette[name] = str(color)
                else:
                    # 접근성을 위해 색상 조정
                    enhanced_color = self.enhance_color_contrast(color, background_color)
                    if enhanced_color:
                        accessible_palette[name] = str(enhanced_color)
                    else:
                        # 접근성 기준을 만족하지 못하는 경우 제외
                        logger.warning(f"접근성 기준 미달 색상 제외: {name} = {color}")

            return accessible_palette

        except Exception as e:
            logger.error(f"접근성 색상 팔레트 생성 실패: {e}")
            return {}

    def validate_theme_file(self, theme_file_path: Union[str, Path]) -> dict[str, Any]:
        """테마 파일 유효성 검사 및 WCAG 준수 검증"""
        try:
            theme_path = Path(theme_file_path)
            if not theme_path.exists():
                return {"valid": False, "error": "테마 파일이 존재하지 않습니다."}

            # 캐시된 결과 확인
            cache_key = f"{theme_path}_{theme_path.stat().st_mtime}"
            if cache_key in self._validation_cache:
                return self._validation_cache[cache_key]

            # 테마 파일 로드
            theme_data = self.token_loader.load_tokens(theme_path)
            if not theme_data:
                return {"valid": False, "error": "테마 파일 로드 실패"}

            validation_result = {
                "valid": True,
                "file_path": str(theme_path),
                "file_size": theme_path.stat().st_size,
                "theme_name": theme_data.get("name", "Unknown"),
                "theme_version": theme_data.get("version", "1.0.0"),
                "theme_type": theme_data.get("type", "unknown"),
                "color_tokens": 0,
                "font_tokens": 0,
                "spacing_tokens": 0,
                "contrast_issues": [],
                "accessibility_score": 0.0,
                "wcag_compliance": {"aa": False, "aaa": False},
                "detailed_analysis": {
                    "color_contrast": {},
                    "font_accessibility": {},
                    "spacing_accessibility": {},
                    "overall_rating": "unknown",
                },
                "recommendations": [],
                "accessibility_metadata": {},
            }

            # 색상 토큰 검증
            color_tokens = theme_data.get("colors", {})
            validation_result["color_tokens"] = len(color_tokens)

            # 배경색과 전경색 분류
            background_colors = []
            foreground_colors = []
            accent_colors = []

            for token_name, token_value in color_tokens.items():
                if "background" in token_name.lower() or "bg" in token_name.lower():
                    background_colors.append((token_name, token_value))
                elif "text" in token_name.lower() or "foreground" in token_name.lower():
                    foreground_colors.append((token_name, token_value))
                elif "accent" in token_name.lower() or "primary" in token_name.lower():
                    accent_colors.append((token_name, token_value))

            # 색상 대비 검증
            contrast_issues = []
            contrast_analysis = {}

            # 주요 색상 조합 검증
            test_combinations = []

            # 배경색과 전경색 조합
            for bg_name, bg_color in background_colors[:3]:
                for fg_name, fg_color in foreground_colors[:3]:
                    test_combinations.append((f"bg:{bg_name}", bg_color, f"fg:{fg_name}", fg_color))

            # 액센트 색상과 배경색 조합
            for accent_name, accent_color in accent_colors[:2]:
                for bg_name, bg_color in background_colors[:2]:
                    test_combinations.append(
                        (f"bg:{bg_name}", bg_color, f"accent:{accent_name}", accent_color)
                    )

            for bg_desc, bg_color, fg_desc, fg_color in test_combinations:
                contrast_result = self.validate_color_contrast(fg_color, bg_color)
                combination_key = f"{fg_desc}_on_{bg_desc}"

                contrast_analysis[combination_key] = {
                    "foreground": fg_color,
                    "background": bg_color,
                    "contrast_ratio": contrast_result.get("contrast_ratio", 0),
                    "passes_aa": contrast_result.get("passes_aa", False),
                    "passes_aaa": contrast_result.get("passes_aaa", False),
                    "wcag_level": self._get_wcag_level(contrast_result.get("contrast_ratio", 0)),
                }

                if not contrast_result.get("passes_aa", False):
                    contrast_issues.append(
                        {
                            "combination": combination_key,
                            "foreground": fg_color,
                            "background": bg_color,
                            "contrast_ratio": contrast_result.get("contrast_ratio", 0),
                            "required": 4.5,
                            "suggestions": self.color_utils.get_contrast_enhancement_suggestions(
                                fg_color, bg_color
                            ),
                        }
                    )

            validation_result["contrast_issues"] = contrast_issues
            validation_result["detailed_analysis"]["color_contrast"] = contrast_analysis

            # 폰트 접근성 검증
            font_tokens = theme_data.get("fonts", {})
            validation_result["font_tokens"] = len(font_tokens)

            font_analysis = self._validate_font_accessibility(font_tokens)
            validation_result["detailed_analysis"]["font_accessibility"] = font_analysis

            # 간격 접근성 검증
            spacing_tokens = theme_data.get("spacing", {})
            validation_result["spacing_tokens"] = len(spacing_tokens)

            spacing_analysis = self._validate_spacing_accessibility(spacing_tokens)
            validation_result["detailed_analysis"]["spacing_accessibility"] = spacing_analysis

            # 접근성 메타데이터 검증
            accessibility_metadata = theme_data.get("accessibility", {})
            validation_result["accessibility_metadata"] = accessibility_metadata

            # 접근성 점수 계산
            total_checks = len(test_combinations)
            passed_checks = total_checks - len(contrast_issues)
            validation_result["accessibility_score"] = (
                (passed_checks / total_checks * 100) if total_checks > 0 else 0
            )

            # WCAG 준수 여부
            validation_result["wcag_compliance"]["aa"] = len(contrast_issues) == 0
            validation_result["wcag_compliance"]["aaa"] = all(
                contrast_analysis[combo]["passes_aaa"] for combo in contrast_analysis.keys()
            )

            # 전체 등급 결정
            validation_result["detailed_analysis"]["overall_rating"] = (
                self._determine_overall_rating(
                    validation_result["accessibility_score"], validation_result["wcag_compliance"]
                )
            )

            # 권장사항 생성
            validation_result["recommendations"] = self._generate_validation_recommendations(
                validation_result, contrast_issues, font_analysis, spacing_analysis
            )

            # 결과 캐시
            self._validation_cache[cache_key] = validation_result

            return validation_result

        except Exception as e:
            logger.error(f"테마 파일 검증 실패: {e}")
            return {"valid": False, "error": str(e), "file_path": str(theme_file_path)}

    def _get_wcag_level(self, contrast_ratio: float) -> str:
        """대비 비율에 따른 WCAG 수준 반환"""
        if contrast_ratio >= 7.0:
            return "AAA"
        elif contrast_ratio >= 4.5:
            return "AA"
        elif contrast_ratio >= 3.0:
            return "A"
        else:
            return "FAIL"

    def _validate_font_accessibility(self, font_tokens: dict[str, Any]) -> dict[str, Any]:
        """폰트 접근성 검증"""
        try:
            analysis = {"valid": True, "issues": [], "recommendations": []}

            # 폰트 크기 검증
            font_sizes = font_tokens.get("size", {})
            min_size = 12  # 최소 권장 폰트 크기 (px)

            for size_name, size_value in font_sizes.items():
                try:
                    # "12px" 형태의 문자열에서 숫자 추출
                    if isinstance(size_value, str) and "px" in size_value:
                        size_num = int(size_value.replace("px", ""))
                        if size_num < min_size:
                            analysis["issues"].append(
                                f"폰트 크기가 너무 작습니다: {size_name} = {size_value}"
                            )
                            analysis["valid"] = False
                except (ValueError, TypeError):
                    analysis["issues"].append(
                        f"폰트 크기 형식이 잘못되었습니다: {size_name} = {size_value}"
                    )
                    analysis["valid"] = False

            # 폰트 패밀리 검증
            font_families = font_tokens.get("family", {})
            for family_name, family_value in font_families.items():
                if not isinstance(family_value, str) or len(family_value.strip()) == 0:
                    analysis["issues"].append(f"폰트 패밀리가 정의되지 않았습니다: {family_name}")
                    analysis["valid"] = False

            # 권장사항 생성
            if analysis["issues"]:
                analysis["recommendations"].append("폰트 크기는 최소 12px 이상으로 설정하세요.")
                analysis["recommendations"].append(
                    "폰트 패밀리는 fallback 폰트를 포함하여 정의하세요."
                )

            return analysis

        except Exception as e:
            logger.error(f"폰트 접근성 검증 실패: {e}")
            return {"valid": False, "error": str(e)}

    def _validate_spacing_accessibility(self, spacing_tokens: dict[str, Any]) -> dict[str, Any]:
        """간격 접근성 검증"""
        try:
            analysis = {"valid": True, "issues": [], "recommendations": []}

            # 최소 간격 검증
            min_spacing = 4  # 최소 권장 간격 (px)

            for spacing_name, spacing_value in spacing_tokens.items():
                try:
                    if isinstance(spacing_value, str) and "px" in spacing_value:
                        spacing_num = int(spacing_value.replace("px", ""))
                        if spacing_num < min_spacing:
                            analysis["issues"].append(
                                f"간격이 너무 작습니다: {spacing_name} = {spacing_value}"
                            )
                            analysis["valid"] = False
                except (ValueError, TypeError):
                    analysis["issues"].append(
                        f"간격 형식이 잘못되었습니다: {spacing_name} = {spacing_value}"
                    )
                    analysis["valid"] = False

            # 권장사항 생성
            if analysis["issues"]:
                analysis["recommendations"].append("요소 간 간격은 최소 4px 이상으로 설정하세요.")
                analysis["recommendations"].append(
                    "터치 인터페이스를 위한 충분한 간격을 확보하세요."
                )

            return analysis

        except Exception as e:
            logger.error(f"간격 접근성 검증 실패: {e}")
            return {"valid": False, "error": str(e)}

    def _determine_overall_rating(
        self, accessibility_score: float, wcag_compliance: dict[str, bool]
    ) -> str:
        """전체 접근성 등급 결정"""
        if accessibility_score >= 95 and wcag_compliance.get("aaa", False):
            return "excellent"
        elif accessibility_score >= 90 and wcag_compliance.get("aa", False):
            return "very_good"
        elif accessibility_score >= 80 and wcag_compliance.get("aa", False):
            return "good"
        elif accessibility_score >= 70:
            return "fair"
        elif accessibility_score >= 50:
            return "poor"
        else:
            return "very_poor"

    def _generate_validation_recommendations(
        self,
        validation_result: dict[str, Any],
        contrast_issues: list[dict[str, Any]],
        font_analysis: dict[str, Any],
        spacing_analysis: dict[str, Any],
    ) -> list[str]:
        """검증 결과를 바탕으로 권장사항 생성"""
        recommendations = []

        # 색상 대비 관련 권장사항
        if contrast_issues:
            recommendations.append(
                f"{len(contrast_issues)}개의 색상 조합이 WCAG AA 기준을 충족하지 않습니다."
            )
            recommendations.append("색상 대비 강화 기능을 활성화하거나 색상을 수동으로 조정하세요.")

            # 구체적인 제안사항 추가
            for issue in contrast_issues[:3]:  # 상위 3개만
                if "suggestions" in issue:
                    recommendations.extend(issue["suggestions"][:2])  # 각 이슈당 최대 2개 제안

        # 폰트 관련 권장사항
        if not font_analysis.get("valid", True):
            recommendations.extend(font_analysis.get("recommendations", []))

        # 간격 관련 권장사항
        if not spacing_analysis.get("valid", True):
            recommendations.extend(spacing_analysis.get("recommendations", []))

        # 전체적인 접근성 점수 관련 권장사항
        accessibility_score = validation_result.get("accessibility_score", 0)
        if accessibility_score < 80:
            recommendations.append("전체적인 접근성 점수가 낮습니다. 테마를 전면적으로 검토하세요.")
        elif accessibility_score < 90:
            recommendations.append(
                "접근성을 더욱 향상시킬 수 있습니다. 세부적인 조정을 고려하세요."
            )

        # WCAG 준수 관련 권장사항
        if not validation_result["wcag_compliance"].get("aa", False):
            recommendations.append(
                "WCAG AA 기준을 충족하지 않습니다. 기본적인 접근성 요구사항을 만족해야 합니다."
            )

        if not validation_result["wcag_compliance"].get("aaa", False):
            recommendations.append(
                "WCAG AAA 기준을 충족하지 않습니다. 고대비 모드 사용자를 위한 추가 개선이 필요합니다."
            )

        return recommendations

    def get_validation_summary(self) -> dict[str, Any]:
        """전체 검증 결과 요약"""
        try:
            summary = {
                "total_validations": len(self._validation_cache),
                "valid_themes": 0,
                "invalid_themes": 0,
                "wcag_aa_compliant": 0,
                "wcag_aaa_compliant": 0,
                "average_accessibility_score": 0.0,
                "total_contrast_issues": 0,
            }

            if not self._validation_cache:
                return summary

            total_score = 0
            for result in self._validation_cache.values():
                if result.get("valid", False):
                    summary["valid_themes"] += 1
                    if result.get("wcag_compliance", {}).get("aa", False):
                        summary["wcag_aa_compliant"] += 1
                    if result.get("wcag_compliance", {}).get("aaa", False):
                        summary["wcag_aaa_compliant"] += 1

                    total_score += result.get("accessibility_score", 0)
                    summary["total_contrast_issues"] += len(result.get("contrast_issues", []))
                else:
                    summary["invalid_themes"] += 1

            if summary["valid_themes"] > 0:
                summary["average_accessibility_score"] = total_score / summary["valid_themes"]

            return summary

        except Exception as e:
            logger.error(f"검증 결과 요약 생성 실패: {e}")
            return {"error": str(e)}

    def clear_validation_cache(self) -> None:
        """검증 결과 캐시 정리"""
        self._validation_cache.clear()
        logger.info("검증 결과 캐시 정리 완료")

    def export_validation_report(self, output_path: Union[str, Path]) -> bool:
        """검증 결과 보고서 내보내기"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            report_data = {
                "settings": asdict(self.settings),
                "validation_summary": self.get_validation_summary(),
                "detailed_results": self._validation_cache,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"검증 결과 보고서 내보내기 완료: {output_path}")
            return True

        except Exception as e:
            logger.error(f"검증 결과 보고서 내보내기 실패: {e}")
            return False

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            self._save_settings()
            self.clear_validation_cache()
            logger.info("A11yOptions 정리 완료")
        except Exception as e:
            logger.error(f"A11yOptions 정리 실패: {e}")


# 편의 함수들
def create_a11y_options(
    app: QApplication = None, config_path: Optional[Union[str, Path]] = None
) -> A11yOptions:
    """A11yOptions 인스턴스 생성 편의 함수"""
    return A11yOptions(app, config_path)


def validate_theme_accessibility(
    theme_file_path: Union[str, Path], a11y_options: Optional[A11yOptions] = None
) -> dict[str, Any]:
    """테마 파일 접근성 검증 편의 함수"""
    if a11y_options is None:
        a11y_options = A11yOptions()

    return a11y_options.validate_theme_file(theme_file_path)
