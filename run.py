import asyncio
import os
import sys

from src.utility.logger import get_logger

from src.core.mcp_server import MCPServer

logger = get_logger(__name__)


def main():
    """Starting the server."""

    mcp_server = MCPServer(
        name='Mindmup2 GDrive MCP Sever',
        host='0.0.0.0',
        port=9802
    )

    # Initialize Google Drive client
    asyncio.run(mcp_server.initialize_gdrive_client())

    try:
        # MCP Client mode | stdio, sse, streamable-http
        transport = os.getenv('MCP_TRANSPORT', 'sse')
        logger.info(f'Staring server in {transport}.')
        mcp_server.start(transport=transport)

    except KeyboardInterrupt:
        logger.info(f'Server stopped by user.')
    except Exception as e:
        logger.error(f'Sever error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
