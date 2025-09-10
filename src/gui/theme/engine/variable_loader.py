"""
Variable Loader for QSS Theme System

This module provides functionality to load and manage theme variables from JSON files.
It supports variable merging, validation, and caching for optimal performance.
"""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VariableLoader:
    """
    Loads and manages theme variables from JSON files.

    Supports variable merging with priority system, validation, and caching.
    """

    def __init__(self, theme_dir: str | Path):
        """
        Initialize the VariableLoader.

        Args:
            theme_dir: Path to the themes directory containing vars/ subdirectory
        """
        self.theme_dir = Path(theme_dir)
        self.vars_dir = self.theme_dir / "vars"
        self._cache: dict[str, dict[str, Any]] = {}
        self._base_vars: dict[str, Any] | None = None
        self.vars_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VariableLoader initialized with theme directory: {self.theme_dir}")

    def load_base_variables(self) -> dict[str, Any]:
        """
        Load base variables from base.json.

        Returns:
            Dictionary containing base variables
        """
        if self._base_vars is not None:
            return self._base_vars
        base_file = self.vars_dir / "base.json"
        if not base_file.exists():
            logger.warning("base.json not found, using empty base variables")
            self._base_vars = {}
            return self._base_vars
        try:
            with base_file.open(encoding="utf-8") as f:
                self._base_vars = json.load(f)
            logger.info("Base variables loaded successfully")
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load base variables: {e}")
            self._base_vars = {}
        return self._base_vars

    def load_theme_variables(self, theme_name: str) -> dict[str, Any]:
        """
        Load variables for a specific theme.

        Args:
            theme_name: Name of the theme (e.g., 'light', 'dark', 'high-contrast')

        Returns:
            Dictionary containing theme variables
        """
        if theme_name in self._cache:
            return self._cache[theme_name]
        normalized_name = self._normalize_theme_name(theme_name)
        theme_file = self.vars_dir / f"{normalized_name}.json"
        if not theme_file.exists():
            logger.warning(f"Theme file not found: {theme_file}")
            return {}
        try:
            with theme_file.open(encoding="utf-8") as f:
                theme_vars = json.load(f)
            logger.info(f"Theme variables loaded for '{theme_name}'")
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load theme variables for '{theme_name}': {e}")
            return {}
        self._cache[theme_name] = theme_vars
        return theme_vars

    def get_merged_variables(self, theme_name: str) -> dict[str, Any]:
        """
        Get merged variables for a theme (base + theme-specific).

        Args:
            theme_name: Name of the theme

        Returns:
            Dictionary containing merged variables with theme-specific overrides
        """
        base_vars = self.load_base_variables()
        theme_vars = self.load_theme_variables(theme_name)
        merged_vars = self._deep_merge_dicts(base_vars, theme_vars)
        logger.debug(
            f"Merged variables for theme '{theme_name}': {len(merged_vars)} total variables"
        )
        return merged_vars

    def _normalize_theme_name(self, theme_name: str) -> str:
        """
        Normalize theme name for file lookup.

        Args:
            theme_name: Theme name to normalize

        Returns:
            Normalized theme name
        """
        name_mapping = {
            "high-contrast": "high-contrast",
            "high_contrast": "high-contrast",
            "highcontrast": "high-contrast",
        }
        return name_mapping.get(theme_name, theme_name)

    def _deep_merge_dicts(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries, with override taking precedence.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], Mapping) and isinstance(value, Mapping):
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                result[key] = value
        return result

    def validate_variables(self, variables: dict[str, Any]) -> bool:
        """
        Validate loaded variables for basic structure and format.

        Args:
            variables: Variables to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(variables, dict):
                logger.error("Variables must be a dictionary")
                return False
            required_keys = ["colors"]
            for key in required_keys:
                if key not in variables:
                    logger.warning(f"Missing required key: {key}")
            if "colors" in variables:
                colors = variables["colors"]
                if not isinstance(colors, dict):
                    logger.error("Colors must be a dictionary")
                    return False
                for category, color_dict in colors.items():
                    if isinstance(color_dict, dict):
                        for shade, color_value in color_dict.items():
                            if not self._is_valid_hex_color(color_value):
                                logger.warning(
                                    f"Invalid hex color: {color_value} in {category}.{shade}"
                                )
            logger.info("Variables validation completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error during variables validation: {e}")
            return False

    def _is_valid_hex_color(self, color_value: str) -> bool:
        """
        Check if a string is a valid hex color.

        Args:
            color_value: Color value to validate

        Returns:
            True if valid hex color, False otherwise
        """
        if not isinstance(color_value, str):
            return False
        if color_value.startswith("#"):
            hex_part = color_value[1:]
            return len(hex_part) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in hex_part)
        return False

    def clear_cache(self) -> None:
        """Clear the variables cache."""
        self._cache.clear()
        self._base_vars = None
        logger.info("Variables cache cleared")

    def get_available_themes(self) -> list[str]:
        """
        Get list of available theme names.

        Returns:
            List of available theme names
        """
        themes = []
        if self.vars_dir.exists():
            for theme_file in self.vars_dir.glob("*.json"):
                if theme_file.name != "base.json":
                    theme_name = theme_file.stem
                    themes.append(theme_name)
        logger.info(f"Available themes: {themes}")
        return themes

    def reload_variables(self) -> None:
        """Reload all variables from files and clear cache."""
        self.clear_cache()
        logger.info("Variables reloaded from files")
