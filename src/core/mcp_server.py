import asyncio
import os
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_manager import MindMupManager
from src.models.file_models import SearchQuery
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MCPServer:
    def __init__(self):
        self.mcp = FastMCP('Mindmup Google Drive Integration', host='0.0.0.0', port=9801)
        self.gdrive_client = None
        self.mindmup_manager = None
        self._setup_tools()
        self._setup_sse_routes()

    async def ping_tool(self) -> Dict[str, Any]:
        """Health check endpoint for SSE mode."""
        return {"status": "pong", "timestamp": time.time(), "server": "MCP MindMup Google Drive"}

    async def list_gdrive_files_tool(self, max_results: int = 10, file_type: Optional[str] = None, name_contains: Optional[str] = None) -> Dict[str, Any]:
        """List files from Google Drive with optional filtering."""
        if not self.gdrive_client:
            return {"error": "Google Drive client not initialized."}

        try:
            query = SearchQuery(
                max_results=max_results,
                mime_types=[file_type] if file_type else [],
                query=name_contains
            )
            result = await self.gdrive_client.list_files(query=query)

            if result.success:
                return result.data
            else:
                return {"error": result.error}
        except Exception as e:
            logger.error(f'list_gdrive_files error: {e}')
            return {"error": str(e)}

    async def search_mindmaps_tool(self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Search for MindMup files in Google Drive."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            files = await self.mindmup_manager.search_mindmup_files(folder_id=folder_id)
            files_data = []
            for file_info in files:
                files_data.append({
                    "id": file_info.id,
                    "name": file_info.name,
                    "mime_type": file_info.mime_type,
                    "size": file_info.size,
                    "modified_time": file_info.modified_time.isoformat() if file_info.modified_time else None,
                    "created_time": file_info.created_time.isoformat() if file_info.created_time else None,
                    "web_view_link": file_info.web_view_link,
                    "starred": file_info.starred,
                    "shared": file_info.shared,
                    "owned_by_me": file_info.owned_by_me
                })

            return {
                "files": files_data,
                "count": len(files_data)
            }

        except Exception as e:
            logger.error(f'search_mindmaps error: {e}')
            return {"error": str(e)}

    async def get_mindmap_content_tool(self, file_id: str) -> Dict[str, Any]:
        """Load and parse a specific mindmap file."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            load_result = await self.mindmup_manager.load_mindmup(file_id=file_id)
            if not load_result.success:
                return {"error": f"Failed to load file: {load_result.error}"}

            parse_result = await self.mindmup_manager.parse_mindmup_file(load_result.data)
            if not parse_result.success:
                return {"error": f"Failed to parse mindmap: {parse_result.error}"}

            mindmap = parse_result.data
            all_text = mindmap.extract_text_content()

            return {
                "mindmap": {
                    "title": mindmap.title,
                    "id": mindmap.id,
                    "format_version": mindmap.format_version,
                    "node_count": mindmap.get_node_count(),
                    "root_node": self._extract_node_info(mindmap.root_node),
                    "all_text_content": all_text,
                    "metadata": {
                        "created_time": mindmap.created_time.isoformat() if mindmap.created_time else None,
                        "modified_time": mindmap.modified_time.isoformat() if mindmap.modified_time else None,
                        "author": mindmap.author
                    }
                },
                "file_id": file_id
            }

        except Exception as e:
            logger.error(f'get_mindmap_content error: {e}')
            return {"error": str(e)}

    async def search_and_parse_mindmaps_tool(self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Search for MindMup files and parse their content."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            search_results = await self.mindmup_manager.search_and_parse_mindmups(folder_id=folder_id)

            results_data = []
            for result in search_results:
                all_text = result.mindmap.extract_text_content()

                results_data.append({
                    "file_id": result.file_id,
                    "file_name": result.file_name,
                    "file_url": result.file_url,
                    "last_modified": result.last_modified.isoformat() if result.last_modified else None,
                    "mindmap": {
                        "title": result.mindmap.title,
                        "id": result.mindmap.id,
                        "format_version": result.mindmap.format_version,
                        "node_count": result.mindmap.get_node_count(),
                        "all_text_content": all_text,
                        "preview": all_text[:500] + "..." if len(all_text) > 500 else all_text
                    }
                })

            return {
                "results": results_data,
                "count": len(results_data)
            }

        except Exception as e:
            logger.error(f'search_and_parse_mindmaps error: {e}')
            return {"error": str(e)}

    async def list_accessible_folders_tool(self) -> Dict[str, Any]:
        """List all accessible folders in Google Drive."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            folders = await self.mindmup_manager.list_accessible_folders()

            folders_data = []
            for folder in folders:
                folders_data.append({
                    "id": folder.id,
                    "name": folder.name,
                    "modified_time": folder.modified_time.isoformat() if folder.modified_time else None,
                    "web_view_link": folder.web_view_link,
                    "starred": folder.starred,
                    "shared": folder.shared,
                    "owned_by_me": folder.owned_by_me
                })

            return {
                "folders": folders_data,
                "count": len(folders_data)
            }

        except Exception as e:
            logger.error(f'list_accessible_folders error: {e}')
            return {"error": str(e)}

    def _extract_node_info(self, node):
        """Extract node information recursively."""
        node_info = {
            "id": node.id,
            "title": node.title,
            "children": []
        }

        if hasattr(node, 'attributes') and node.attributes:
            node_info["attributes"] = node.attributes

        if hasattr(node, 'position') and node.position:
            node_info["position"] = node.position

        for child in node.children:
            node_info["children"].append(self._extract_node_info(child))

        return node_info

    def _setup_tools(self):
        """Register all MCP tools."""
        self.mcp.tool()(self.ping_tool)
        self.mcp.tool()(self.list_gdrive_files_tool)
        self.mcp.tool()(self.search_mindmaps_tool)
        self.mcp.tool()(self.get_mindmap_content_tool)
        self.mcp.tool()(self.search_and_parse_mindmaps_tool)
        self.mcp.tool()(self.list_accessible_folders_tool)

    def _setup_sse_routes(self):
        """Setup SSE-specific routes for keep-alive."""

        @self.mcp.custom_route('/ping', methods=['GET'])
        async def ping_endpoint(request):
            """HTTP ping endpoint for SSE keep-alive."""
            from starlette.responses import JSONResponse
            return JSONResponse({"status": "pong", "timestamp": time.time(), "server": "MCP MindMup Google Drive"})

        @self.mcp.custom_route('/health', methods=['GET'])
        async def health_endpoint(request):
            """Health check endpoint."""
            from starlette.responses import JSONResponse
            return JSONResponse({
                "status": "healthy",
                "timestamp": time.time(),
                "clients_initialized": self.gdrive_client is not None and self.mindmup_manager is not None
            })

    def _load_environment(self):
        """Load environment variables from deployment directory."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_file = '.env.dev' if os.getenv('ENV', 'development') == 'development' else '.env.prod'
        env_path = os.path.join(project_root, 'deployment', env_file)

        logger.info(f'Project root: {project_root}')
        logger.info(f'Current working directory: {os.getcwd()}')
        logger.info(f'Loading env from: {env_path}')

        load_dotenv(env_path)

    async def initialize_clients(self):
        """Initialize Google Drive and MindMup clients."""
        try:
            self.gdrive_client = GoogleDriveClient()
            auth_result = await self.gdrive_client.authenticate()

            if not auth_result.success:
                logger.error(f'Failed to authenticate with Google Drive: {auth_result.error}')
                return False

            self.mindmup_manager = MindMupManager(self.gdrive_client)
            logger.info('Clients initialized successfully')
            return True
        except Exception as e:
            logger.error(f'Error initializing clients: {e}')
            return False

    def start(self, mode: str = 'stdio'):
        """Start the MCP server."""
        self._load_environment()

        # Initialize clients
        success = asyncio.run(self.initialize_clients())
        if not success:
            logger.error('Failed to initialize clients. Exiting.')
            return

        logger.info('Clients ready. Starting FastMCP server...')

        # Start server
        if mode == 'http':
            logger.info('Starting FastMCP server in SSE mode...')
            self.mcp.run(transport='sse')
        else:
            logger.info('Starting FastMCP server in stdio mode...')
            self.mcp.run()


# Create a singleton instance
mcp_server = MCPServer()
