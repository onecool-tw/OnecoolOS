"""Domain exceptions for the Onecool OS Core Engine."""


class OnecoolOSError(Exception):
    """Base exception for Onecool OS."""


class ConfigurationError(OnecoolOSError):
    """Raised when configuration is invalid."""


class DatabaseError(OnecoolOSError):
    """Raised when database initialization or migration fails."""


class PluginError(OnecoolOSError):
    """Raised when plugin loading or execution fails."""
