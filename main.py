import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.mcp_server import mcp_server
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main function to start the MCP server."""
    try:
        # Check if running in HTTP mode (e.g., in Docker)
        mode = os.getenv('MCP_MODE', 'stdio')
        host = os.getenv('MCP_HOST', '0.0.0.0')
        port = int(os.getenv('MCP_PORT', '9801'))

        logger.info(f'Starting MCP MindMup Google Drive server in {mode} mode...')

        if mode == 'http':
            logger.info(f'HTTP server will listen on {host}:{port}')
            mcp_server.start(mode="http", host=host, port=port)
        else:
            mcp_server.start(mode="stdio")

    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    except Exception as e:
        logger.error(f'Failed to start server: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()