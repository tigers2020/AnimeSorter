"""
국제화(i18n) 관리 시스템 (Phase 10.2)
한국어/영어 다국어 지원을 위한 번역 시스템
"""

import logging

logger = logging.getLogger(__name__)
from pathlib import Path

from PyQt5.QtCore import QLocale, QObject, QTranslator, pyqtSignal
from PyQt5.QtWidgets import QApplication


class I18nManager(QObject):
    """국제화 관리자 - 한국어/영어 다국어 지원"""

    language_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_language = "ko"
        self.translator = QTranslator()
        self.app_translator = QTranslator()
        self.supported_languages = {"ko": "한국어", "en": "English"}
        self.translations = {"ko": {}, "en": {}}
        self._initialize_translations()

    def _initialize_translations(self):
        """번역 데이터 초기화 (Phase 10.2)"""
        self.translations["ko"] = {
            "main_window_title": "AnimeSorter",
            "main_window_description": "애니메이션 파일 정리 도구",
            "scan_files": "파일 스캔",
            "scan_files_desc": "선택된 폴더의 애니메이션 파일들을 스캔합니다",
            "preview_organization": "미리보기",
            "preview_organization_desc": "정리 작업의 미리보기를 표시합니다",
            "organize_files": "파일 정리",
            "organize_files_desc": "스캔된 파일들을 정리된 구조로 이동합니다",
            "settings": "설정",
            "settings_desc": "애플리케이션 설정을 엽니다",
            "quick_actions": "빠른 작업",
            "statistics": "통계",
            "source_folder": "소스 폴더",
            "source_folder_select": "소스 폴더 선택",
            "source_folder_desc": "스캔할 애니메이션 파일들이 있는 폴더를 선택합니다",
            "destination_folder": "대상 폴더",
            "destination_folder_select": "대상 폴더 선택",
            "destination_folder_desc": "정리된 파일들을 저장할 폴더를 선택합니다",
            "scan_start": "스캔 시작",
            "scan_start_desc": "선택된 폴더의 파일 스캔을 시작합니다",
            "preview_show": "미리보기",
            "preview_show_desc": "정리 작업의 미리보기를 표시합니다",
            "organize_execute": "정리 실행",
            "organize_execute_desc": "파일 정리 작업을 실행합니다",
            "tab_all": "전체",
            "tab_unmatched": "미매칭",
            "tab_conflict": "충돌",
            "tab_duplicate": "중복",
            "tab_completed": "완료",
            "poster": "포스터",
            "title": "제목",
            "final_path": "최종 이동 경로",
            "season": "시즌",
            "episode_count": "에피소드 수",
            "resolution": "해상도",
            "status": "상태",
            "filename": "파일명",
            "original_path": "원본 경로",
            "file_size": "파일 크기",
            "detected_info": "감지된 정보",
            "status_ready": "준비",
            "status_scanning": "스캔 중...",
            "status_completed": "완료",
            "status_error": "오류",
            "status_organizing": "정리 중...",
            "total_files": "전체 파일",
            "total_groups": "전체 그룹",
            "matched_groups": "매칭된 그룹",
            "unmatched_groups": "미매칭 그룹",
            "conflict_groups": "충돌 그룹",
            "duplicate_groups": "중복 그룹",
            "completed_groups": "완료된 그룹",
            "ok": "확인",
            "cancel": "취소",
            "apply": "적용",
            "close": "닫기",
            "save": "저장",
            "load": "불러오기",
            "reset": "초기화",
            "help": "도움말",
            "about": "정보",
            "file_menu": "파일",
            "edit_menu": "편집",
            "view_menu": "보기",
            "tools_menu": "도구",
            "help_menu": "도움말",
            "language_menu": "언어",
            "theme_auto": "자동",
            "theme_light": "라이트",
            "theme_dark": "다크",
            "theme_high_contrast": "고대비",
            "accessibility_enabled": "접근성 모드 활성화",
            "high_contrast_mode": "고대비 모드",
            "screen_reader_support": "스크린 리더 지원",
            "keyboard_navigation": "키보드 네비게이션",
            "error_file_not_found": "파일을 찾을 수 없습니다",
            "error_permission_denied": "권한이 거부되었습니다",
            "error_invalid_format": "잘못된 파일 형식입니다",
            "error_network_error": "네트워크 오류가 발생했습니다",
            "success_scan_completed": "스캔이 완료되었습니다",
            "success_organization_completed": "파일 정리가 완료되었습니다",
            "success_settings_saved": "설정이 저장되었습니다",
        }
        self.translations["en"] = {
            "main_window_title": "AnimeSorter",
            "main_window_description": "Anime File Organization Tool",
            "scan_files": "Scan Files",
            "scan_files_desc": "Scan anime files in the selected folder",
            "preview_organization": "Preview",
            "preview_organization_desc": "Show preview of organization task",
            "organize_files": "Organize Files",
            "organize_files_desc": "Move scanned files to organized structure",
            "settings": "Settings",
            "settings_desc": "Open application settings",
            "quick_actions": "Quick Actions",
            "statistics": "Statistics",
            "source_folder": "Source Folder",
            "source_folder_select": "Select Source Folder",
            "source_folder_desc": "Select folder containing anime files to scan",
            "destination_folder": "Destination Folder",
            "destination_folder_select": "Select Destination Folder",
            "destination_folder_desc": "Select folder to save organized files",
            "scan_start": "Start Scan",
            "scan_start_desc": "Start scanning files in selected folder",
            "preview_show": "Preview",
            "preview_show_desc": "Show preview of organization task",
            "organize_execute": "Execute Organization",
            "organize_execute_desc": "Execute file organization task",
            "tab_all": "All",
            "tab_unmatched": "Unmatched",
            "tab_conflict": "Conflict",
            "tab_duplicate": "Duplicate",
            "tab_completed": "Completed",
            "poster": "Poster",
            "title": "Title",
            "final_path": "Final Path",
            "season": "Season",
            "episode_count": "Episodes",
            "resolution": "Resolution",
            "status": "Status",
            "filename": "Filename",
            "original_path": "Original Path",
            "file_size": "File Size",
            "detected_info": "Detected Info",
            "status_ready": "Ready",
            "status_scanning": "Scanning...",
            "status_completed": "Completed",
            "status_error": "Error",
            "status_organizing": "Organizing...",
            "total_files": "Total Files",
            "total_groups": "Total Groups",
            "matched_groups": "Matched Groups",
            "unmatched_groups": "Unmatched Groups",
            "conflict_groups": "Conflict Groups",
            "duplicate_groups": "Duplicate Groups",
            "completed_groups": "Completed Groups",
            "ok": "OK",
            "cancel": "Cancel",
            "apply": "Apply",
            "close": "Close",
            "save": "Save",
            "load": "Load",
            "reset": "Reset",
            "help": "Help",
            "about": "About",
            "file_menu": "File",
            "edit_menu": "Edit",
            "view_menu": "View",
            "tools_menu": "Tools",
            "help_menu": "Help",
            "language_menu": "Language",
            "theme_auto": "Auto",
            "theme_light": "Light",
            "theme_dark": "Dark",
            "theme_high_contrast": "High Contrast",
            "accessibility_enabled": "Accessibility Mode Enabled",
            "high_contrast_mode": "High Contrast Mode",
            "screen_reader_support": "Screen Reader Support",
            "keyboard_navigation": "Keyboard Navigation",
            "error_file_not_found": "File not found",
            "error_permission_denied": "Permission denied",
            "error_invalid_format": "Invalid file format",
            "error_network_error": "Network error occurred",
            "success_scan_completed": "Scan completed",
            "success_organization_completed": "File organization completed",
            "success_settings_saved": "Settings saved",
        }

    def get_supported_languages(self) -> dict[str, str]:
        """지원 언어 목록 반환"""
        return self.supported_languages.copy()

    def get_current_language(self) -> str:
        """현재 언어 반환"""
        return self.current_language

    def set_language(self, language_code: str) -> bool:
        """언어 설정"""
        if language_code not in self.supported_languages:
            logger.info("⚠️ 지원되지 않는 언어: %s", language_code)
            return False
        if language_code == self.current_language:
            return True
        old_language = self.current_language
        self.current_language = language_code
        success = self._apply_language_change()
        if success:
            logger.info("🌍 언어가 %s에서 %s로 변경되었습니다", old_language, language_code)
            self.language_changed.emit(language_code)
            return True
        self.current_language = old_language
        logger.info("⚠️ 언어 변경 실패, %s로 롤백", old_language)
        return False

    def _apply_language_change(self) -> bool:
        """언어 변경 적용"""
        try:
            app = QApplication.instance()
            if not app:
                return False
            app.removeTranslator(self.translator)
            app.removeTranslator(self.app_translator)
            self.translator = QTranslator()
            if self.current_language == "ko":
                locale = QLocale(QLocale.Korean, QLocale.SouthKorea)
            else:
                locale = QLocale(QLocale.English, QLocale.UnitedStates)
            QLocale.setDefault(locale)
            app.installTranslator(self.translator)
            return True
        except Exception as e:
            logger.info("⚠️ 언어 변경 적용 실패: %s", e)
            return False

    def tr(self, key: str, fallback: str | None = None) -> str:
        """번역 함수 - 키에 해당하는 번역된 텍스트 반환"""
        try:
            translation = self.translations.get(self.current_language, {}).get(key)
            if translation:
                return translation
            if self.current_language != "ko":
                ko_translation = self.translations.get("ko", {}).get(key)
                if ko_translation:
                    return ko_translation
            return fallback if fallback else key
        except Exception as e:
            logger.info("⚠️ 번역 오류 (키: %s): %s", key, e)
            return fallback if fallback else key

    def get_language_name(self, language_code: str) -> str:
        """언어 코드에 해당하는 언어명 반환"""
        return self.supported_languages.get(language_code, language_code)

    def detect_system_language(self) -> str:
        """시스템 언어 감지"""
        try:
            system_locale = QLocale.system()
            language = system_locale.language()
            if language == QLocale.Korean:
                return "ko"
            return "en"
        except Exception as e:
            logger.info("⚠️ 시스템 언어 감지 실패: %s", e)
            return "ko"

    def initialize_with_system_language(self):
        """시스템 언어로 초기화"""
        system_lang = self.detect_system_language()
        self.set_language(system_lang)
        logger.info("🌍 시스템 언어로 초기화: %s", system_lang)

    def get_translation_coverage(self) -> dict[str, float]:
        """각 언어의 번역 완성도 반환"""
        coverage = {}
        if not self.translations:
            return coverage
        base_keys = set(self.translations.get("ko", {}).keys())
        total_keys = len(base_keys)
        for lang_code, translations in self.translations.items():
            if total_keys > 0:
                translated_keys = len(set(translations.keys()) & base_keys)
                coverage[lang_code] = translated_keys / total_keys * 100
            else:
                coverage[lang_code] = 0.0
        return coverage

    def add_custom_translation(self, language_code: str, key: str, value: str):
        """사용자 정의 번역 추가"""
        if language_code not in self.translations:
            self.translations[language_code] = {}
        self.translations[language_code][key] = value
        logger.info("🌍 사용자 정의 번역 추가: %s.%s = %s", language_code, key, value)

    def get_all_translation_keys(self) -> list:
        """모든 번역 키 목록 반환"""
        all_keys = set()
        for translations in self.translations.values():
            all_keys.update(translations.keys())
        return sorted(all_keys)

    def export_translations(self, file_path: str) -> bool:
        """번역 데이터를 파일로 내보내기"""
        try:
            import json

            export_data = {
                "version": "1.0",
                "current_language": self.current_language,
                "supported_languages": self.supported_languages,
                "translations": self.translations,
            }
            with Path(file_path).open("w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info("✅ 번역 데이터 내보내기 완료: %s", file_path)
            return True
        except Exception as e:
            logger.info("⚠️ 번역 데이터 내보내기 실패: %s", e)
            return False

    def import_translations(self, file_path: str) -> bool:
        """파일에서 번역 데이터 가져오기"""
        try:
            import json

            with Path(file_path).open(encoding="utf-8") as f:
                import_data = json.load(f)
            if "translations" not in import_data:
                logger.info("⚠️ 잘못된 번역 파일 형식")
                return False
            for lang_code, translations in import_data["translations"].items():
                if lang_code not in self.translations:
                    self.translations[lang_code] = {}
                self.translations[lang_code].update(translations)
            if "supported_languages" in import_data:
                self.supported_languages.update(import_data["supported_languages"])
            logger.info("✅ 번역 데이터 가져오기 완료: %s", file_path)
            return True
        except Exception as e:
            logger.info("⚠️ 번역 데이터 가져오기 실패: %s", e)
            return False
