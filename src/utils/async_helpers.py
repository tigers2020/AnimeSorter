"""
비동기 프로그래밍을 위한 유틸리티 함수들

동기/비동기 함수를 구분 없이 호출할 수 있는 헬퍼 함수들을 제공합니다.
"""

import inspect
import asyncio
from typing import Any, Callable, TypeVar, Awaitable

T = TypeVar('T')


async def maybe_await(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    동기·비동기 함수 구분 없이 호출해 결과를 돌려준다.
    
    Args:
        func: 호출할 함수 (동기 또는 비동기)
        *args: 함수 인자
        **kwargs: 함수 키워드 인자
        
    Returns:
        함수의 반환값 (비동기 함수인 경우 await된 결과)
        
    Examples:
        # 동기 함수
        result = await maybe_await(sync_function, arg1, arg2)
        
        # 비동기 함수
        result = await maybe_await(async_function, arg1, arg2)
    """
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


def is_async_function(func: Callable) -> bool:
    """
    함수가 비동기 함수인지 확인한다.
    
    Args:
        func: 확인할 함수
        
    Returns:
        bool: 비동기 함수이면 True, 동기 함수이면 False
    """
    return asyncio.iscoroutinefunction(func)


def is_awaitable(obj: Any) -> bool:
    """
    객체가 await 가능한지 확인한다.
    
    Args:
        obj: 확인할 객체
        
    Returns:
        bool: await 가능하면 True, 아니면 False
    """
    return inspect.isawaitable(obj) 