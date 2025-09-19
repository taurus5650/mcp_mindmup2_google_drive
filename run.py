# 主程式入口 - 啟動 MCP (Model Context Protocol) 伺服器
# 這個伺服器專門處理 MindMup 心智圖檔案與 Google Drive 的整合

import os
import sys

from src.core.mcp_server import mcp_server
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """啟動 MCP 伺服器的主函數"""
    try:
        # 從環境變數取得運行模式，預設為 stdio（標準輸入輸出）
        mode = os.getenv('MCP_MODE', 'stdio')
        logger.info(f'Starting MCP MindMup Google Drive server in {mode} mode...')

        # 啟動伺服器 - mcp_server 是在 mcp_server.py 中建立的單例實例
        mcp_server.start(mode)
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
    except Exception as e:
        logger.error(f'Failed to start server: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
