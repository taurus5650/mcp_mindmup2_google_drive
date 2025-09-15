import asyncio
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_manager import MindMupManager
from src.models.file_models import SearchQuery
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MCPServer:
    def __init__(self):
        self.mcp = FastMCP('Mindmup Google Drive Integration')
        self.gdrive_client = None
        self.mindmup_manager = None
        self._setup_tools()

    def _setup_tools(self):
        """Register all MCP tools."""

        @self.mcp.tool()
        async def list_gdrive_files(
                max_results: int = 10, file_type: Optional[str] = None, name_contains: Optional[str] = None) -> Dict[str, Any]:
            """List files from Google Drive with optional filtering."""
            if not self.gdrive_client:
                return {"error": "Google Drive client not initialized."}

            try:
                query = SearchQuery(
                    max_results=max_results,
                    mime_types=file_type,
                    name_contains=name_contains
                )
                result = await self.gdrive_client.list_files(query=query)

                if result.success:
                    return result.data
                else:
                    return {"error": result.error}
            except Exception as e:
                logger.error(f'list_gdrive_files error: {e}')
                return {"error": str(e)}

        @self.mcp.tool()
        async def search_mindmaps(folder_id: Optional[str] = None) -> Dict[str, Any]:
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

        @self.mcp.tool()
        async def get_mindmap_content(file_id: str) -> Dict[str, Any]:
            """Load and parse a specific mindmap file."""
            if not self.mindmup_manager:
                return {"error": "MindMup manager not initialized"}

            try:
                result = await self.mindmup_manager.load_minmdup(file_id=file_id)

                if result.success:
                    return result.data
                else:
                    return {"error": result.error}

            except Exception as e:
                logger.error(f'get_mindmap_content error: {e}')
                return {"error": str(e)}

        @self.mcp.tool()
        async def search_and_parse_mindmaps(folder_id: Optional[str] = None) -> Dict[str, Any]:
            """Search for MindMup files and parse their content."""
            if not self.mindmup_manager:
                return {"error": "MindMup manager not initialized"}

            try:
                search_results = await self.mindmup_manager.search_and_parse_mindmups(folder_id=folder_id)

                # Convert search results to dictionaries
                results_data = []
                for result in search_results:
                    results_data.append({
                        "file_id": result.file_id,
                        "file_name": result.file_name,
                        "file_url": result.file_url,
                        "last_modified": result.last_modified.isoformat() if result.last_modified else None,
                        "mindmap": {
                            "title": result.mindmap.title,
                            "id": result.mindmap.id,
                            "format_version": result.mindmap.format_version
                        }
                    })

                return {
                    "results": results_data,
                    "count": len(results_data)
                }

            except Exception as e:
                logger.error(f'search_and_parse_mindmaps error: {e}')
                return {"error": str(e)}

        @self.mcp.tool()
        async def list_accessible_folders() -> Dict[str, Any]:
            """List all accessible folders in Google Drive."""
            if not self.mindmup_manager:
                return {"error": "MindMup manager not initialized"}

            try:
                folders = await self.mindmup_manager.list_accessible_folders()

                # Convert FileInfo objects to dictionaries
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

    async def initialize_clients(self):
        """Initialize Google Drive and MindMup clients."""
        try:
            self.gdrive_client = GoogleDriveClient()

            # Override credentials path from environment
            creds_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE')
            if creds_file:
                self.gdrive_client.config.google_drive.credentials_file = creds_file
                logger.info(f'Using credentials file: {creds_file}')

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

    def start(self):
        """Start the MCP server."""
        # Load environment variables from deployment directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_file = '.env.dev' if os.getenv('ENV', 'development') == 'development' else '.env.prod'
        env_path = os.path.join(project_root, 'deployment', env_file)
        load_dotenv(env_path)

        # Initialize clients before starting MCP server
        async def setup():
            success = await self.initialize_clients()
            if not success:
                logger.error('Failed to initialize clients. Exiting.')
                return False
            logger.info('Starting MCP server...')
            return True

        # Run setup and then start MCP server
        if asyncio.run(setup()):
            self.mcp.run()


# Create a singleton instance
mcp_server = MCPServer()
