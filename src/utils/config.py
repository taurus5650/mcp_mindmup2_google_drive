import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator
from enum import Enum
from pydantic_settings import BaseSettings
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


class EnvironmentType(str, Enum):
    DEVELOPMENT = 'development'
    TESTING = 'testing'
    PRODUCTION = 'production'


class GoogleDriveConfig(BaseSettings):
    """Google Drive API configuration."""
    credentials_file: Optional[str] = Field(
        default=None,
        description='Google service account credentials JSON file path.'
    )

    scopes: List[str] = Field(
        default=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
        ],
        description='GOogle Drive API scopes.'
    )

    client_id: Optional[str] = Field(default=None, description='OAuth client Id.')
    client_secret: Optional[str] = Field(default=None, description='OAuth client secret".')
    redirect_uri: str = Field(
        default='http://localhost:9802/oauth/callback',
        description='OAuth redirect URI.'
    )

    max_file_size_mb: int = Field(default=10, description='Maximum file size in MB')
    supported_extensions: List[str] = Field(
        default=['.mup', '.json'],
        description='upported MindMup file extensions.'
    )

    @field_validator('credentials_file')
    def validate_credentials_file(cls, v):
        if v and not Path(v).exists():
            raise ValueError(f"Credentials file not found: {v}")
        return v


class MCPServerConfig(BaseSettings):
    host: str = Field(default='localhost', description='MCP server host.')
    port: int = Field(default=9801, description='MCP server port.')

    # TO configuration
    request_timeout_seconds: int = Field(default=30, description='Request timeout.')
    connection_timeout_seconds: int = Field(default=10, description='Connection timeout.')

    # Functionality on/off
    enable_search: bool = Field(default=True, description='Enable search functionality')
    enable_export: bool = Field(default=True, description='Enable export functionality')
    enable_cache: bool = Field(default=True, description='Enable caching')

    # Limitation
    max_concurrent_requests: int = Field(default=10, description='Max concurrent requests.')
    rate_limit_per_minute: int = Field(default=60, description='Rate limit per minute.')


class CacheConfig(BaseSettings):
    enabled: bool = Field(default=True, description='Enable caching.')
    ttl_seconds: int = Field(default=300, description='Cache TTL in seconds.')
    max_size: int = Field(default=1000, description='Max cache entries.')


class AppConfig(BaseSettings):
    app_name: str = Field(default='mindmup2-gdrive-mcp', description='Application name.')
    version: str = Field(default='0.1.0', description='Application version')
    environment: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT)

    log_level: LogLevel = Field(default=LogLevel.INFO, description='Log level')
    log_format: str = Field(
        default='json',
        description='Log format: json or text.'
    )
    log_file: Optional[str] = Field(default=None, description='Log file path')

    debug: bool = Field(default=False, description='Enable debug mode')

    google_drive: GoogleDriveConfig = Field(default_factory=GoogleDriveConfig)
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        env_nested_delimiter = '__'  # Support GOOGLE_DRIVE__CREDENTIALS_FILE format
        case_sensitive = False


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    global _config
    _config = AppConfig()
    return _config


def set_config_for_testing(**overrides) -> AppConfig:
    global _config
    test_config = AppConfig(**overrides)
    test_config.environment = EnvironmentType.TESTING
    _config = test_config
    return _config
