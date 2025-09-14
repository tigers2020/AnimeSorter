"""
BaseState class for common state management patterns.

This class provides a foundation for all state-managing components in the application,
encapsulating common state initialization and reset logic to promote DRY and SRP principles.
"""

import logging
from typing import Any

from src.core.unified_config import unified_config_manager

logger = logging.getLogger(__name__)


class BaseState:
    """
    Base class for state management in AnimeSorter.

    This class provides common state management functionality that can be inherited
    by other classes that need to manage application state. It includes methods for
    state initialization and resetting, incorporating the common state initialization
    patterns identified in Task 8.

    Attributes:
        _initialized (bool): Flag indicating whether the state has been initialized.
        _state_vars (Dict[str, Any]): Dictionary storing state variables and their values.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the BaseState instance.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self._initialized = False
        self._state_vars: dict[str, Any] = {}

        # Call the state initialization method
        self._initialize_state()
        self._initialized = True

        logger.debug(f"BaseState initialized for {self.__class__.__name__}")

    def _initialize_state(self) -> None:
        """
        Initialize the state variables using common patterns.

        This method incorporates the common state initialization logic identified
        in Task 8. It supports five main patterns for initialization:

        1. Manager/Service References: Initialize to None
        2. Data Collections: Initialize as empty list, dict, or set
        3. String Variables: Initialize with default string values
        4. Boolean Flags: Initialize with default boolean values
        5. Configuration-Based Variables: Initialize from configuration with fallback to defaults

        Subclasses should override _get_default_state_config() to provide their
        specific state configuration.

        Note:
            This method is called automatically during __init__.
        """
        state_config = self._get_default_state_config()

        # Initialize manager/service references
        self._init_manager_references(state_config.get("managers", {}))

        # Initialize data collections
        self._init_data_collections(state_config.get("collections", {}))

        # Initialize string variables
        self._init_string_variables(state_config.get("strings", {}))

        # Initialize boolean flags
        self._init_boolean_flags(state_config.get("flags", {}))

        # Initialize configuration-based variables
        self._init_config_variables(state_config.get("config", {}))

    def _get_default_state_config(self) -> dict[str, Any]:
        """
        Get the default state configuration for this component.

        Subclasses should override this method to provide their specific
        state configuration. The returned dictionary should contain:

        - 'managers': Dict mapping attribute names to manager types or None
        - 'collections': Dict mapping attribute names to collection types ('list', 'dict', 'set')
        - 'strings': Dict mapping attribute names to default string values
        - 'flags': Dict mapping attribute names to default boolean values
        - 'config': Dict mapping attribute names to configuration specifications

        Returns:
            Dictionary containing default state configuration.
        """
        return {"managers": {}, "collections": {}, "strings": {}, "flags": {}, "config": {}}

    def _init_manager_references(self, managers: dict[str, Any]) -> None:
        """
        Initialize manager and service references.

        Args:
            managers: Dictionary mapping attribute names to manager types or None.
        """
        for attr_name, _manager_type in managers.items():
            if hasattr(self, attr_name):
                continue
            setattr(self, attr_name, None)

    def _init_data_collections(self, collections: dict[str, str]) -> None:
        """
        Initialize data collection attributes.

        Args:
            collections: Dictionary mapping attribute names to collection types.
                        Supported types: 'list', 'dict', 'set'.
        """
        for attr_name, collection_type in collections.items():
            if hasattr(self, attr_name):
                continue

            if collection_type == "list":
                setattr(self, attr_name, [])
            elif collection_type == "dict":
                setattr(self, attr_name, {})
            elif collection_type == "set":
                setattr(self, attr_name, set())
            else:
                raise ValueError(f"Unsupported collection type: {collection_type}")

    def _init_string_variables(self, strings: dict[str, str]) -> None:
        """
        Initialize string variables.

        Args:
            strings: Dictionary mapping attribute names to default string values.
        """
        for attr_name, default_value in strings.items():
            if hasattr(self, attr_name):
                continue
            setattr(self, attr_name, default_value)

    def _init_boolean_flags(self, flags: dict[str, bool]) -> None:
        """
        Initialize boolean flag variables.

        Args:
            flags: Dictionary mapping attribute names to default boolean values.
        """
        for attr_name, default_value in flags.items():
            if hasattr(self, attr_name):
                continue
            setattr(self, attr_name, default_value)

    def _init_config_variables(self, config_vars: dict[str, dict[str, Any]]) -> None:
        """
        Initialize variables from configuration.

        Args:
            config_vars: Dictionary mapping attribute names to configuration
                        specifications. Each spec should contain 'section', 'key',
                        and optionally 'default'.
        """
        for attr_name, config_spec in config_vars.items():
            if hasattr(self, attr_name):
                continue

            section = config_spec.get("section")
            key = config_spec.get("key")
            default = config_spec.get("default", "")

            if section and key:
                try:
                    value = self._get_config_value(section, key, default)
                    setattr(self, attr_name, value)
                except Exception:
                    setattr(self, attr_name, default)
            else:
                setattr(self, attr_name, default)

    def _get_config_value(self, section: str, key: str, default: Any) -> Any:
        """
        Get configuration value from the unified config manager.

        Args:
            section: Configuration section name.
            key: Configuration key name.
            default: Default value to return if key is not found.

        Returns:
            Configuration value or default if not found.
        """
        return unified_config_manager.get(section, key, default)

    def reset_all_states(self) -> None:
        """
        Reset all state variables to their initial values.

        This method clears all state attributes and re-initializes them using
        the common state initialization patterns. Subclasses can override this
        method to provide additional reset logic if needed.
        """
        logger.debug(f"Resetting all states for {self.__class__.__name__}")

        # Clear existing state variables
        self._state_vars.clear()

        # Clear state attributes based on configuration
        state_config = self._get_default_state_config()

        # Clear managers
        for attr_name in state_config.get("managers", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear collections
        for attr_name in state_config.get("collections", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear strings
        for attr_name in state_config.get("strings", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear flags
        for attr_name in state_config.get("flags", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear config variables
        for attr_name in state_config.get("config", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Re-initialize state
        self._initialize_state()

        logger.debug(f"States reset completed for {self.__class__.__name__}")

    def get_state_var(self, key: str, default: Any = None) -> Any:
        """
        Get a state variable value.

        Args:
            key (str): The key of the state variable to retrieve.
            default (Any): Default value to return if key is not found.

        Returns:
            Any: The value of the state variable or the default value.
        """
        return self._state_vars.get(key, default)

    def set_state_var(self, key: str, value: Any) -> None:
        """
        Set a state variable value.

        Args:
            key (str): The key of the state variable to set.
            value (Any): The value to set for the state variable.
        """
        self._state_vars[key] = value
        logger.debug(f"State variable '{key}' set to {value} in {self.__class__.__name__}")

    def has_state_var(self, key: str) -> bool:
        """
        Check if a state variable exists.

        Args:
            key (str): The key of the state variable to check.

        Returns:
            bool: True if the state variable exists, False otherwise.
        """
        return key in self._state_vars

    def remove_state_var(self, key: str) -> bool:
        """
        Remove a state variable.

        Args:
            key (str): The key of the state variable to remove.

        Returns:
            bool: True if the variable was removed, False if it didn't exist.
        """
        if key in self._state_vars:
            del self._state_vars[key]
            logger.debug(f"State variable '{key}' removed from {self.__class__.__name__}")
            return True
        return False

    def get_all_state_vars(self) -> dict[str, Any]:
        """
        Get all state variables as a dictionary.

        Returns:
            Dict[str, Any]: A copy of all state variables.
        """
        return self._state_vars.copy()

    def is_initialized(self) -> bool:
        """
        Check if the state has been initialized.

        Returns:
            bool: True if the state has been initialized, False otherwise.
        """
        return self._initialized
