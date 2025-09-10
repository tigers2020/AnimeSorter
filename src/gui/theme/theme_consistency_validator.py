"""
테마 전환 시 스타일 일관성 검증 모듈

이 모듈은 테마 전환 시 모든 UI 요소의 스타일이 올바르게 적용되는지 검증합니다.
"""

import json
import logging

logger = logging.getLogger(__name__)
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget

from src.gui.theme.engine.theme_manager import ThemeManager
from src.gui.theme.engine.variable_loader import VariableLoader as TokenLoader


class ThemeConsistencyValidator(QObject):
    """테마 전환 시 스타일 일관성 검증 클래스"""

    validation_started = pyqtSignal(str)
    validation_completed = pyqtSignal(dict)
    validation_error = pyqtSignal(str, str)

    def __init__(self, theme_manager: ThemeManager, parent: QWidget = None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        theme_dir = Path(__file__).parent.parent.parent.parent / "data" / "theme"
        self.token_loader = TokenLoader(theme_dir)
        self.logger = logging.getLogger(__name__)
        self.available_themes = ["light", "dark", "high_contrast"]
        self.validation_results = {}

    def validate_all_themes(self) -> dict[str, dict]:
        """모든 테마에 대해 일관성 검증 수행"""
        self.logger.info("테마 일관성 검증 시작")
        self.validation_started.emit("테마 일관성 검증 시작")
        results = {}
        for theme_name in self.available_themes:
            try:
                self.logger.info(f"테마 '{theme_name}' 검증 중...")
                theme_result = self.validate_theme(theme_name)
                results[theme_name] = theme_result
                if theme_result["is_valid"]:
                    self.logger.info(f"테마 '{theme_name}' 검증 성공")
                else:
                    self.logger.warning(f"테마 '{theme_name}' 검증 실패: {theme_result['errors']}")
            except Exception as e:
                error_msg = f"테마 '{theme_name}' 검증 중 오류 발생: {str(e)}"
                self.logger.error(error_msg)
                self.validation_error.emit(theme_name, error_msg)
                results[theme_name] = {
                    "is_valid": False,
                    "errors": [error_msg],
                    "warnings": [],
                    "details": {},
                }
        self.validation_results = results
        self.validation_completed.emit(results)
        return results

    def validate_theme(self, theme_name: str) -> dict:
        """특정 테마에 대한 일관성 검증 수행"""
        result = {"is_valid": True, "errors": [], "warnings": [], "details": {}}
        try:
            theme_file_result = self._validate_theme_file(theme_name)
            result["details"]["theme_file"] = theme_file_result
            if not theme_file_result["exists"]:
                result["is_valid"] = False
                result["errors"].append(f"테마 파일이 존재하지 않음: {theme_file_result['path']}")
            token_file_result = self._validate_token_file(theme_name)
            result["details"]["token_file"] = token_file_result
            if not token_file_result["exists"]:
                result["is_valid"] = False
                result["errors"].append(f"토큰 파일이 존재하지 않음: {token_file_result['path']}")
            qss_files_result = self._validate_qss_files(theme_name)
            result["details"]["qss_files"] = qss_files_result
            missing_qss = [f for f in qss_files_result["files"] if not f["exists"]]
            if missing_qss:
                result["warnings"].extend([f"QSS 파일 누락: {f['path']}" for f in missing_qss])
            icon_files_result = self._validate_icon_files(theme_name)
            result["details"]["icon_files"] = icon_files_result
            missing_icons = [f for f in icon_files_result["files"] if not f["exists"]]
            if missing_icons:
                result["warnings"].extend([f"아이콘 파일 누락: {f['path']}" for f in missing_icons])
            if theme_file_result["exists"] and token_file_result["exists"]:
                css_vars_result = self._validate_css_variables(theme_name)
                result["details"]["css_variables"] = css_vars_result
                if not css_vars_result["is_consistent"]:
                    result["warnings"].extend(css_vars_result["warnings"])
            if theme_name == "high_contrast":
                contrast_result = self._validate_high_contrast_theme(theme_name)
                result["details"]["high_contrast"] = contrast_result
                if not contrast_result["meets_standards"]:
                    result["warnings"].extend(contrast_result["warnings"])
        except Exception as e:
            error_msg = f"테마 '{theme_name}' 검증 중 예외 발생: {str(e)}"
            self.logger.error(error_msg)
            result["is_valid"] = False
            result["errors"].append(error_msg)
        return result

    def _validate_theme_file(self, theme_name: str) -> dict:
        """테마 파일 존재 여부 및 유효성 확인"""
        theme_dir = Path(__file__).parent / "themes"
        theme_file = theme_dir / f"{theme_name}_theme.json"
        result = {
            "exists": theme_file.exists(),
            "path": str(theme_file),
            "is_valid_json": False,
            "has_required_fields": False,
        }
        if result["exists"]:
            try:
                with theme_file.open(encoding="utf-8") as f:
                    theme_data = json.load(f)
                result["is_valid_json"] = True
                required_fields = [
                    "name",
                    "version",
                    "colors",
                    "fonts",
                    "spacing",
                    "sizes",
                    "radii",
                ]
                result["has_required_fields"] = all(
                    field in theme_data for field in required_fields
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                result["is_valid_json"] = False
                result["error"] = str(e)
        return result

    def _validate_token_file(self, theme_name: str) -> dict:
        """토큰 파일 존재 여부 및 유효성 확인"""
        token_dir = Path(__file__).parent / "tokens"
        token_file = token_dir / f"{theme_name}_tokens.json"
        result = {
            "exists": token_file.exists(),
            "path": str(token_file),
            "is_valid_json": False,
            "has_required_sections": False,
        }
        if result["exists"]:
            try:
                with token_file.open(encoding="utf-8") as f:
                    token_data = json.load(f)
                result["is_valid_json"] = True
                required_sections = ["colors", "fonts", "spacing", "sizes", "radii", "durations"]
                result["has_required_sections"] = all(
                    section in token_data for section in required_sections
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                result["is_valid_json"] = False
                result["error"] = str(e)
        return result

    def _validate_qss_files(self, theme_name: str) -> dict:
        """QSS 템플릿 파일 존재 여부 확인"""
        qss_dir = Path(__file__).parent / "templates"
        required_qss_files = [
            "layouts/main_window.qss",
            "layouts/panel.qss",
            "components/table.qss",
            "components/controls.qss",
            "components/dialogs.qss",
            "components/scrollbars.qss",
        ]
        files_status = []
        for qss_file in required_qss_files:
            file_path = qss_dir / qss_file
            files_status.append(
                {
                    "path": str(file_path),
                    "exists": file_path.exists(),
                    "size": file_path.stat().st_size if file_path.exists() else 0,
                }
            )
        return {"files": files_status, "all_exist": all(f["exists"] for f in files_status)}

    def _validate_icon_files(self, theme_name: str) -> dict:
        """아이콘 파일 존재 여부 확인"""
        icon_dir = Path(__file__).parent / "assets" / "icons" / theme_name
        required_icons = [
            "home.svg",
            "settings.svg",
            "close.svg",
            "checkmark.svg",
            "chevron-down.svg",
            "chevron-up.svg",
            "chevron-left.svg",
            "chevron-right.svg",
            "checkbox-checked.svg",
            "checkbox-unchecked.svg",
            "radio-checked.svg",
            "radio-unchecked.svg",
        ]
        files_status = []
        for icon_file in required_icons:
            file_path = icon_dir / icon_file
            files_status.append(
                {
                    "path": str(file_path),
                    "exists": file_path.exists(),
                    "size": file_path.stat().st_size if file_path.exists() else 0,
                }
            )
        return {
            "files": files_status,
            "all_exist": all(f["exists"] for f in files_status),
            "missing_count": len([f for f in files_status if not f["exists"]]),
        }

    def _validate_css_variables(self, theme_name: str) -> dict:
        """CSS 변수 일관성 확인"""
        result = {
            "is_consistent": True,
            "warnings": [],
            "variable_count": 0,
            "missing_variables": [],
        }
        try:
            qss_dir = Path(__file__).parent / "templates"
            main_qss_file = qss_dir / "layouts" / "main_window.qss"
            if main_qss_file.exists():
                with main_qss_file.open(encoding="utf-8") as f:
                    qss_content = f.read()
                import re

                css_vars = re.findall("var\\(--([^)]+)\\)", qss_content)
                result["variable_count"] = len(set(css_vars))
                token_dir = Path(__file__).parent / "tokens"
                token_file = token_dir / f"{theme_name}_tokens.json"
                if token_file.exists():
                    with token_file.open(encoding="utf-8") as f:
                        token_data = json.load(f)
                    available_tokens = set()
                    self._extract_tokens_recursive(token_data, available_tokens)
                    used_vars = set(css_vars)
                    missing_vars = used_vars - available_tokens
                    if missing_vars:
                        result["is_consistent"] = False
                        result["missing_variables"] = list(missing_vars)
                        result["warnings"].append(
                            f"QSS에서 사용하지만 토큰에 정의되지 않은 변수: {list(missing_vars)}"
                        )
        except Exception as e:
            result["is_consistent"] = False
            result["warnings"].append(f"CSS 변수 검증 중 오류: {str(e)}")
        return result

    def _extract_tokens_recursive(self, data: dict, tokens: set[str], prefix: str = ""):
        """토큰 데이터에서 모든 변수명을 재귀적으로 추출"""
        for key, value in data.items():
            if isinstance(value, dict):
                new_prefix = f"{prefix}{key}-" if prefix else f"{key}-"
                self._extract_tokens_recursive(value, tokens, new_prefix)
            elif isinstance(value, str | int | float):
                if prefix:
                    tokens.add(f"{prefix}{key}")
                else:
                    tokens.add(key)

    def _validate_high_contrast_theme(self, theme_name: str) -> dict:
        """고대비 테마 색상 대비 검증"""
        result = {"meets_standards": True, "warnings": [], "contrast_ratios": {}}
        try:
            theme_dir = Path(__file__).parent / "themes"
            theme_file = theme_dir / f"{theme_name}_theme.json"
            if theme_file.exists():
                with theme_file.open(encoding="utf-8") as f:
                    theme_data = json.load(f)
                colors = theme_data.get("colors", {})
                key_combinations = [
                    ("background", "text"),
                    ("primary", "background"),
                    ("secondary", "background"),
                    ("accent", "background"),
                ]
                for fg_color, bg_color in key_combinations:
                    if fg_color in colors and bg_color in colors:
                        contrast_ratio = self._calculate_contrast_ratio(
                            colors[fg_color], colors[bg_color]
                        )
                        result["contrast_ratios"][f"{fg_color}-{bg_color}"] = contrast_ratio
                        if contrast_ratio < 4.5:
                            result["meets_standards"] = False
                            result["warnings"].append(
                                f"색상 대비 부족: {fg_color}-{bg_color} = {contrast_ratio:.2f}:1 (최소 4.5:1 필요)"
                            )
        except Exception as e:
            result["meets_standards"] = False
            result["warnings"].append(f"고대비 테마 검증 중 오류: {str(e)}")
        return result

    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """두 색상 간의 대비 비율 계산"""
        try:
            c1 = QColor(color1)
            c2 = QColor(color2)
            if not c1.isValid() or not c2.isValid():
                return 0.0

            def get_relative_luminance(color: QColor) -> float:
                r = color.redF()
                g = color.greenF()
                b = color.blueF()
                r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
                g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
                b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
                return 0.2126 * r + 0.7152 * g + 0.0722 * b

            l1 = get_relative_luminance(c1)
            l2 = get_relative_luminance(c2)
            lighter = max(l1, l2)
            darker = min(l1, l2)
            if darker == 0:
                return float("inf")
            return (lighter + 0.05) / (darker + 0.05)
        except Exception:
            return 0.0

    def get_validation_summary(self) -> dict:
        """검증 결과 요약 반환"""
        if not self.validation_results:
            return {"status": "검증 수행되지 않음"}
        total_themes = len(self.validation_results)
        valid_themes = sum(1 for r in self.validation_results.values() if r["is_valid"])
        invalid_themes = total_themes - valid_themes
        total_errors = sum(len(r.get("errors", [])) for r in self.validation_results.values())
        total_warnings = sum(len(r.get("warnings", [])) for r in self.validation_results.values())
        return {
            "status": "검증 완료" if invalid_themes == 0 else "검증 실패",
            "total_themes": total_themes,
            "valid_themes": valid_themes,
            "invalid_themes": invalid_themes,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "overall_valid": invalid_themes == 0,
        }

    def export_validation_report(self, output_path: str) -> bool:
        """검증 결과를 JSON 파일로 내보내기"""
        try:
            report = {
                "summary": self.get_validation_summary(),
                "detailed_results": self.validation_results,
                "timestamp": str(Path().cwd()),
                "validator_version": "1.0.0",
            }
            with Path(output_path).open("w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.logger.info(f"검증 보고서 내보내기 완료: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"검증 보고서 내보내기 실패: {str(e)}")
            return False
