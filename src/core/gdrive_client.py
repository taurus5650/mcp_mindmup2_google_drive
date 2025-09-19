import asyncio
import functools
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from src.models.file_models import (
    SearchQuery, OperationResult,
    create_file_info, success_result, error_result
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDriveClient:
    def __init__(self):
        self.service = None
        self.credentials = None
        self._executor = ThreadPoolExecutor(max_workers=5)

    async def authenticate(self) -> OperationResult:
        try:
            logger.info('Authenticating with Google Drive.')
            creds_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE')

            # If no environment variable set, try default locations
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
                return error_result(error=f'Credentials file not found: {creds_file}. Please set GOOGLE_DRIVE_CREDENTIALS_FILE environment variable or place the file at deployment/credentials/google_service_account.json')

            # Default scopes for Google Drive
            scopes = [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]

            # Load credentials from JSON file
            self.credentials = service_account.Credentials.from_service_account_file(
                creds_file,
                scopes=scopes
            )

            # Build service
            self.service = build('drive', 'v3', credentials=self.credentials)

            # Test connection
            await self._test_connection()
            return success_result('Authentication successful.')
        except Exception as e:
            logger.error(f'Error authenticating with Google Drive: {e}')
            return error_result(error=f'Error authenticating with Google Drive: {e}')

    async def _test_connection(self):
        """Try to connect Google Drive."""
        try:
            result = await self._run_sync(
                lambda: self.service.about().get(fields='user, storageQuota').execute()
            )
            user_email = result.get('user', {}).get('emailAddress', 'Unknown')
            logger.info(f'Service Account: {user_email}.')
        except Exception as e:
            raise Exception(f'Error testing connection: {e}') from e

    async def _run_sync(self, func, *args, **kwargs):
        """
        Run a synchronous function in a separate thread to avoid blocking the asyncio event loop.
        Uses functools.partial to handle keyword arguments correctly.
        """
        loop = asyncio.get_running_loop()
        # Use functools.partial to wrap the function and its arguments
        return await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))

    async def list_files(self, query: Optional[SearchQuery] = None) -> OperationResult:
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
            return success_result({
                "files": files,
                "files_total_count": len(files),
                "next_page_token": result.get('nextPageToken')
            })
        except Exception as e:
            logger.error(f'Error of list files: {e}')
            return error_result(error=f'Error of list files: {e}')

    async def download_file_content(self, file_id: str) -> OperationResult:
        """Download file content from Google Drive."""
        try:
            logger.info(f'Downloading file content: {file_id}')

            # Get file metadata first
            file_metadata = await self._run_sync(
                lambda: self.service.files().get(fileId=file_id, fields='id,name,mimeType,size').execute()
            )

            # Download file content
            file_content = await self._run_sync(
                lambda: self.service.files().get_media(fileId=file_id).execute()
            )

            # Decode content based on mime type
            if isinstance(file_content, bytes):
                try:
                    content_str = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    content_str = file_content.decode('utf-8', errors='ignore')
            else:
                content_str = str(file_content)

            logger.info(f'Successfully downloaded file: {file_metadata.get("name")} ({len(content_str)} characters)')

            return success_result({
                "file_id": file_id,
                "name": file_metadata.get('name'),
                "mime_type": file_metadata.get('mimeType'),
                "size": file_metadata.get('size'),
                "content": content_str
            })

        except Exception as e:
            logger.error(f'Error downloading file {file_id}: {e}')
            return error_result(error=f'Error downloading file {file_id}: {e}')
