"""
테마 템플릿 패키지

이 패키지는 QSS(Qt Style Sheets) 템플릿들을 정의하고 관리합니다.
"""

from pathlib import Path

# 템플릿 디렉토리 경로
TEMPLATES_DIR = Path(__file__).parent

# 기본 템플릿 디렉토리들
COMPONENTS_DIR = TEMPLATES_DIR / "components"
LAYOUTS_DIR = TEMPLATES_DIR / "layouts"
UTILITIES_DIR = TEMPLATES_DIR / "utilities"

# 컴포넌트별 템플릿 파일들
BUTTON_TEMPLATE = COMPONENTS_DIR / "button.qss"
LINEEDIT_TEMPLATE = COMPONENTS_DIR / "lineedit.qss"
TABLE_TEMPLATE = COMPONENTS_DIR / "table.qss"
COMBOBOX_TEMPLATE = COMPONENTS_DIR / "combobox.qss"
CHECKBOX_TEMPLATE = COMPONENTS_DIR / "checkbox.qss"
RADIOBUTTON_TEMPLATE = COMPONENTS_DIR / "radiobutton.qss"
SLIDER_TEMPLATE = COMPONENTS_DIR / "slider.qss"
PROGRESSBAR_TEMPLATE = COMPONENTS_DIR / "progressbar.qss"
SCROLLBAR_TEMPLATE = COMPONENTS_DIR / "scrollbar.qss"
MENU_TEMPLATE = COMPONENTS_DIR / "menu.qss"
TOOLBAR_TEMPLATE = COMPONENTS_DIR / "toolbar.qss"
STATUSBAR_TEMPLATE = COMPONENTS_DIR / "statusbar.qss"
DIALOG_TEMPLATE = COMPONENTS_DIR / "dialog.qss"
TABWIDGET_TEMPLATE = COMPONENTS_DIR / "tabwidget.qss"
TREEVIEW_TEMPLATE = COMPONENTS_DIR / "treeview.qss"
LISTVIEW_TEMPLATE = COMPONENTS_DIR / "listview.qss"
TEXTEDIT_TEMPLATE = COMPONENTS_DIR / "textedit.qss"

# 레이아웃 템플릿 파일들
MAIN_WINDOW_TEMPLATE = LAYOUTS_DIR / "main_window.qss"
SIDEBAR_TEMPLATE = LAYOUTS_DIR / "sidebar.qss"
HEADER_TEMPLATE = LAYOUTS_DIR / "header.qss"
FOOTER_TEMPLATE = LAYOUTS_DIR / "footer.qss"
PANEL_TEMPLATE = LAYOUTS_DIR / "panel.qss"
CARD_TEMPLATE = LAYOUTS_DIR / "card.qss"

# 유틸리티 템플릿 파일들
VARIABLES_TEMPLATE = UTILITIES_DIR / "variables.qss"
MIXINS_TEMPLATE = UTILITIES_DIR / "mixins.qss"
ANIMATIONS_TEMPLATE = UTILITIES_DIR / "animations.qss"

# 사용 가능한 템플릿 파일들
AVAILABLE_TEMPLATES = [
    # 컴포넌트 템플릿
    "components/button.qss",
    "components/lineedit.qss",
    "components/table.qss",
    "components/combobox.qss",
    "components/checkbox.qss",
    "components/radiobutton.qss",
    "components/slider.qss",
    "components/progressbar.qss",
    "components/scrollbar.qss",
    "components/menu.qss",
    "components/toolbar.qss",
    "components/statusbar.qss",
    "components/dialog.qss",
    "components/tabwidget.qss",
    "components/treeview.qss",
    "components/listview.qss",
    "components/textedit.qss",
    # 레이아웃 템플릿
    "layouts/main_window.qss",
    "layouts/sidebar.qss",
    "layouts/header.qss",
    "layouts/footer.qss",
    "layouts/panel.qss",
    "layouts/card.qss",
    # 유틸리티 템플릿
    "utilities/variables.qss",
    "utilities/mixins.qss",
    "utilities/animations.qss",
]

__all__ = [
    "TEMPLATES_DIR",
    "COMPONENTS_DIR",
    "LAYOUTS_DIR",
    "UTILITIES_DIR",
    "BUTTON_TEMPLATE",
    "LINEEDIT_TEMPLATE",
    "TABLE_TEMPLATE",
    "COMBOBOX_TEMPLATE",
    "CHECKBOX_TEMPLATE",
    "RADIOBUTTON_TEMPLATE",
    "SLIDER_TEMPLATE",
    "PROGRESSBAR_TEMPLATE",
    "SCROLLBAR_TEMPLATE",
    "MENU_TEMPLATE",
    "TOOLBAR_TEMPLATE",
    "STATUSBAR_TEMPLATE",
    "DIALOG_TEMPLATE",
    "TABWIDGET_TEMPLATE",
    "TREEVIEW_TEMPLATE",
    "LISTVIEW_TEMPLATE",
    "TEXTEDIT_TEMPLATE",
    "MAIN_WINDOW_TEMPLATE",
    "SIDEBAR_TEMPLATE",
    "HEADER_TEMPLATE",
    "FOOTER_TEMPLATE",
    "PANEL_TEMPLATE",
    "CARD_TEMPLATE",
    "VARIABLES_TEMPLATE",
    "MIXINS_TEMPLATE",
    "ANIMATIONS_TEMPLATE",
    "AVAILABLE_TEMPLATES",
]
