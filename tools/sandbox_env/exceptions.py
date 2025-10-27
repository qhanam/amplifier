"""Custom exception types for sandbox operations."""


class SandboxError(Exception):
    """Base exception for sandbox operations."""


class SandboxExistsError(SandboxError):
    """Sandbox with this name already exists."""


class SandboxNotFoundError(SandboxError):
    """Sandbox not found."""


class InvalidProjectPathError(SandboxError):
    """Project path is invalid or inaccessible."""


class GitOperationError(SandboxError):
    """Git operation failed."""


class StateFileError(SandboxError):
    """State file operation failed."""
