"""
테마 토큰 시스템 데이터 모델

이 모듈은 Pydantic을 사용하여 테마 토큰의 구조를 정의하고
데이터 검증을 제공합니다.
"""

import re
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThemeType(str, Enum):
    """테마 타입 열거형"""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


class OptimizationLevel(str, Enum):
    """최적화 레벨 열거형"""

    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"


class AccessibilityLevel(str, Enum):
    """접근성 레벨 열거형"""

    NONE = "none"
    BASIC = "basic"
    ENHANCED = "enhanced"
    FULL = "full"


class ColorToken(BaseModel):
    """색상 토큰 모델"""

    value: str = Field(..., description="색상 값 (HEX, RGB, HSL 등)")
    description: Optional[str] = Field(None, description="색상 설명")
    category: Optional[str] = Field(None, description="색상 카테고리")

    @field_validator("value")
    @classmethod
    def validate_color_value(cls, v):
        """색상 값 유효성 검사"""
        if not v:
            raise ValueError("색상 값은 비어있을 수 없습니다")

        # HEX 색상 검사
        if v.startswith("#"):
            if not re.match(r"^#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?$", v):
                raise ValueError("유효하지 않은 HEX 색상 형식입니다")

        # RGB/RGBA 색상 검사
        elif v.startswith("rgb"):
            if not re.match(r"^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+\s*)?\)$", v):
                raise ValueError("유효하지 않은 RGB/RGBA 색상 형식입니다")

        # HSL/HSLA 색상 검사
        elif v.startswith("hsl"):
            if not re.match(r"^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(,\s*[\d.]+\s*)?\)$", v):
                raise ValueError("유효하지 않은 HSL/HSLA 색상 형식입니다")

        # 명명된 색상 검사
        elif v.lower() in ["transparent", "currentcolor", "inherit", "initial", "unset"]:
            pass

        # CSS 키워드 색상 (간단한 검사)
        elif v.lower() in ["red", "green", "blue", "black", "white", "gray", "grey"]:
            pass

        else:
            raise ValueError("지원하지 않는 색상 형식입니다")

        return v


class FontToken(BaseModel):
    """폰트 토큰 모델"""

    family: str = Field(..., description="폰트 패밀리")
    size: Optional[Union[int, float]] = Field(None, description="폰트 크기 (px)")
    weight: Optional[str] = Field(None, description="폰트 굵기")
    style: Optional[str] = Field(None, description="폰트 스타일")
    line_height: Optional[Union[int, float]] = Field(None, description="줄 높이")
    description: Optional[str] = Field(None, description="폰트 설명")

    @field_validator("size", "line_height")
    @classmethod
    def validate_positive_number(cls, v):
        """양수 숫자 검사"""
        if v is not None and v <= 0:
            raise ValueError("값은 0보다 커야 합니다")
        return v

    @field_validator("weight")
    @classmethod
    def validate_font_weight(cls, v):
        """폰트 굵기 검사"""
        if v is not None:
            valid_weights = [
                "normal",
                "bold",
                "bolder",
                "lighter",
                "100",
                "200",
                "300",
                "400",
                "500",
                "600",
                "700",
                "800",
                "900",
            ]
            if v not in valid_weights:
                raise ValueError(f"유효하지 않은 폰트 굵기입니다: {v}")
        return v

    @field_validator("style")
    @classmethod
    def validate_font_style(cls, v):
        """폰트 스타일 검사"""
        if v is not None:
            valid_styles = ["normal", "italic", "oblique"]
            if v not in valid_styles:
                raise ValueError(f"유효하지 않은 폰트 스타일입니다: {v}")
        return v


class SpacingToken(BaseModel):
    """간격 토큰 모델"""

    value: Union[int, float] = Field(..., description="간격 값 (px)")
    description: Optional[str] = Field(None, description="간격 설명")
    category: Optional[str] = Field(None, description="간격 카테고리")

    @field_validator("value")
    @classmethod
    def validate_positive_number(cls, v):
        """양수 숫자 검사"""
        if v is not None and v <= 0:
            raise ValueError("값은 0보다 커야 합니다")
        return v


class BorderToken(BaseModel):
    """테두리 토큰 모델"""

    width: Optional[Union[int, float]] = Field(None, description="테두리 너비 (px)")
    radius: Optional[Union[int, float]] = Field(None, description="테두리 반지름 (px)")
    style: Optional[str] = Field(None, description="테두리 스타일")
    description: Optional[str] = Field(None, description="테두리 설명")

    @field_validator("width", "radius")
    @classmethod
    def validate_positive_number(cls, v):
        """양수 숫자 검사"""
        if v is not None and v < 0:
            raise ValueError("값은 0 이상이어야 합니다")
        return v

    @field_validator("style")
    @classmethod
    def validate_border_style(cls, v):
        """테두리 스타일 검사"""
        if v is not None:
            valid_styles = [
                "none",
                "hidden",
                "dotted",
                "dashed",
                "solid",
                "double",
                "groove",
                "ridge",
                "inset",
                "outset",
            ]
            if v not in valid_styles:
                raise ValueError(f"유효하지 않은 테두리 스타일입니다: {v}")
        return v


class ShadowToken(BaseModel):
    """그림자 토큰 모델"""

    offset_x: Union[int, float] = Field(..., description="X축 오프셋 (px)")
    offset_y: Union[int, float] = Field(..., description="Y축 오프셋 (px)")
    blur: Optional[Union[int, float]] = Field(0, description="블러 반지름 (px)")
    spread: Optional[Union[int, float]] = Field(0, description="스프레드 반지름 (px)")
    color: str = Field(..., description="그림자 색상")
    description: Optional[str] = Field(None, description="그림자 설명")

    @field_validator("blur", "spread")
    @classmethod
    def validate_non_negative_number(cls, v):
        """음수가 아닌 숫자 검사"""
        if v is not None and v < 0:
            raise ValueError("값은 0 이상이어야 합니다")
        return v


class TransitionToken(BaseModel):
    """전환 토큰 모델"""

    duration: Union[int, float] = Field(..., description="전환 지속 시간 (ms)")
    delay: Optional[Union[int, float]] = Field(0, description="전환 지연 시간 (ms)")
    easing: Optional[str] = Field("ease", description="전환 이징 함수")
    description: Optional[str] = Field(None, description="전환 설명")

    @field_validator("duration", "delay")
    @classmethod
    def validate_non_negative_number(cls, v):
        """음수가 아닌 숫자 검사"""
        if v is not None and v < 0:
            raise ValueError("값은 0 이상이어야 합니다")
        return v

    @field_validator("easing")
    @classmethod
    def validate_easing_function(cls, v):
        """이징 함수 검사"""
        if v is not None:
            valid_easings = ["ease", "linear", "ease-in", "ease-out", "ease-in-out", "cubic-bezier"]
            if v not in valid_easings and not v.startswith("cubic-bezier("):
                raise ValueError(f"유효하지 않은 이징 함수입니다: {v}")
        return v


class ZIndexToken(BaseModel):
    """Z-인덱스 토큰 모델"""

    value: int = Field(..., description="Z-인덱스 값")
    description: Optional[str] = Field(None, description="Z-인덱스 설명")
    category: Optional[str] = Field(None, description="Z-인덱스 카테고리")


class BreakpointToken(BaseModel):
    """브레이크포인트 토큰 모델"""

    value: Union[int, float] = Field(..., description="브레이크포인트 값 (px)")
    description: Optional[str] = Field(None, description="브레이크포인트 설명")
    category: Optional[str] = Field(None, description="브레이크포인트 카테고리")


class ColorPalette(BaseModel):
    """색상 팔레트 모델"""

    primary: ColorToken = Field(..., description="주요 색상")
    secondary: ColorToken = Field(..., description="보조 색상")
    background: ColorToken = Field(..., description="배경 색상")
    text: ColorToken = Field(..., description="텍스트 색상")
    surface: ColorToken = Field(..., description="표면 색상")
    border: ColorToken = Field(..., description="테두리 색상")


class FontSystem(BaseModel):
    """폰트 시스템 모델"""

    primary: FontToken = Field(..., description="주요 폰트")
    sizes: dict[str, Union[int, float]] = Field(..., description="폰트 크기들")


class SpacingSystem(BaseModel):
    """간격 시스템 모델"""

    xs: SpacingToken = Field(..., description="매우 작은 간격")
    sm: SpacingToken = Field(..., description="작은 간격")
    md: SpacingToken = Field(..., description="중간 간격")
    lg: SpacingToken = Field(..., description="큰 간격")
    xl: SpacingToken = Field(..., description="매우 큰 간격")


class BorderSystem(BaseModel):
    """테두리 시스템 모델"""

    widths: dict[str, BorderToken] = Field(..., description="테두리 너비들")
    radiuses: dict[str, BorderToken] = Field(..., description="테두리 반지름들")


class ShadowSystem(BaseModel):
    """그림자 시스템 모델"""

    small: Optional[ShadowToken] = Field(None, description="작은 그림자")
    medium: Optional[ShadowToken] = Field(None, description="중간 그림자")
    large: Optional[ShadowToken] = Field(None, description="큰 그림자")
    custom: Optional[dict[str, ShadowToken]] = Field(None, description="사용자 정의 그림자들")


class ThemeTokens(BaseModel):
    """테마 토큰 모델"""

    name: str = Field(..., description="테마 이름")
    version: str = Field(..., description="테마 버전")
    description: Optional[str] = Field(None, description="테마 설명")

    # 디자인 토큰들
    colors: ColorPalette = Field(..., description="색상 팔레트")
    fonts: FontSystem = Field(..., description="폰트 시스템")
    spacing: SpacingSystem = Field(..., description="간격 시스템")
    borders: BorderSystem = Field(..., description="테두리 시스템")
    shadows: Optional[ShadowSystem] = Field(None, description="그림자 시스템")
    transitions: Optional[dict[str, TransitionToken]] = Field(None, description="전환 설정")
    z_index: Optional[dict[str, ZIndexToken]] = Field(None, description="Z-인덱스 시스템")
    breakpoints: Optional[dict[str, BreakpointToken]] = Field(None, description="브레이크포인트")

    # 변수들
    variables: Optional[dict[str, Any]] = Field(None, description="사용자 정의 변수들")

    # 사용자 정의 토큰들
    custom: Optional[dict[str, Any]] = Field(None, description="사용자 정의 토큰들")

    model_config = ConfigDict(
        extra="allow",
        json_encoders={
            ColorToken: lambda v: v.value,
            FontToken: lambda v: v.model_dump(exclude_none=True),
            SpacingToken: lambda v: v.value,
            BorderToken: lambda v: v.model_dump(exclude_none=True),
            ShadowToken: lambda v: v.model_dump(exclude_none=True),
            TransitionToken: lambda v: v.model_dump(exclude_none=True),
            ZIndexToken: lambda v: v.value,
            BreakpointToken: lambda v: v.value,
            ThemeType: lambda v: v.value,
            OptimizationLevel: lambda v: v.value,
            AccessibilityLevel: lambda v: v.value,
        },
    )


class TokenReference(BaseModel):
    """토큰 참조 모델"""

    path: str = Field(..., description="토큰 경로")
    value: Any = Field(..., description="토큰 값")
    description: Optional[str] = Field(None, description="토큰 설명")
    category: Optional[str] = Field(None, description="토큰 카테고리")
    metadata: Optional[dict[str, Any]] = Field(None, description="추가 메타데이터")


class TokenCollection(BaseModel):
    """토큰 컬렉션 모델"""

    name: str = Field(..., description="컬렉션 이름")
    description: Optional[str] = Field(None, description="컬렉션 설명")
    tokens: dict[str, TokenReference] = Field(..., description="토큰 참조들")
    version: str = Field("1.0.0", description="컬렉션 버전")

    model_config = ConfigDict(extra="allow")


# 유틸리티 함수들
def create_color_token(value: str, **kwargs) -> ColorToken:
    """색상 토큰 생성 헬퍼"""
    return ColorToken(value=value, **kwargs)


def create_font_token(family: str, **kwargs) -> FontToken:
    """폰트 토큰 생성 헬퍼"""
    return FontToken(family=family, **kwargs)


def create_spacing_token(value: Union[int, float], **kwargs) -> SpacingToken:
    """간격 토큰 생성 헬퍼"""
    return SpacingToken(value=value, **kwargs)


def create_border_token(**kwargs) -> BorderToken:
    """테두리 토큰 생성 헬퍼"""
    return BorderToken(**kwargs)


def create_shadow_token(
    offset_x: Union[int, float], offset_y: Union[int, float], color: str, **kwargs
) -> ShadowToken:
    """그림자 토큰 생성 헬퍼"""
    return ShadowToken(offset_x=offset_x, offset_y=offset_y, color=color, **kwargs)


def create_transition_token(duration: Union[int, float], easing: str, **kwargs) -> TransitionToken:
    """전환 토큰 생성 헬퍼"""
    return TransitionToken(duration=duration, easing=easing, **kwargs)


def create_z_index_token(value: int, **kwargs) -> ZIndexToken:
    """Z-인덱스 토큰 생성 헬퍼"""
    return ZIndexToken(value=value, **kwargs)


def create_breakpoint_token(value: Union[int, float], **kwargs) -> BreakpointToken:
    """브레이크포인트 토큰 생성 헬퍼"""
    return BreakpointToken(value=value, **kwargs)
