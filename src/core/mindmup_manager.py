# MindMup 管理器 - 整合 Google Drive 客戶端和 MindMup 解析器
# 提供高層次的心智圖檔案管理功能

from typing import List, Optional

from src.core.gdrive_client import GoogleDriveClient
from src.core.mindmup_parser import MindMupParser
from src.models.file_models import SearchQuery, FileInfo, OperationResult
from src.models.mindmap_models import MindMapSearchResult
from src.utils.enum import MimeType
from src.utils.logger import get_logger

logger = get_logger(__name__)



class MindMupManager:
    """
    MindMup 管理器類別
    整合 GoogleDriveClient 和 MindMupParser，提供完整的心智圖檔案管理功能：
    1. 搜尋 MindMup 檔案
    2. 載入和解析檔案內容
    3. 組合搜尋和解析功能
    """

    def __init__(self, gdrive_client: GoogleDriveClient):
        self.client = gdrive_client      # Google Drive API 客戶端
        self.parser = MindMupParser()    # MindMup 檔案解析器

    async def search_mindmup_files(
            self, folder_id: Optional[str] = None) -> List[FileInfo]:
        """
        搜尋所有 MindMup 檔案，包含子資料夾
        參數：
            folder_id: 指定資料夾 ID，若為 None 則搜尋整個 Drive
        """

        all_mindmup_files = []

        if folder_id:
            # 搜尋指定資料夾（包含子資料夾）
            files = await self._search_folder_for_mindmup(folder_id=folder_id)
            all_mindmup_files.extend(files)

        else:
            # 搜尋整個 Google Drive
            files = await self._search_all_drive_for_mindmup()
            all_mindmup_files.extend(files)

        logger.info(f'search_mindmup_files: {all_mindmup_files}')
        return all_mindmup_files

    async def _search_folder_for_mindmup(
            self, folder_id: str) -> List[FileInfo]:
        """在指定資料夾中搜尋 MindMup 檔案（遞迴搜尋子資料夾）"""
        mindmup_files = []

        query = SearchQuery(
            folder_id=folder_id,
            max_results=1000
        )
        result = await self.client.list_files(query=query)

        if not result.success:
            logger.error(
                f'_search_folder_for_mindmup error: {folder_id}: {result.error}')
            return mindmup_files

        files = result.data.get('files', [])

        for file_info in files:
            if file_info.is_mindmup():
                mindmup_files.append(file_info)
                logger.info(f'_search_folder_for_mindmup: found mindmup file {file_info.name}')
            elif file_info.is_folder():
                # 遞迴搜尋子資料夾
                subfolder_files = await self._search_folder_for_mindmup(file_info.id)
                mindmup_files.extend(subfolder_files)

        logger.info(f'_search_folder_for_mindmup: total found {len(mindmup_files)} mindmup files')
        return mindmup_files

    async def _search_all_drive_for_mindmup(self) -> List[FileInfo]:
        """搜尋整個 Google Drive，使用多種關鍵字組合"""
        mindmup_files = []

        # 使用多種搜尋查詢來找到所有可能的 MindMup 檔案
        queries = [
            SearchQuery(query='mindmup', max_results=100),    # 直接搜尋 'mindmup'
            SearchQuery(query='mindmap', max_results=100),    # 搜尋 'mindmap'
            SearchQuery(query='.mup', max_results=100),       # 搜尋 '.mup' 副檔名
            SearchQuery(mime_types=[MimeType.MINDMUP], max_results=100)  # 按 MIME 類型搜尋
        ]

        for query in queries:
            result = await self.client.list_files(query=query)
            if result.success:
                files = result.data.get('files', [])
                for file_info in files:
                    if file_info.is_mindmup() and file_info not in mindmup_files:
                        mindmup_files.append(file_info)

        logger.info(f'_search_all_drive_for_mindmup: {mindmup_files}')
        return mindmup_files

    async def load_mindmup(self, file_id: str) -> OperationResult:
        """下載並返回 MindMup 檔案內容"""
        try:
            logger.info(f'load_mindmup: {file_id}')

            # 從 Google Drive 下載檔案內容
            download_result = await self.client.download_file_content(file_id)
            if not download_result.success:
                return download_result

            file_content = download_result.data.get('content')
            if not file_content:
                return OperationResult.fail(
                    'No content found in downloaded file')

            logger.info(
                f'load_mindmup success: {download_result.data.get("name")}')
            return OperationResult.ok(file_content)

        except Exception as e:
            logger.error(f'load_mindmup error: {e}')
            return OperationResult.fail(f'load_mindmup error: {e}')

    async def parse_mindmup_file(self, file_content: str) -> OperationResult:
        """解析 MindMup 檔案內容"""
        try:
            mindmap = self.parser.parse_mindmup_content(file_content)
            logger.info(f'parse_mindmup_file success: {mindmap.title}')
            return OperationResult.ok(mindmap)
        except Exception as e:
            logger.error(f'parse_mindmup_file error: {e}')
            return OperationResult.fail(f'parse_mindmup_file error: {e}')

    async def search_and_parse_mindmups(
            self, folder_id: Optional[str] = None) -> List[MindMapSearchResult]:
        """搜尋並解析 MindMup 檔案，返回完整的搜尋結果"""
        search_results = []
        mindmup_files = await self.search_mindmup_files(folder_id=folder_id)

        for file_info in mindmup_files:
            try:
                logger.info(
                    f'Attempting to load mindmup for file: {file_info.id}, self type: {type(self)}, has load_mindmup: {hasattr(self, "load_mindmup")}')
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

                logger.info(f'search_and_parse_mindmups:{search_results}')

            except Exception as e:
                logger.error(f'search_and_parse_mindmups error:{e}')

        return search_results

    async def list_accessible_folders(self) -> List[FileInfo]:
        """列出所有可訪問的資料夾"""
        from src.models.file_models import MimeType
        # 只搜尋資料夾類型的檔案
        query = SearchQuery(mime_types=[MimeType.FOLDER], max_results=100)
        result = await self.client.list_files(query)

        if result.success:
            return result.data.get('files', [])
        else:
            logger.error(f'list_accessible_folders error: {result.error}')
            return []
