import os
import sys

from src.core.mcp_server import mcp_server
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main function to start the MCP server."""
    try:
        mode = os.getenv('MCP_MODE', 'stdio')
        logger.info(f'Starting MCP MindMup Google Drive server in {mode} mode...')
        mcp_server.start(mode)
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    except Exception as e:
        logger.error(f'Failed to start server: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
