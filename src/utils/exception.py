
class MindMupMCPError(Exception):
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ConfigurationError(MindMupMCPError):

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code='CONFIG_ERROR',
            details=details
        )


class GoogleDriveError(MindMupMCPError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code='GDRIVE_ERROR',
            details=details
        )


class MindMapParseError(MindMupMCPError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code='MINDMAP_PARSE_ERROR',
            details=details
        )


class MCPServerError(MindMupMCPError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code='MCP_SERVER_ERROR',
            details=details
        )


class AuthenticationError(MindMupMCPError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code='AUTH_ERROR',
            details=details
        )
