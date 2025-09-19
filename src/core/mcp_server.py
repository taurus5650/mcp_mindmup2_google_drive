import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_manager import MindMupManager
from src.models.file_models import SearchQuery
from src.utils.logger import get_logger

logger = get_logger(__name__)

class MCPServer:
    # Claude content length limit (1MB)
    CLAUDE_MAX_CONTENT_LENGTH = 1048576

    def __init__(self):
        self.mcp = FastMCP(
            name='Mindmup2 Google Drive MCP',
            host='0.0.0.0',
            port=int(os.getenv('MCP_PORT', 9802))
        )
        self.gdrive_client = None
        self.mindmup_manager = None
        self._setup_tools()
        self._setup_sse_routes()

    async def list_gdrive_files_tool(
            self, max_results: int = 10, file_type: Optional[str] = None, name_contains: Optional[str] = None) -> Dict[str, Any]:
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

    async def search_mindmaps_tool(
            self, folder_id: Optional[str] = None) -> Dict[str, Any]:
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
            logger.info(f'search_mindmaps_tool: {files_data}')

            return {
                "files": files_data,
                "count": len(files_data)
            }

        except Exception as e:
            logger.error(f'search_mindmaps_tool error: {e}')
            return {"error": str(e)}

    async def get_mindmap_content_tool(self, file_id: str) -> Dict[str, Any]:
        """Load and parse a specific mindmap file."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            load_result = await self.mindmup_manager.load_mindmup(file_id=file_id)
            if not load_result.success:
                return {"error": f"Failed to load file: {load_result.error}"}

            parse_result = await self.mindmup_manager.parse_mindmup_file(file_content=load_result.data)
            if not parse_result.success:
                return {"error": f"Failed to parse mindmap: {parse_result.error}"}

            mindmap = parse_result.data
            all_text_list = mindmap.extract_text_content()
            all_text = ' '.join(all_text_list) if all_text_list else ''

            # Handle large content that exceeds Claude's limit
            all_text, content_truncated, original_length = self._handle_large_content(all_text, file_id)

            return_data = {
                "mindmap": {
                    "title": mindmap.title,
                    "id": mindmap.id,
                    "format_version": mindmap.format_version,
                    "node_count": mindmap.get_node_count(),
                    "root_node": self._extract_node_info(mindmap.root_node),
                    "all_text_content": all_text,
                    "content_truncated": content_truncated,
                    "original_content_length": original_length,
                    "metadata": {
                        "created_time": mindmap.created_time.isoformat() if mindmap.created_time else None,
                        "modified_time": mindmap.modified_time.isoformat() if mindmap.modified_time else None,
                        "author": mindmap.author
                    }
                },
                "file_id": file_id
            }
            logger.info(f'get_mindmap_content_tool: {return_data}')
            return return_data

        except Exception as e:
            logger.error(f'get_mindmap_content error: {e}')
            return {"error": str(e)}

    async def search_and_parse_mindmaps_tool(
            self, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Search for MindMup files and parse their content."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            search_results = await self.mindmup_manager.search_and_parse_mindmups(folder_id=folder_id)

            results_data = []

            for result in search_results:
                all_text_list = result.mindmap.extract_text_content()
                all_text = " ".join(all_text_list) if all_text_list else ""

                # Handle large content that exceeds Claude's limit
                all_text, content_truncated, original_length = self._handle_large_content(all_text, result.file_id)

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
                        "content_truncated": content_truncated,
                        "original_content_length": original_length,
                        "preview": all_text[:500] + "..." if len(all_text) > 500 else all_text
                    }
                })
            logger.info(f'search_and_parse_mindmaps_tool: {results_data}')
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
            logger.info(f'list_accessible_folders_tool: {folders_data}')
            return {
                "folders": folders_data,
                "count": len(folders_data)
            }

        except Exception as e:
            logger.error(f'list_accessible_folders error: {e}')
            return {"error": str(e)}

    async def search_mindmap_content_tool(self, file_id: str, keyword: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search for specific content within a mindmap file."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            # Load and parse the mindmap
            load_result = await self.mindmup_manager.load_mindmup(file_id=file_id)
            if not load_result.success:
                return {"error": f"Failed to load file: {load_result.error}"}

            parse_result = await self.mindmup_manager.parse_mindmup_file(file_content=load_result.data)
            if not parse_result.success:
                return {"error": f"Failed to parse mindmap: {parse_result.error}"}

            mindmap = parse_result.data

            # Search for content
            from src.core.mindmup_parser import MindMupParser
            matches = MindMupParser.search_content(mindmap, keyword, case_sensitive)

            logger.info(f'search_mindmap_content_tool: found {len(matches)} matches for "{keyword}" in {file_id}')

            return {
                "file_id": file_id,
                "keyword": keyword,
                "case_sensitive": case_sensitive,
                "matches": matches,
                "total_matches": len(matches),
                "mindmap_title": mindmap.title
            }

        except Exception as e:
            logger.error(f'search_mindmap_content error: {e}')
            return {"error": str(e)}

    async def get_mindmap_node_tool(self, file_id: str, node_id: str, include_siblings: bool = False) -> Dict[str, Any]:
        """Get specific node with context from a mindmap file."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            # Load and parse the mindmap
            load_result = await self.mindmup_manager.load_mindmup(file_id=file_id)
            if not load_result.success:
                return {"error": f"Failed to load file: {load_result.error}"}

            parse_result = await self.mindmup_manager.parse_mindmup_file(file_content=load_result.data)
            if not parse_result.success:
                return {"error": f"Failed to parse mindmap: {parse_result.error}"}

            mindmap = parse_result.data

            # Get node with context
            from src.core.mindmup_parser import MindMupParser
            node_context = MindMupParser.get_node_with_context(mindmap, node_id, include_siblings)

            if not node_context:
                return {"error": f"Node with ID '{node_id}' not found in mindmap"}

            logger.info(f'get_mindmap_node_tool: retrieved node {node_id} from {file_id}')

            return {
                "file_id": file_id,
                "mindmap_title": mindmap.title,
                **node_context
            }

        except Exception as e:
            logger.error(f'get_mindmap_node error: {e}')
            return {"error": str(e)}

    async def get_chunked_mindmap_content_tool(self, file_id: str, chunk_size: int = 50) -> Dict[str, Any]:
        """Get mindmap content in chunks to handle large files."""
        if not self.mindmup_manager:
            return {"error": "MindMup manager not initialized"}

        try:
            # Load and parse the mindmap
            load_result = await self.mindmup_manager.load_mindmup(file_id=file_id)
            if not load_result.success:
                return {"error": f"Failed to load file: {load_result.error}"}

            parse_result = await self.mindmup_manager.parse_mindmup_file(file_content=load_result.data)
            if not parse_result.success:
                return {"error": f"Failed to parse mindmap: {parse_result.error}"}

            mindmap = parse_result.data

            # Extract all text content
            all_text_list = mindmap.extract_text_content()
            total_nodes = len(all_text_list)

            # Create chunks
            chunks = []
            for i in range(0, total_nodes, chunk_size):
                chunk_texts = all_text_list[i:i + chunk_size]
                chunk_content = ' '.join(chunk_texts)
                chunks.append({
                    "chunk_id": i // chunk_size,
                    "start_node": i,
                    "end_node": min(i + chunk_size - 1, total_nodes - 1),
                    "node_count": len(chunk_texts),
                    "content": chunk_content,
                    "content_length": len(chunk_content)
                })

            logger.info(f'get_chunked_mindmap_content_tool: created {len(chunks)} chunks for {file_id}')

            return {
                "file_id": file_id,
                "mindmap_title": mindmap.title,
                "total_nodes": total_nodes,
                "chunk_size": chunk_size,
                "total_chunks": len(chunks),
                "chunks": chunks
            }

        except Exception as e:
            logger.error(f'get_chunked_mindmap_content error: {e}')
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

    def _handle_large_content(self, content: str, file_id: str = None) -> tuple[str, bool, int]:
        """Handle large content that may exceed Claude's processing limit.

        Returns:
            tuple: (truncated_content, was_truncated, original_length)
        """
        original_length = len(content)
        content_truncated = False

        if original_length > self.CLAUDE_MAX_CONTENT_LENGTH:
            content = content[:self.CLAUDE_MAX_CONTENT_LENGTH]
            content_truncated = True
            file_info = f" for file {file_id}" if file_id else ""
            logger.info(f'Content truncated{file_info}. Original length: {original_length}, truncated to: {self.CLAUDE_MAX_CONTENT_LENGTH}')

        return content, content_truncated, original_length

    def _setup_tools(self):
        """Register all MCP tools."""
        self.mcp.tool()(self.list_gdrive_files_tool)
        self.mcp.tool()(self.search_mindmaps_tool)
        self.mcp.tool()(self.get_mindmap_content_tool)
        self.mcp.tool()(self.search_and_parse_mindmaps_tool)
        self.mcp.tool()(self.list_accessible_folders_tool)
        # New tools for handling large content
        self.mcp.tool()(self.search_mindmap_content_tool)
        self.mcp.tool()(self.get_mindmap_node_tool)
        self.mcp.tool()(self.get_chunked_mindmap_content_tool)

    def _setup_sse_routes(self):
        """Setup SSE-specific routes for keep-alive."""

        @self.mcp.custom_route('/ping', methods=['GET'])
        async def ping_endpoint(request):
            """HTTP ping endpoint for SSE keep-alive."""
            from starlette.responses import JSONResponse
            return JSONResponse({
                "time": datetime.now().isoformat(),
                "server": "MCP MindMup Google Drive"
            })

        @self.mcp.custom_route('/health', methods=['GET'])
        async def health_endpoint(request):
            """Health check endpoint."""
            from starlette.responses import JSONResponse
            return JSONResponse({
                "time": datetime.now().isoformat(),
                "clients_initialized": self.gdrive_client is not None and self.mindmup_manager is not None
            })

    async def initialize_clients(self):
        """Initialize Google Drive and MindMup clients."""
        try:
            self.gdrive_client = GoogleDriveClient()
            auth_result = await self.gdrive_client.authenticate()

            if not auth_result.success:
                logger.error(
                    f'Failed to authenticate with Google Drive: {auth_result.error}')
                return False

            self.mindmup_manager = MindMupManager(self.gdrive_client)
            logger.info('Clients initialized successfully')
            return True
        except Exception as e:
            logger.error(f'Error initializing clients: {e}')
            return False

    def start(self, mode: str = 'stdio'):
        """Start the MCP server."""
        # Initialize clients
        success = asyncio.run(self.initialize_clients())
        if not success:
            logger.error('Failed to initialize clients. Exiting.')
            return

        logger.info('Clients ready. Starting FastMCP server')

        # Start server
        if mode == 'http':
            logger.info('Starting FastMCP server in SSE mode')
            self.mcp.run(transport='sse')
        else:
            logger.info('Starting FastMCP server in stdio mode')
            self.mcp.run()


# Create a singleton instance
mcp_server = MCPServer()