from enum import Enum

class MimeType(str, Enum):
    JSON = 'application/json'
    TEXT = 'text/plain'
    FOLDER = 'application/vnd.google-apps.folder'
    MINDMUP = 'application/vnd.mindmup'


class FileStatus(str, Enum):
    ACTIVE = 'active'
    TRASHED = 'trashed'
    DELETED = 'deleted'


class LogLevel(str, Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class EnvironmentType(str, Enum):
    DEVELOPMENT = 'development'
    TESTING = 'testing'
    PRODUCTION = 'production'