"""
Base classes for common GUI patterns and state management.

This module provides base classes that encapsulate common patterns
found across the AnimeSorter GUI components, particularly for
state initialization and management.
"""

from abc import ABC, abstractmethod
from typing import Any

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget

from src.core.unified_config import unified_config_manager


class BaseStateInitializer(ABC):
    """
    Abstract base class for components that need state initialization.

    This class provides a common interface and helper methods for
    initializing component state in a consistent manner.
    """

    @abstractmethod
    def initialize_state(self) -> None:
        """Initialize the component state. Must be implemented by subclasses."""

    def __init__(self, obj: Any = None):
        """Initialize the base state initializer."""
        self._obj = obj  # The object whose state is being managed
        self._state_initialized = False

    def _initialize_state(self, state_config: dict[str, Any] | None = None) -> None:
        """
        Initialize component state using the provided configuration.

        Args:
            state_config: Optional dictionary containing state initialization
                         configuration. If None, uses default initialization.
        """
        if state_config is None:
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

        self._state_initialized = True

    def _get_default_state_config(self) -> dict[str, Any]:
        """
        Get the default state configuration for this component.

        Subclasses should override this method to provide their
        specific default configuration.

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
        if self._obj is None:
            return
        for attr_name, _manager_type in managers.items():
            if hasattr(self._obj, attr_name):
                continue
            setattr(self._obj, attr_name, None)

    def _init_data_collections(self, collections: dict[str, str]) -> None:
        """
        Initialize data collection attributes.

        Args:
            collections: Dictionary mapping attribute names to collection types.
                        Supported types: 'list', 'dict', 'set'.
        """
        if self._obj is None:
            return
        for attr_name, collection_type in collections.items():
            if hasattr(self._obj, attr_name):
                continue

            if collection_type == "list":
                setattr(self._obj, attr_name, [])
            elif collection_type == "dict":
                setattr(self._obj, attr_name, {})
            elif collection_type == "set":
                setattr(self._obj, attr_name, set())
            else:
                raise ValueError(f"Unsupported collection type: {collection_type}")

    def _init_string_variables(self, strings: dict[str, str]) -> None:
        """
        Initialize string variables.

        Args:
            strings: Dictionary mapping attribute names to default string values.
        """
        if self._obj is None:
            return
        for attr_name, default_value in strings.items():
            if hasattr(self._obj, attr_name):
                continue
            setattr(self._obj, attr_name, default_value)

    def _init_boolean_flags(self, flags: dict[str, bool]) -> None:
        """
        Initialize boolean flag variables.

        Args:
            flags: Dictionary mapping attribute names to default boolean values.
        """
        if self._obj is None:
            return
        for attr_name, default_value in flags.items():
            if hasattr(self._obj, attr_name):
                continue
            setattr(self._obj, attr_name, default_value)

    def _init_config_variables(self, config_vars: dict[str, dict[str, Any]]) -> None:
        """
        Initialize variables from configuration.

        Args:
            config_vars: Dictionary mapping attribute names to configuration
                        specifications. Each spec should contain 'section', 'key',
                        and optionally 'default'.
        """
        if self._obj is None:
            return
        for attr_name, config_spec in config_vars.items():
            if hasattr(self._obj, attr_name):
                continue

            section = config_spec.get("section")
            key = config_spec.get("key")
            default = config_spec.get("default", "")

            if section and key:
                try:
                    # Use a method that can be easily mocked in tests
                    value = self._get_config_value(section, key, default)
                    setattr(self._obj, attr_name, value)
                except Exception:
                    setattr(self._obj, attr_name, default)
            else:
                setattr(self._obj, attr_name, default)

    def _get_config_value(self, section: str, key: str, default: Any) -> Any:
        """Get configuration value. Can be overridden for testing."""
        return unified_config_manager.get(section, key, default)

    def reset_state(self) -> None:
        """
        Reset the component state to its initial values.

        This method should be overridden by subclasses to provide
        specific reset logic.
        """
        # Clear existing state attributes
        if self._obj:
            config = self._get_default_state_config()

            # Clear managers
            for attr_name in config.get("managers", {}):
                if hasattr(self._obj, attr_name):
                    delattr(self._obj, attr_name)

            # Clear collections
            for attr_name in config.get("collections", {}):
                if hasattr(self._obj, attr_name):
                    delattr(self._obj, attr_name)

            # Clear strings
            for attr_name in config.get("strings", {}):
                if hasattr(self._obj, attr_name):
                    delattr(self._obj, attr_name)

            # Clear flags
            for attr_name in config.get("flags", {}):
                if hasattr(self._obj, attr_name):
                    delattr(self._obj, attr_name)

            # Clear config variables
            for attr_name in config.get("config", {}):
                if hasattr(self._obj, attr_name):
                    delattr(self._obj, attr_name)

        self._state_initialized = False
        self._initialize_state()

    @property
    def is_state_initialized(self) -> bool:
        """Check if the state has been initialized."""
        return self._state_initialized


class BaseWidget(QWidget):
    """
    Base widget class that combines QWidget functionality with state management.

    This class provides a foundation for custom widgets that need both
    Qt widget functionality and consistent state initialization.
    """

    def __init__(self, parent: QWidget | None = None, state_config: dict[str, Any] | None = None):
        """
        Initialize the base widget.

        Args:
            parent: Parent widget.
            state_config: Optional state configuration dictionary.
        """
        super().__init__(parent)
        self._state_initializer = BaseStateInitializer(self)
        self._initialize_state(state_config)

    def _initialize_state(self, state_config: dict[str, Any] | None = None) -> None:
        """Initialize component state using the provided configuration."""
        self._state_initializer._initialize_state(state_config)

    def _get_default_state_config(self) -> dict[str, Any]:
        """Get the default state configuration for this component."""
        return {"managers": {}, "collections": {}, "strings": {}, "flags": {}, "config": {}}

    def reset_state(self) -> None:
        """Reset the component state to its initial values."""
        self._state_initializer.reset_state()

    @property
    def is_state_initialized(self) -> bool:
        """Check if the state has been initialized."""
        return self._state_initializer.is_state_initialized


class BaseObject(QObject):
    """
    Base object class that combines QObject functionality with state management.

    This class provides a foundation for non-widget objects that need both
    Qt object functionality and consistent state initialization.
    """

    def __init__(self, parent: QObject | None = None, state_config: dict[str, Any] | None = None):
        """
        Initialize the base object.

        Args:
            parent: Parent object.
            state_config: Optional state configuration dictionary.
        """
        super().__init__(parent)
        self._state_initializer = BaseStateInitializer(self)
        self._initialize_state(state_config)

    def _initialize_state(self, state_config: dict[str, Any] | None = None) -> None:
        """Initialize component state using the provided configuration."""
        self._state_initializer._initialize_state(state_config)

    def _get_default_state_config(self) -> dict[str, Any]:
        """Get the default state configuration for this component."""
        return {"managers": {}, "collections": {}, "strings": {}, "flags": {}, "config": {}}

    def reset_state(self) -> None:
        """Reset the component state to its initial values."""
        self._state_initializer.reset_state()

    @property
    def is_state_initialized(self) -> bool:
        """Check if the state has been initialized."""
        return self._state_initializer.is_state_initialized


class StateInitializationMixin:
    """
    Mixin class that provides state initialization functionality.

    This mixin can be added to any class to provide state initialization
    capabilities without requiring inheritance from BaseStateInitializer.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        self._state_initializer = BaseStateInitializer(self)
        # Auto-initialize state with default config
        self.initialize_state()

    def _get_default_state_config(self) -> dict[str, Any]:
        """Get the default state configuration for this component."""
        return {"managers": {}, "collections": {}, "strings": {}, "flags": {}, "config": {}}

    def initialize_state(self, state_config: dict[str, Any] | None = None) -> None:
        """
        Initialize component state using the provided configuration.

        Args:
            state_config: Optional dictionary containing state initialization
                         configuration. If None, uses default initialization.
        """
        if state_config is None:
            state_config = self._get_default_state_config()

        # Initialize config variables directly in the mixin
        if "config" in state_config:
            self._init_config_variables(state_config["config"])

        # Use the state initializer for other types
        other_config = {k: v for k, v in state_config.items() if k != "config"}
        if other_config:
            self._state_initializer._initialize_state(other_config)

    def _get_config_value(self, section: str, key: str, default: Any) -> Any:
        """Get configuration value. Can be overridden for testing."""
        return unified_config_manager.get(section, key, default)

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
                    # Use a method that can be easily mocked in tests
                    value = self._get_config_value(section, key, default)
                    setattr(self, attr_name, value)
                except Exception:
                    # If config fails, use default value
                    setattr(self, attr_name, default)
            else:
                setattr(self, attr_name, default)

    def reset_state(self) -> None:
        """Reset the component state to its initial values."""
        # Clear existing state attributes
        config = self._get_default_state_config()

        # Clear managers
        for attr_name in config.get("managers", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear collections
        for attr_name in config.get("collections", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear strings
        for attr_name in config.get("strings", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear flags
        for attr_name in config.get("flags", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Clear config variables
        for attr_name in config.get("config", {}):
            if hasattr(self, attr_name):
                delattr(self, attr_name)

        # Reinitialize state
        self.initialize_state()

    @property
    def is_state_initialized(self) -> bool:
        """Check if the state has been initialized."""
        return self._state_initializer.is_state_initialized
