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
        logger.info('Starting MCP MindMup Google Drive server...')
        mcp_server.start()
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    except Exception as e:
        logger.error(f'Failed to start server: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()