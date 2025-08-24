"""
아이콘 관리 시스템

이 모듈은 테마별 아이콘 자동 전환, SVG 아이콘 지원, 
고해상도 디스플레이 대응을 위한 IconManager를 제공합니다.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QSize, Qt, pyqtSignal, QObject, QRect
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class IconManager(QObject):
    """
    테마별 아이콘 관리자
    
    이 클래스는 다음과 같은 기능을 제공합니다:
    - 테마별 아이콘 경로 관리
    - SVG 아이콘 로딩 및 고해상도 대응
    - 다크/라이트 테마 전환 시 아이콘 자동 교체
    - QIcon.fromTheme 활용
    - 아이콘 캐싱 및 성능 최적화
    """
    
    # 시그널 정의
    icon_theme_changed = pyqtSignal(str)  # 아이콘 테마 변경 시그널
    icon_loaded = pyqtSignal(str, str)    # 아이콘 로드 완료 시그널 (아이콘명, 경로)
    icon_error = pyqtSignal(str, str)     # 아이콘 로드 오류 시그널 (아이콘명, 오류메시지)
    
    def __init__(self, app: QApplication, base_path: Optional[Union[str, Path]] = None):
        """
        IconManager 초기화
        
        Args:
            app: QApplication 인스턴스
            base_path: 아이콘 기본 경로 (기본값: src/gui/theme/assets/icons)
        """
        super().__init__()
        
        self.app = app
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent / "assets" / "icons"
        
        # 현재 테마 및 아이콘 테마
        self.current_theme = "light"
        self.current_icon_theme = "light"
        
        # 아이콘 캐시
        self._icon_cache: Dict[str, QIcon] = {}
        self._pixmap_cache: Dict[str, QPixmap] = {}
        
        # 테마별 아이콘 경로 매핑
        self.theme_paths = {
            "light": self.base_path / "light",
            "dark": self.base_path / "dark",
            "high-contrast": self.base_path / "dark"  # 고대비는 다크 테마 아이콘 사용
        }
        
        # 지원하는 아이콘 형식
        self.supported_formats = [".svg", ".png", ".ico", ".jpg", ".jpeg"]
        
        # 고해상도 디스플레이 지원
        self.device_pixel_ratio = self.app.devicePixelRatio()
        self.high_dpi_suffixes = ["@2x", "@3x", "@4x"]
        
        # 시스템 아이콘 테마 지원
        self.system_icon_themes = self._get_system_icon_themes()
        
        # SVG 최적화 설정
        self.svg_optimization = True
        self.svg_cache_enabled = True
        
        # 초기화
        self._ensure_directories()
        self._load_theme_icons()
        
        logger.info(f"IconManager initialized with base path: {self.base_path}")
        logger.info(f"Current theme: {self.current_theme}")
        logger.info(f"Device pixel ratio: {self.device_pixel_ratio}")
    
    def _ensure_directories(self):
        """필요한 디렉토리들이 존재하는지 확인하고 생성"""
        for theme_path in self.theme_paths.values():
            theme_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {theme_path}")
    
    def _get_system_icon_themes(self) -> List[str]:
        """시스템에서 사용 가능한 아이콘 테마 목록 반환"""
        system_themes = []
        
        # Linux/Unix 시스템에서 아이콘 테마 검색
        if os.name == 'posix':
            icon_dirs = [
                "/usr/share/icons",
                "/usr/local/share/icons",
                os.path.expanduser("~/.local/share/icons"),
                os.path.expanduser("~/.icons")
            ]
            
            for icon_dir in icon_dirs:
                if os.path.exists(icon_dir):
                    try:
                        themes = [d for d in os.listdir(icon_dir) 
                                if os.path.isdir(os.path.join(icon_dir, d))]
                        system_themes.extend(themes)
                    except (OSError, PermissionError):
                        continue
        
        # 중복 제거 및 정렬
        system_themes = list(set(system_themes))
        system_themes.sort()
        
        logger.debug(f"Available system icon themes: {system_themes}")
        return system_themes
    
    def _load_theme_icons(self):
        """현재 테마의 아이콘들을 미리 로드"""
        theme_path = self.theme_paths.get(self.current_theme)
        if not theme_path or not theme_path.exists():
            logger.warning(f"Theme path does not exist: {theme_path}")
            return
        
        try:
            # 테마 디렉토리의 모든 아이콘 파일 스캔
            icon_files = []
            for format_ext in self.supported_formats:
                icon_files.extend(theme_path.glob(f"*{format_ext}"))
            
            logger.info(f"Found {len(icon_files)} icons in theme: {self.current_theme}")
            
            # 아이콘 정보 로깅
            for icon_file in icon_files:
                logger.debug(f"Available icon: {icon_file.name}")
                
        except Exception as e:
            logger.error(f"Error loading theme icons: {e}")
    
    def set_theme(self, theme: str) -> bool:
        """
        테마 설정 및 아이콘 테마 변경
        
        Args:
            theme: 설정할 테마 ("light", "dark", "high-contrast")
            
        Returns:
            bool: 테마 변경 성공 여부
        """
        if theme not in self.theme_paths:
            logger.error(f"Unsupported theme: {theme}")
            return False
        
        if theme == self.current_theme:
            logger.debug(f"Theme already set to: {theme}")
            return True
        
        try:
            old_theme = self.current_theme
            self.current_theme = theme
            
            # 아이콘 테마도 함께 변경
            if theme == "high-contrast":
                self.current_icon_theme = "dark"
            else:
                self.current_icon_theme = theme
            
            # 캐시 클리어
            self._clear_cache()
            
            # 새 테마의 아이콘 로드
            self._load_theme_icons()
            
            # 시그널 발생
            self.icon_theme_changed.emit(theme)
            
            logger.info(f"Theme changed from {old_theme} to {theme}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing theme to {theme}: {e}")
            # 롤백
            self.current_theme = old_theme
            return False
    
    def get_theme(self) -> str:
        """현재 테마 반환"""
        return self.current_theme
    
    def get_icon_theme(self) -> str:
        """현재 아이콘 테마 반환"""
        return self.current_icon_theme
    
    def get_icon(self, icon_name: str, size: Optional[QSize] = None, 
                 fallback_to_system: bool = True, enable_fallback: bool = True) -> Optional[QIcon]:
        """
        아이콘 반환
        
        Args:
            icon_name: 아이콘 이름 (확장자 제외)
            size: 원하는 아이콘 크기
            fallback_to_system: 시스템 아이콘 테마 사용 여부
            
        Returns:
            QIcon: 로드된 아이콘 또는 None
        """
        # 캐시에서 먼저 검색
        cache_key = f"{icon_name}_{self.current_theme}_{size}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        try:
            # 1. 테마별 아이콘 경로에서 검색
            icon = self._load_from_theme_path(icon_name, size)
            if icon:
                self._icon_cache[cache_key] = icon
                self.icon_loaded.emit(icon_name, "theme_path")
                return icon
            
            # 2. 시스템 아이콘 테마에서 검색
            if fallback_to_system:
                icon = self._load_from_system_theme(icon_name, size)
                if icon:
                    self._icon_cache[cache_key] = icon
                    self.icon_loaded.emit(icon_name, "system_theme")
                    return icon
            
            # 3. 기본 아이콘 생성 (색상 기반)
            if enable_fallback:
                icon = self._create_fallback_icon(icon_name, size)
                if icon:
                    self._icon_cache[cache_key] = icon
                    self.icon_loaded.emit(icon_name, "fallback")
                    return icon
            
            logger.warning(f"Icon not found: {icon_name}")
            self.icon_error.emit(icon_name, "Icon not found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading icon {icon_name}: {e}")
            self.icon_error.emit(icon_name, str(e))
            return None
    
    def _load_from_theme_path(self, icon_name: str, size: Optional[QSize] = None) -> Optional[QIcon]:
        """테마별 아이콘 경로에서 아이콘 로드"""
        theme_path = self.theme_paths.get(self.current_theme)
        if not theme_path or not theme_path.exists():
            return None
        
        # 다양한 확장자로 시도
        for format_ext in self.supported_formats:
            # 기본 아이콘 파일
            icon_file = theme_path / f"{icon_name}{format_ext}"
            if icon_file.exists():
                return self._create_icon_from_file(icon_file, size)
            
            # 고해상도 디스플레이용 아이콘 파일
            if size and self.device_pixel_ratio > 1.0:
                for dpi_suffix in self.high_dpi_suffixes:
                    dpi_icon_file = theme_path / f"{icon_name}{dpi_suffix}{format_ext}"
                    if dpi_icon_file.exists():
                        return self._create_icon_from_file(dpi_icon_file, size)
        
        return None
    
    def _load_from_system_theme(self, icon_name: str, size: Optional[QSize] = None) -> Optional[QIcon]:
        """시스템 아이콘 테마에서 아이콘 로드"""
        try:
            # QIcon.fromTheme 사용
            icon = QIcon.fromTheme(icon_name)
            if not icon.isNull():
                if size:
                    # 크기 조정
                    pixmap = icon.pixmap(size)
                    if not pixmap.isNull():
                        return QIcon(pixmap)
                return icon
            
            # 시스템 아이콘 테마 디렉토리에서 직접 검색
            for theme_name in self.system_icon_themes:
                for icon_dir in ["16x16", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256"]:
                    icon_path = f"/usr/share/icons/{theme_name}/{icon_dir}/apps/{icon_name}.png"
                    if os.path.exists(icon_path):
                        return self._create_icon_from_file(Path(icon_path), size)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error loading from system theme: {e}")
            return None
    
    def _create_fallback_icon(self, icon_name: str, size: Optional[QSize] = None) -> Optional[QIcon]:
        """기본 아이콘 생성 (색상 기반)"""
        try:
            # 기본 크기 설정
            if not size:
                size = QSize(16, 16)
            
            # 아이콘 이름에서 색상 추출 시도
            color = self._extract_color_from_name(icon_name)
            if not color:
                color = "#666666"  # 기본 회색
            
            # 간단한 색상 기반 아이콘 생성
            pixmap = QPixmap(size)
            pixmap.fill(Qt.transparent)
            
            # 여기에 간단한 아이콘 그리기 로직 추가 가능
            # 현재는 투명한 픽스맵만 반환
            
            icon = QIcon(pixmap)
            return icon
            
        except Exception as e:
            logger.debug(f"Error creating fallback icon: {e}")
            return None
    
    def _extract_color_from_name(self, icon_name: str) -> Optional[str]:
        """아이콘 이름에서 색상 정보 추출"""
        # 색상 관련 키워드 매핑
        color_keywords = {
            "red": "#ff0000", "green": "#00ff00", "blue": "#0000ff",
            "yellow": "#ffff00", "purple": "#800080", "orange": "#ffa500",
            "pink": "#ffc0cb", "brown": "#a52a2a", "gray": "#808080",
            "black": "#000000", "white": "#ffffff"
        }
        
        icon_name_lower = icon_name.lower()
        for keyword, color in color_keywords.items():
            if keyword in icon_name_lower:
                return color
        
        return None
    
    def _create_icon_from_file(self, file_path: Path, size: Optional[QSize] = None) -> Optional[QIcon]:
        """파일에서 아이콘 생성"""
        try:
            if not file_path.exists():
                return None
            
            # SVG 파일인 경우
            if file_path.suffix.lower() == ".svg":
                icon = QIcon(str(file_path))
                if size:
                    # SVG는 크기 조정이 자동으로 됨
                    pixmap = icon.pixmap(size)
                    return QIcon(pixmap)
                return icon
            
            # 래스터 파일인 경우
            else:
                pixmap = QPixmap(str(file_path))
                if pixmap.isNull():
                    return None
                
                if size:
                    # 크기 조정
                    pixmap = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                return QIcon(pixmap)
                
        except Exception as e:
            logger.error(f"Error creating icon from file {file_path}: {e}")
            return None
    
    def get_icon_path(self, icon_name: str) -> Optional[Path]:
        """아이콘 파일 경로 반환"""
        theme_path = self.theme_paths.get(self.current_theme)
        if not theme_path:
            return None
        
        for format_ext in self.supported_formats:
            icon_file = theme_path / f"{icon_name}{format_ext}"
            if icon_file.exists():
                return icon_file
        
        return None
    
    def list_available_icons(self) -> List[str]:
        """사용 가능한 아이콘 목록 반환"""
        icons = []
        theme_path = self.theme_paths.get(self.current_theme)
        
        if theme_path and theme_path.exists():
            for format_ext in self.supported_formats:
                for icon_file in theme_path.glob(f"*{format_ext}"):
                    # 확장자 제거
                    icon_name = icon_file.stem
                    # 고해상도 접미사 제거
                    for dpi_suffix in self.high_dpi_suffixes:
                        if icon_name.endswith(dpi_suffix):
                            icon_name = icon_name[:-len(dpi_suffix)]
                            break
                    
                    if icon_name not in icons:
                        icons.append(icon_name)
        
        return sorted(icons)
    
    def add_icon(self, icon_name: str, icon_path: Union[str, Path], 
                 theme: Optional[str] = None) -> bool:
        """
        새 아이콘 추가
        
        Args:
            icon_name: 아이콘 이름
            icon_path: 아이콘 파일 경로
            theme: 대상 테마 (None이면 현재 테마)
            
        Returns:
            bool: 추가 성공 여부
        """
        if theme is None:
            theme = self.current_theme
        
        if theme not in self.theme_paths:
            logger.error(f"Invalid theme: {theme}")
            return False
        
        try:
            source_path = Path(icon_path)
            if not source_path.exists():
                logger.error(f"Source icon file does not exist: {source_path}")
                return False
            
            # 대상 경로
            target_dir = self.theme_paths[theme]
            target_path = target_dir / f"{icon_name}{source_path.suffix}"
            
            # 파일 복사
            import shutil
            shutil.copy2(source_path, target_path)
            
            # 캐시 클리어
            self._clear_cache()
            
            logger.info(f"Icon added: {icon_name} to theme {theme}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding icon {icon_name}: {e}")
            return False
    
    def remove_icon(self, icon_name: str, theme: Optional[str] = None) -> bool:
        """
        아이콘 제거
        
        Args:
            icon_name: 제거할 아이콘 이름
            theme: 대상 테마 (None이면 현재 테마)
            
        Returns:
            bool: 제거 성공 여부
        """
        if theme is None:
            theme = self.current_theme
        
        if theme not in self.theme_paths:
            logger.error(f"Invalid theme: {theme}")
            return False
        
        try:
            theme_path = self.theme_paths[theme]
            removed = False
            
            # 모든 확장자와 고해상도 접미사에 대해 검색
            for format_ext in self.supported_formats:
                # 기본 아이콘
                icon_file = theme_path / f"{icon_name}{format_ext}"
                if icon_file.exists():
                    icon_file.unlink()
                    removed = True
                
                # 고해상도 아이콘
                for dpi_suffix in self.high_dpi_suffixes:
                    dpi_icon_file = theme_path / f"{icon_name}{dpi_suffix}{format_ext}"
                    if dpi_icon_file.exists():
                        dpi_icon_file.unlink()
                        removed = True
            
            if removed:
                # 캐시 클리어
                self._clear_cache()
                logger.info(f"Icon removed: {icon_name} from theme {theme}")
                return True
            else:
                logger.warning(f"Icon not found: {icon_name} in theme {theme}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing icon {icon_name}: {e}")
            return False
    
    def _clear_cache(self):
        """아이콘 캐시 클리어"""
        self._icon_cache.clear()
        self._pixmap_cache.clear()
        logger.debug("Icon cache cleared")
    
    def clear_cache(self):
        """캐시 클리어 (공개 메서드)"""
        self._clear_cache()
    
    def get_cache_info(self) -> Dict[str, int]:
        """캐시 정보 반환"""
        return {
            "icon_cache_size": len(self._icon_cache),
            "pixmap_cache_size": len(self._pixmap_cache)
        }
    
    def cleanup(self):
        """리소스 정리"""
        self._clear_cache()
        logger.info("IconManager cleanup completed")
    
    # 추가된 고급 기능들
    
    def get_icon_quality_info(self, icon_name: str) -> Dict[str, any]:
        """
        아이콘 품질 정보 반환
        
        Args:
            icon_name: 아이콘 이름
            
        Returns:
            Dict: 아이콘 품질 정보
        """
        try:
            icon_path = self.get_icon_path(icon_name)
            if not icon_path:
                return {"error": "Icon not found"}
            
            info = {
                "name": icon_name,
                "path": str(icon_path),
                "format": icon_path.suffix.lower(),
                "file_size": icon_path.stat().st_size,
                "theme": self.current_theme
            }
            
            # SVG 파일인 경우 추가 정보
            if icon_path.suffix.lower() == ".svg":
                info["type"] = "vector"
                info["scalable"] = True
                info["optimized"] = self._is_svg_optimized(icon_path)
            else:
                info["type"] = "raster"
                info["scalable"] = False
                
                # 픽스맵 정보
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    info["original_size"] = {"width": pixmap.width(), "height": pixmap.height()}
                    info["dpi_aware"] = self._is_dpi_aware(icon_path)
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting icon quality info: {e}")
            return {"error": str(e)}
    
    def _is_svg_optimized(self, svg_path: Path) -> bool:
        """SVG 파일이 최적화되었는지 확인"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 최적화 지표들
            optimization_indicators = [
                '<!-- Generated by' not in content,  # 자동 생성된 주석 없음
                'viewBox' in content,  # viewBox 속성 있음
                'xmlns=' in content,   # 네임스페이스 선언
                len(content) < 10000   # 적절한 파일 크기
            ]
            
            return all(optimization_indicators)
            
        except Exception as e:
            logger.debug(f"Error checking SVG optimization: {e}")
            return False
    
    def _is_dpi_aware(self, icon_path: Path) -> bool:
        """아이콘이 고해상도 디스플레이를 인식하는지 확인"""
        icon_name = icon_path.stem
        theme_path = self.theme_paths.get(self.current_theme)
        
        if not theme_path:
            return False
        
        # 고해상도 접미사가 있는지 확인
        for dpi_suffix in self.high_dpi_suffixes:
            for format_ext in self.supported_formats:
                dpi_icon = theme_path / f"{icon_name}{dpi_suffix}{format_ext}"
                if dpi_icon.exists():
                    return True
        
        return False
    
    def create_icon_set(self, base_name: str, sizes: List[QSize]) -> Dict[str, QIcon]:
        """
        여러 크기의 아이콘으로 구성된 아이콘 세트 생성
        
        Args:
            base_name: 기본 아이콘 이름
            sizes: 아이콘 크기 리스트
            
        Returns:
            Dict: 크기별 아이콘 매핑
        """
        icon_set = {}
        
        for size in sizes:
            icon = self.get_icon(base_name, size)
            if icon:
                # QSize를 문자열로 변환하여 딕셔너리 키로 사용
                size_key = f"{size.width()}x{size.height()}"
                icon_set[size_key] = icon
        
        return icon_set
    
    def optimize_svg_icons(self, theme: Optional[str] = None) -> Dict[str, bool]:
        """
        SVG 아이콘 최적화 (실제 구현은 외부 도구 필요)
        
        Args:
            theme: 대상 테마 (None이면 현재 테마)
            
        Returns:
            Dict: 최적화 결과
        """
        if theme is None:
            theme = self.current_theme
        
        if theme not in self.theme_paths:
            logger.error(f"Invalid theme: {theme}")
            return {}
        
        theme_path = self.theme_paths[theme]
        results = {}
        
        try:
            # SVG 파일들 찾기
            svg_files = list(theme_path.glob("*.svg"))
            
            for svg_file in svg_files:
                icon_name = svg_file.stem
                # 고해상도 접미사 제거
                for dpi_suffix in self.high_dpi_suffixes:
                    if icon_name.endswith(dpi_suffix):
                        icon_name = icon_name[:-len(dpi_suffix)]
                        break
                
                # 최적화 상태 확인
                is_optimized = self._is_svg_optimized(svg_file)
                results[icon_name] = is_optimized
                
                if not is_optimized:
                    logger.info(f"SVG icon {icon_name} could be optimized")
            
            logger.info(f"SVG optimization check completed for theme {theme}")
            return results
            
        except Exception as e:
            logger.error(f"Error optimizing SVG icons: {e}")
            return {}
    
    def get_high_dpi_icons(self, icon_name: str) -> Dict[str, Path]:
        """
        고해상도 아이콘 파일들 반환
        
        Args:
            icon_name: 아이콘 이름
            
        Returns:
            Dict: 해상도별 파일 경로
        """
        theme_path = self.theme_paths.get(self.current_theme)
        if not theme_path:
            return {}
        
        high_dpi_files = {}
        
        for format_ext in self.supported_formats:
            # 기본 아이콘
            base_icon = theme_path / f"{icon_name}{format_ext}"
            if base_icon.exists():
                high_dpi_files["1x"] = base_icon
            
            # 고해상도 아이콘들
            for dpi_suffix in self.high_dpi_suffixes:
                dpi_icon = theme_path / f"{icon_name}{dpi_suffix}{format_ext}"
                if dpi_icon.exists():
                    # 접미사에서 배율 추출
                    scale = dpi_suffix.replace("@", "").replace("x", "")
                    high_dpi_files[f"{scale}x"] = dpi_icon
        
        return high_dpi_files
    
    def validate_icon_integrity(self, icon_name: str) -> Dict[str, any]:
        """
        아이콘 무결성 검증
        
        Args:
            icon_name: 아이콘 이름
            
        Returns:
            Dict: 검증 결과
        """
        try:
            icon_path = self.get_icon_path(icon_name)
            if not icon_path:
                return {"valid": False, "error": "Icon not found"}
            
            # 파일 존재 확인
            if not icon_path.exists():
                return {"valid": False, "error": "File does not exist"}
            
            # 파일 크기 확인
            file_size = icon_path.stat().st_size
            if file_size == 0:
                return {"valid": False, "error": "File is empty"}
            
            # 아이콘 로드 테스트
            icon = self.get_icon(icon_name)
            if not icon or icon.isNull():
                return {"valid": False, "error": "Failed to load icon"}
            
            # 고해상도 지원 확인
            high_dpi_icons = self.get_high_dpi_icons(icon_name)
            
            result = {
                "valid": True,
                "path": str(icon_path),
                "file_size": file_size,
                "format": icon_path.suffix.lower(),
                "high_dpi_support": len(high_dpi_icons) > 1,
                "high_dpi_versions": list(high_dpi_icons.keys())
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating icon integrity: {e}")
            return {"valid": False, "error": str(e)}
    
    def get_icon_statistics(self) -> Dict[str, any]:
        """
        아이콘 통계 정보 반환
        
        Returns:
            Dict: 통계 정보
        """
        try:
            stats = {
                "total_themes": len(self.theme_paths),
                "current_theme": self.current_theme,
                "device_pixel_ratio": self.device_pixel_ratio,
                "cache_info": self.get_cache_info(),
                "theme_stats": {}
            }
            
            for theme_name, theme_path in self.theme_paths.items():
                if theme_path.exists():
                    theme_icons = list(theme_path.glob("*.*"))
                    svg_count = len(list(theme_path.glob("*.svg")))
                    png_count = len(list(theme_path.glob("*.png")))
                    high_dpi_count = sum(1 for icon in theme_icons 
                                       if any(suffix in icon.name for suffix in self.high_dpi_suffixes))
                    
                    stats["theme_stats"][theme_name] = {
                        "total_icons": len(theme_icons),
                        "svg_icons": svg_count,
                        "png_icons": png_count,
                        "high_dpi_icons": high_dpi_count
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting icon statistics: {e}")
            return {"error": str(e)}
