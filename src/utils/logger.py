import inspect
import json
import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Request ID context variable for async support
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class SimpleLogger:
    def __init__(self, name: str = 'mcp_mindmup2_google_drive'):
        self.name = name
        self._logger = logging.getLogger(name)
        self._is_configured = False

    def configure(
            self, level: str = 'INFO', console: bool = True, file_path: Optional[str] = None, json_format: bool = False):
        if self._is_configured:
            return

        # Set logging level
        self._logger.setLevel(getattr(logging, level.upper()))

        # Clear existing handlers
        self._logger.handlers.clear()

        # Console settings
        if console:
            if json_format:
                console_handler.setFormatter(JsonFormatter())
            else:
                console_handler.setFormatter(SimpleFormatter())
            self._logger.addHandler(console_handler)

        # Log file settings
        if file_path:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setFormatter(JsonFormatter())
            self._logger.addHandler(file_handler)

        self._is_configured = True

    def set_request_id(self, request_id: str = None) -> str:
        """Set request ID for current context. If not provided, generates a new one."""
        if request_id is None:
            request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
        return request_id

    def get_request_id(self) -> Optional[str]:
        """Get current request ID from context."""
        return request_id_context.get()

    def clear_request_id(self):
        """Clear request ID from context."""
        request_id_context.set(None)

    def _log_with_context(self, level: str, message: str, extra: Dict[str, Any] = None):
        """Internal method to log with request ID context."""
        self._ensure_configured()

        # Add request ID to extra data
        log_extra = extra or {}
        request_id = self.get_request_id()
        if request_id:
            log_extra['request_id'] = request_id

        # Update logger name to current caller's filename
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back.f_back  # Go up 2 levels to get actual caller
            if caller_frame:
                filename = caller_frame.f_globals.get('__file__')
                if filename:
                    caller_name = os.path.splitext(os.path.basename(filename))[0]
                    self._logger.name = caller_name
        finally:
            del frame

    def debug(self, message: str, extra: Dict[str, Any] = None):
        """Log debug message."""
        self._log_with_context('debug', message, extra)

    def info(self, message: str, extra: Dict[str, Any] = None):
        """Log info message."""
        self._log_with_context('info', message, extra)

    def warning(self, message: str, extra: Dict[str, Any] = None):
        """Log warning message."""
        self._log_with_context('warning', message, extra)

    def error(self, message: str, extra: Dict[str, Any] = None):
        """Log error message."""
        self._log_with_context('error', message, extra)

    def exception(self, message: str, extra: Dict[str, Any] = None):
        """Log exception with stack trace."""
        self._ensure_configured()
        log_extra = extra or {}
        request_id = self.get_request_id()
        if request_id:
            log_extra['request_id'] = request_id

    def _ensure_configured(self):
        """Ensure logger is configured before use."""
        if not self._is_configured:
            self.configure()


class SimpleFormatter(logging.Formatter):
    def format(self, record):
        # Add request ID to the record if available, or generate one
        request_id = getattr(record, 'request_id', None)
        if not request_id:
            # Get from context or generate new one
            request_id = request_id_context.get()
            if not request_id:
                request_id = str(uuid.uuid4())
                request_id_context.set(request_id)

        request_part = f" | {request_id}"

        # Format: timestamp | level | logger | request_id | message
        formatted = f"{datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')} | {record.levelname} | {record.name}{request_part} | {record.getMessage()}"

        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add request ID if available
        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_data['request_id'] = request_id

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def _get_caller_filename():
    """Get the filename of the module that imported this logger."""
    frame = inspect.currentframe()
    try:
        # Go up the call stack to find the caller
        caller_frame = frame.f_back.f_back
        if caller_frame:
            filename = caller_frame.f_globals.get('__file__')
            if filename:
                return os.path.splitext(os.path.basename(filename))[0]
    finally:
        del frame
    return 'unknown'

# Auto-detecting logger instance


class AutoLogger(SimpleLogger):
    def __init__(self):
        caller_name = _get_caller_filename()
        super().__init__(caller_name)


logger = AutoLogger()


def get_logger(name: str = None) -> SimpleLogger:
    if name:
        return SimpleLogger(name)
    return SimpleLogger(_get_caller_filename())
