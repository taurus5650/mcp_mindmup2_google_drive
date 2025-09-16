class LogLevel(str, Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class EnvironmentType(str, Enum):
    DEVELOPMENT = 'development'
    TESTING = 'testing'
    PRODUCTION = 'production'