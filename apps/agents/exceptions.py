"""
Custom exceptions for Agents app.
"""


class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass


class AgentExecutionError(AgentError):
    """Exception raised when agent execution fails."""
    pass


class AgentValidationError(AgentError):
    """Exception raised when agent validation fails."""
    pass


class AgentCodeError(AgentError):
    """Exception raised for errors in agent code."""
    pass


class AgentSecurityError(AgentError):
    """Exception raised for security violations in agent code."""
    pass


class AgentParameterError(AgentError):
    """Exception raised for invalid parameters."""
    pass


class AgentScheduleError(AgentError):
    """Exception raised for schedule configuration errors."""
    pass


class AgentPermissionError(AgentError):
    """Exception raised for permission violations."""
    pass


class AgentNotFoundError(AgentError):
    """Exception raised when agent is not found."""
    pass


class AgentExecutionTimeoutError(AgentExecutionError):
    """Exception raised when execution exceeds timeout."""
    pass


class AgentMemoryLimitError(AgentExecutionError):
    """Exception raised when execution exceeds memory limit."""
    pass


class AgentDependencyError(AgentError):
    """Exception raised when required dependencies are missing."""
    pass
