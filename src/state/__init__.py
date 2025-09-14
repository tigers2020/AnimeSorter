"""
State management package for AnimeSorter.

This package provides common state management functionality through the BaseState class,
which can be inherited by other state-managing components to promote DRY and SRP principles.
"""

from .base_state import BaseState

__all__ = ["BaseState"]
