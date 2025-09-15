import os
import pytest
from pathlib import Path
from src.utils.config import (
    AppConfig, GoogleDriveConfig, MCPServerConfig,
    get_config, reload_config, set_config_for_testing,
    EnvironmentType, LogLevel
)
from src.utils.exception import ConfigurationError


class TestAppConfig:

    def test_default_config(self):
        config = AppConfig()

        assert config.app_name == 'mindmup2-gdrive-mcp'
        assert config.version == '0.1.0'
        assert config.environment == EnvironmentType.DEVELOPMENT
        assert config.log_level == LogLevel.INFO
        assert config.debug is False

    def test_environment_override(self, monkeypatch):
        monkeypatch.setenv('DEBUG', 'true')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        monkeypatch.setenv('ENVIRONMENT', 'testing')

        config = AppConfig()

        assert config.debug is True
        assert config.log_level == LogLevel.DEBUG
        assert config.environment == EnvironmentType.TESTING

    def test_nested_config_override(self, monkeypatch):
        monkeypatch.setenv('MCP_SERVER__PORT', '9090')
        monkeypatch.setenv('GOOGLE_DRIVE__MAX_FILE_SIZE_MB', '20')

        config = AppConfig()

        assert config.mcp_server.port == 9090
        assert config.google_drive.max_file_size_mb == 20


class TestGoogleDriveConfig:
    def test_default_config(self):
        config = GoogleDriveConfig()

        assert config.credentials_file is None
        assert "https://www.googleapis.com/auth/drive" in config.scopes
        assert config.max_file_size_mb == 10
        assert ".mup" in config.supported_extensions

    def test_credentials_file_validation(self, tmp_path):
        with pytest.raises(ValueError):
            GoogleDriveConfig(credentials_file="nonexistent.json")

        credentials_file = tmp_path / "credentials.json"
        credentials_file.write_text("{}")

        config = GoogleDriveConfig(credentials_file=str(credentials_file))
        assert config.credentials_file == str(credentials_file)


class TestMCPServerConfig:

    def test_default_config(self):
        config = MCPServerConfig()

        assert config.host == 'localhost'
        assert config.port == 9801
        assert config.request_timeout_seconds == 30
        assert config.enable_search is True
        assert config.max_concurrent_requests == 10


class TestConfigHelpers:
    def test_get_config_singleton(self):
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reload_config(self):
        config1 = get_config()
        config2 = reload_config()

        assert config1 is not config2

    def test_set_config_for_testing(self):
        test_config = set_config_for_testing(
            debug=True,
            log_level=LogLevel.DEBUG
        )

        assert test_config.debug is True
        assert test_config.log_level == LogLevel.DEBUG
        assert test_config.environment == EnvironmentType.TESTING

        current_config = get_config()
        assert current_config is test_config