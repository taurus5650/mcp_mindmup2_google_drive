from typing import List, Optional

from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_parser import MindMupParser
from src.models.file_models import SearchQuery, FileInfo, OperationResult
from src.models.mindmap_models import MindMapSearchResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MindMupManager:
    def __init__(self, gdrive_client: GoogleDriveClient):
        self.client = gdrive_client
        self.parser = MindMupParser()

    async def search_mindmup_files(self, folder_id: Optional[str] = None) -> List[FileInfo]:
        """Search all Mindmup file, inlcluding sub folder."""

        all_mindmup_files = []

        if folder_id:
            files = await self._search_folder_for_mindmup(folder_id=folder_id)
            all_mindmup_files.extend(files)

        else:
            # Search whole Drive
            files = await self._search_all_drive_for_mindmup()
            all_mindmup_files.extend(files)

        return all_mindmup_files

    async def _search_folder_for_mindmup(self, folder_id: str) -> List[FileInfo]:
        """Search Mindmup files in a folder."""
        mindmup_files = []

        query = SearchQuery(
            folder_id=folder_id,
            max_results=1000
        )
        result = await self.client.list_files(query=query)

        if not result.success:
            logger.error(f'_search_folder_for_mindmup error: {folder_id}: {result.error}')
            return mindmup_files

        files = result.data.get('files', [])

        for file_info in files:
            if file_info.is_mindmup():
                logger.info(f'_search_folder_for_mindmup found: {file_info.id}: {file_info.name}')
                mindmup_files.append(file_info)
            elif file_info.is_folder():
                logger.info(f'_search_folder_for_mindmup found sub folder: {file_info.id}: {file_info.name}')
                subfolder_files = await self._search_folder_for_mindmup(file_info.id)
                mindmup_files.extend(subfolder_files)

        return mindmup_files

    async def _search_all_drive_for_mindmup(self) -> List[FileInfo]:
        """Search whole Google Drive."""
        mindmup_files = []

        queries = [
            SearchQuery(query='mindmup', max_results=100),
            SearchQuery(query='mindmap', max_results=100),
            SearchQuery(query='.mup', max_results=100),
            SearchQuery(mime_types=['application/vnd.mindmup'], max_results=100)
        ]

        for query in queries:
            result = await self.client.list_files(query=query)
            if not result.success:
                files = result.data.get('files', [])
                for file_info in files:
                    if file_info.is_mindmup() and file_info not in mindmup_files:
                        mindmup_files.append(file_info)

        return mindmup_files

    async def load_mindmup(self, file_id: str) -> OperationResult:
        """Download and return MindMup file content."""
        try:
            logger.info(f'load_mindmup: {file_id}')

            # Download file content from Google Drive
            download_result = await self.client.download_file_content(file_id)
            if not download_result.success:
                return download_result

            file_content = download_result.data.get('content')
            if not file_content:
                return OperationResult.fail('No content found in downloaded file')

            logger.info(f'Successfully loaded MindMup file: {download_result.data.get("name")}')
            return OperationResult.ok(file_content)

        except Exception as e:
            logger.error(f'load_mindmup error: {e}')
            return OperationResult.fail(f'load_mindmup error: {e}')

    async def load_minmdup(self, file_id: str) -> OperationResult:
        """Get Mindmup and analysis (deprecated - use load_mindmup)."""
        logger.warning('load_minmdup is deprecated, use load_mindmup instead')
        return await self.load_mindmup(file_id)

    async def parse_mindmup_file(self, file_content: str) -> OperationResult:
        """Parse Mindmup content."""
        try:
            mindmap = self.parser.parse_mindmup_content(file_content)
            logger.info(f'parse_mindmup_file success: {mindmap.title}')
            return OperationResult.ok(mindmap)
        except Exception as e:
            logger.error(f'parse_mindmup_file error: {e}')
            return OperationResult.fail(f'parse_mindmup_file error: {e}')

    async def search_and_parse_mindmups(self, folder_id: Optional[str] = None) -> List[MindMapSearchResult]:
        """Search and parse MindMup files."""
        search_results = []
        mindmup_files = await self.search_mindmup_files(folder_id=folder_id)

        for file_info in mindmup_files:
            try:
                load_result = await self.load_mindmup(file_info.id)
                if load_result.success:
                    parse_result = await self.parse_mindmup_file(load_result.data)
                    if parse_result.success:
                        search_result = MindMapSearchResult(
                            mindmap=parse_result.data,
                            file_id=file_info.id,
                            file_name=file_info.name,
                            file_url=file_info.web_view_link,
                            last_modified=file_info.modified_time
                        )
                        search_results.append(search_result)

                logger.info(f'search_and_parse_mindmups:{file_info.name}')

            except Exception as e:
                logger.error(f'search_and_parse_mindmups error:{e}')

        return search_results

    async def list_accessible_folders(self) -> List[FileInfo]:
        """List all accessible folders."""
        from src.models.file_models import MimeType
        query = SearchQuery(mime_types=[MimeType.FOLDER], max_results=100)
        result = await self.client.list_files(query)

        if result.success:
            return result.data.get('files', [])
        else:
            logger.error(f'list_accessible_folders error: {result.error}')
            return []
