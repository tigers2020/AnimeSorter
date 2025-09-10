"""
Template Engine for QSS Theme System

This module provides functionality to process QSS templates with variable substitution.
It supports both ${variable} and var(--variable) syntax for maximum compatibility.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Processes QSS templates with variable substitution.

    Supports multiple variable syntaxes and provides error handling and logging.
    """

    def __init__(self):
        """Initialize the TemplateEngine."""
        self.variable_pattern = re.compile("\\$\\{([^}]+)\\}")
        self.css_var_pattern = re.compile("var\\(--([^)]+)\\)")
        self.nested_var_pattern = re.compile("\\$\\{([^}]+)\\}")
        logger.info("TemplateEngine initialized")

    def compile_qss(self, qss_content: str, variables: dict[str, Any]) -> str:
        """
        Compile QSS content by substituting variables.

        Args:
            qss_content: Raw QSS content with variable placeholders
            variables: Dictionary of variables to substitute

        Returns:
            Compiled QSS content with variables resolved
        """
        if not qss_content:
            logger.warning("Empty QSS content provided")
            return ""
        if not variables:
            logger.warning("No variables provided for substitution")
            return qss_content
        try:
            compiled_qss = self._substitute_variables(qss_content, variables)
            compiled_qss = self._substitute_css_variables(compiled_qss, variables)
            logger.info("QSS compilation completed successfully")
            return compiled_qss
        except Exception as e:
            logger.error(f"Error during QSS compilation: {e}")
            return qss_content

    def _substitute_variables(self, qss_content: str, variables: dict[str, Any]) -> str:
        """
        Substitute ${variable} placeholders with actual values.

        Args:
            qss_content: QSS content with ${variable} placeholders
            variables: Variables dictionary

        Returns:
            QSS content with variables substituted
        """

        def replace_variable(match):
            var_path = match.group(1)
            try:
                value = self._get_nested_value(variables, var_path)
                if value is not None:
                    return str(value)
                logger.warning(f"Variable not found: {var_path}")
                return match.group(0)
            except Exception as e:
                logger.error(f"Error resolving variable {var_path}: {e}")
                return match.group(0)

        return self.variable_pattern.sub(replace_variable, qss_content)

    def _substitute_css_variables(self, qss_content: str, variables: dict[str, Any]) -> str:
        """
        Substitute var(--variable) placeholders with actual values.

        Args:
            qss_content: QSS content with var(--variable) placeholders
            variables: Variables dictionary

        Returns:
            QSS content with CSS variables substituted
        """

        def replace_css_variable(match):
            var_name = match.group(1)
            try:
                value = self._find_css_variable_value(variables, var_name)
                if value is not None:
                    return str(value)
                logger.warning(f"CSS variable not found: {var_name}")
                return match.group(0)
            except Exception as e:
                logger.error(f"Error resolving CSS variable {var_name}: {e}")
                return match.group(0)

        return self.css_var_pattern.sub(replace_css_variable, qss_content)

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """
        Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search in
            path: Dot-separated path (e.g., "colors.primary.500")

        Returns:
            Value at the specified path or None if not found
        """
        try:
            keys = path.split(".")
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except Exception as e:
            logger.error(f"Error accessing nested path {path}: {e}")
            return None

    def _find_css_variable_value(self, variables: dict[str, Any], var_name: str) -> Any:
        """
        Find CSS variable value by converting CSS variable name to our structure.

        Args:
            variables: Variables dictionary
            var_name: CSS variable name (e.g., "primary-color")

        Returns:
            Value for the CSS variable or None if not found
        """
        try:
            if var_name == "primary-color":
                return self._get_nested_value(variables, "colors.primary.500")
            if var_name == "primary-hover-color":
                return self._get_nested_value(variables, "colors.primary.600")
            if var_name == "text-color":
                return self._get_nested_value(variables, "colors.text.primary")
            if var_name == "text-muted-color":
                return self._get_nested_value(variables, "colors.text.muted")
            if var_name == "background-color":
                return self._get_nested_value(variables, "colors.background.default")
            if var_name == "border-color":
                return self._get_nested_value(variables, "colors.border.default")
            if var_name == "focus-color":
                return self._get_nested_value(variables, "colors.border.focus")
            dot_path = var_name.replace("-", ".")
            return self._get_nested_value(variables, dot_path)
        except Exception as e:
            logger.error(f"Error finding CSS variable {var_name}: {e}")
            return None

    def validate_template(self, qss_content: str) -> tuple[bool, list[str]]:
        """
        Validate QSS template for syntax and variable usage.

        Args:
            qss_content: QSS content to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        try:
            open_braces = qss_content.count("${")
            close_braces = qss_content.count("}")
            if open_braces != close_braces:
                issues.append(f"Unmatched braces: {open_braces} open, {close_braces} close")
            empty_vars = re.findall("\\$\\{\\s*\\}", qss_content)
            if empty_vars:
                issues.append(f"Empty variable placeholders found: {len(empty_vars)}")
            malformed_css_vars = re.findall("var\\([^)]*$", qss_content)
            if malformed_css_vars:
                issues.append(f"Malformed CSS variable declarations: {len(malformed_css_vars)}")
            is_valid = len(issues) == 0
            if is_valid:
                logger.info("QSS template validation passed")
            else:
                logger.warning(f"QSS template validation failed: {issues}")
            return is_valid, issues
        except Exception as e:
            logger.error(f"Error during template validation: {e}")
            issues.append(f"Validation error: {e}")
            return False, issues

    def get_used_variables(self, qss_content: str) -> list[str]:
        """
        Extract all variable names used in QSS content.

        Args:
            qss_content: QSS content to analyze

        Returns:
            List of variable names used
        """
        variables = set()
        try:
            var_matches = self.variable_pattern.findall(qss_content)
            variables.update(var_matches)
            css_var_matches = self.css_var_pattern.findall(qss_content)
            variables.update(css_var_matches)
            logger.debug(f"Found {len(variables)} variables in QSS content")
            return list(variables)
        except Exception as e:
            logger.error(f"Error extracting variables: {e}")
            return []

    def create_variable_mapping(
        self, qss_content: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a mapping of used variables to their values.

        Args:
            qss_content: QSS content to analyze
            variables: Variables dictionary

        Returns:
            Dictionary mapping used variables to their values
        """
        used_vars = self.get_used_variables(qss_content)
        mapping: dict[str, Any] = {}
        for var_name in used_vars:
            if var_name.startswith("--"):
                value = self._find_css_variable_value(variables, var_name[2:])
            else:
                value = self._get_nested_value(variables, var_name)
            if value is not None:
                mapping[var_name] = value
            else:
                logger.warning(f"Variable {var_name} not found in variables dictionary")
        logger.debug(f"Created variable mapping with {len(mapping)} variables")
        return mapping
