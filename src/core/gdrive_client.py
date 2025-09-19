# Google Drive 客戶端 - 負責與 Google Drive API 溝通
# 提供身份驗證、檔案列表、下載等功能

import asyncio
import functools
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List

from google.oauth2 import service_account
from googleapiclient.discovery import build

from src.models.file_models import (
    SearchQuery, OperationResult,
    create_file_info
)
from src.utils.enum import MimeType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDriveClient:
    """
    Google Drive API 客戶端類別
    負責處理與 Google Drive 的所有交互，包含：
    1. 身份驗證（使用 Service Account）
    2. 檔案列表和搜尋
    3. 檔案內容下載
    """

    def __init__(self):
        self.service = None  # Google Drive API 服務物件
        self.credentials = None  # 身份驗證物件
        self._executor = ThreadPoolExecutor(max_workers=5)  # 非同步作業線程池

    async def authenticate(self) -> OperationResult:
        """
        身份驗證方法 - 使用 Service Account 身份驗證
        會嘗試多個預設位置的身份驗證檔案
        """
        try:
            logger.info('Authenticating with Google Drive.')
            # 從環境變數取得身份驗證檔案路徑
            creds_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE')

            # 如果環境變數未設定，嘗試預設位置
            if not creds_file:
                default_paths = [
                    'deployment/credentials/google_service_account.json',
                    'credentials/google_service_account.json',
                    'google_service_account.json'
                ]
                for path in default_paths:
                    if Path(path).exists():
                        creds_file = path
                        logger.info(f'Using credentials file from default location: {creds_file}')
                        break

            if not creds_file or not Path(creds_file).exists():
                return OperationResult.fail(f'Credentials file not found: {creds_file}. Please set GOOGLE_DRIVE_CREDENTIALS_FILE environment variable or place the file at deployment/credentials/google_service_account.json')

            # Google Drive API 所需的權限範圍
            scopes = [
                'https://www.googleapis.com/auth/drive',         # 完整 Drive 訪問權限
                'https://www.googleapis.com/auth/drive.file'     # 檔案訪問權限
            ]

            # 從 JSON 檔案載入身份驗證
            self.credentials = service_account.Credentials.from_service_account_file(
                creds_file,
                scopes=scopes
            )

            # 建立 Google Drive API 服務
            self.service = build('drive', 'v3', credentials=self.credentials)

            # 測試連線
            await self._test_connection()
            return OperationResult.ok('Authentication successful.')
        except Exception as e:
            logger.error(f'Error authenticating with Google Drive: {e}')
            return OperationResult.fail(f'Error authenticating with Google Drive: {e}')

    async def _test_connection(self):
        """測試 Google Drive 連線狀態"""
        try:
            # 取得用戶資訊來驗證連線
            result = await self._run_sync(
                lambda: self.service.about().get(fields='user, storageQuota').execute()
            )
            user_email = result.get('user', {}).get('emailAddress', 'Unknown')
            logger.info(f'Service Account: {user_email}.')
        except Exception as e:
            raise Exception(f'Error testing connection: {e}') from e

    async def _run_sync(self, func, *args, **kwargs):
        """
        在獨立線程中執行同步函數，避免阻塞 asyncio 事件迴圈
        使用 functools.partial 正確處理關鍵字參數
        """
        loop = asyncio.get_running_loop()
        # 使用 functools.partial 封裝函數和其參數
        return await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))

    async def list_files(self, query: Optional[SearchQuery] = None) -> OperationResult:
        """
        列出 Google Drive 檔案
        參數：
            query: 搜尋查詢條件，可指定資料夾、檔案類型等
        """
        try:
            if query is None:
                query = SearchQuery()

            logger.info(f'List files: (max_results={query.max_results})')

            search_query = query.to_drive_query()
            logger.debug(f'Query: {search_query}')

            result = await self._run_sync(
                lambda: self.service.files().list(
                    q=search_query,
                    pageSize=min(query.max_results, 1000),
                    fields='nextPageToken,files(id,name,mimeType,size,modifiedTime,createdTime,parents,webViewLink,starred,shared,ownedByMe)',
                    orderBy='modifiedTime desc'
                ).execute()
            )

            files_data = result.get('files', [])

            files = [create_file_info(data) for data in files_data]
            logger.info(f'Found {len(files)} files.')
            return OperationResult.ok({
                "files": files,
                "files_total_count": len(files),
                "next_page_token": result.get('nextPageToken')
            })
        except Exception as e:
            logger.error(f'Error of list files: {e}')
            return OperationResult.fail(f'Error of list files: {e}')

    async def download_file_content(self, file_id: str) -> OperationResult:
        """從 Google Drive 下載檔案內容"""
        try:
            logger.info(f'Downloading file content: {file_id}')

            # 先取得檔案元數據
            file_metadata = await self._run_sync(
                lambda: self.service.files().get(fileId=file_id, fields='id,name,mimeType,size').execute()
            )

            # 下載檔案內容
            file_content = await self._run_sync(
                lambda: self.service.files().get_media(fileId=file_id).execute()
            )

            # 檢查檔案內容是否有效
            if file_content is None:
                return OperationResult.fail(f'File {file_id} cannot be downloaded - may be a Google Docs file or requires special access')

            # 根據 MIME 類型解碼內容
            if isinstance(file_content, bytes):
                try:
                    content_str = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    content_str = file_content.decode('utf-8', errors='ignore')
            else:
                content_str = str(file_content)

            # 檢查內容是否為空
            if not content_str:
                return OperationResult.fail(f'File {file_id} appears to be empty or unreadable')

            logger.info(f'Successfully downloaded file: {file_metadata.get("name")} ({len(content_str)} characters)')

            return OperationResult.ok({
                "file_id": file_id,
                "name": file_metadata.get('name'),
                "mime_type": file_metadata.get('mimeType'),
                "size": file_metadata.get('size'),
                "content": content_str
            })

        except Exception as e:
            logger.error(f'Error downloading file {file_id}: {e}')
            return OperationResult.fail(f'Error downloading file {file_id}: {e}')

    async def search_mindmup_files(self, folder_id: Optional[str] = None) -> List:
        """
        搜尋所有 MindMup 檔案，包含子資料夾
        整合原本在 MindMupManager 中的搜尋邏輯
        """
        from src.models.file_models import FileInfo

        all_mindmup_files = []

        if folder_id:
            # 搜尋指定資料夾（包含子資料夾）
            files = await self._search_folder_for_mindmup(folder_id=folder_id)
            all_mindmup_files.extend(files)
        else:
            # 搜尋整個 Google Drive
            files = await self._search_all_drive_for_mindmup()
            all_mindmup_files.extend(files)

        logger.info(f'search_mindmup_files: found {len(all_mindmup_files)} files')
        return all_mindmup_files

    async def _search_folder_for_mindmup(self, folder_id: str) -> List:
        """在指定資料夾中搜尋 MindMup 檔案（遞迴搜尋子資料夾）"""
        from src.models.file_models import FileInfo

        mindmup_files = []

        query = SearchQuery(
            folder_id=folder_id,
            max_results=1000
        )
        result = await self.list_files(query=query)

        if not result.success:
            logger.error(
                f'_search_folder_for_mindmup error: {folder_id}: {result.error}')
            return mindmup_files

        files = result.data.get('files', [])

        for file_info in files:
            if file_info.is_mindmup() and file_info.is_downloadable():
                mindmup_files.append(file_info)
                logger.info(f'_search_folder_for_mindmup: found downloadable mindmup file {file_info.name}')
            elif file_info.is_mindmup() and not file_info.is_downloadable():
                logger.warning(f'_search_folder_for_mindmup: skipping non-downloadable mindmup file {file_info.name} (type: {file_info.mime_type})')
            elif file_info.is_folder():
                # 遞迴搜尋子資料夾
                subfolder_files = await self._search_folder_for_mindmup(file_info.id)
                mindmup_files.extend(subfolder_files)

        logger.info(f'_search_folder_for_mindmup: total found {len(mindmup_files)} mindmup files')
        return mindmup_files

    async def _search_all_drive_for_mindmup(self) -> List:
        """搜尋整個 Google Drive，使用多種關鍵字組合"""
        from src.models.file_models import FileInfo

        mindmup_files = []

        # 使用多種搜尋查詢來找到所有可能的 MindMup 檔案
        queries = [
            SearchQuery(query='mindmup', max_results=100),    # 直接搜尋 'mindmup'
            SearchQuery(query='mindmap', max_results=100),    # 搜尋 'mindmap'
            SearchQuery(query='.mup', max_results=100),       # 搜尋 '.mup' 副檔名
            SearchQuery(mime_types=[MimeType.MINDMUP], max_results=100)  # 按 MIME 類型搜尋
        ]

        for query in queries:
            result = await self.list_files(query=query)
            if result.success:
                files = result.data.get('files', [])
                for file_info in files:
                    if (file_info.is_mindmup() and
                        file_info.is_downloadable() and
                        file_info not in mindmup_files):
                        mindmup_files.append(file_info)

        logger.info(f'_search_all_drive_for_mindmup: found {len(mindmup_files)} files')
        return mindmup_files

    async def list_accessible_folders(self) -> List:
        """列出所有可訪問的資料夾"""
        from src.models.file_models import FileInfo

        # 只搜尋資料夾類型的檔案
        query = SearchQuery(mime_types=[MimeType.FOLDER], max_results=100)
        result = await self.list_files(query)

        if result.success:
            return result.data.get('files', [])
        else:
            logger.error(f'list_accessible_folders error: {result.error}')
            return []
