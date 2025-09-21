import time
from typing import Optional, Dict, Tuple, List, Any

from src.model.common_model import OperationResult
from src.model.gdrive_model import SearchQuery, create_file_info
from src.utility.logger import get_logger

from src.core.gdrive_client import GoogleDriveClient
from src.utility.enum import MimeType

logger = get_logger(__name__)


class GoogleDriveFeature:

    MAX_FILE_SIZE_BYTES = 100000000  # 100MB - With chunking support

    def __init__(self, client: GoogleDriveClient):
        self.client = client

        self._file_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl = 300  # 5 mins
        self._max_cache_size = 100  # Cache 100 files

    async def list_file(
            self, query: Optional[SearchQuery] = None) -> OperationResult:
        """List out Gdrive file list."""

        try:
            if query is None:
                query = SearchQuery()

            search_query = query.to_drive_query()
            logger.info(f'list_file search_query: {search_query}')

            result = await self.client.run_sync(
                lambda: self.client.service.files().list(
                    q=search_query,
                    pageSize=min(query.max_result, 1000),
                    fields='nextPageToken,files(id,name,mimeType,size,modifiedTime,createdTime,parents,webViewLink,starred,shared,ownedByMe)',
                    orderBy='modifiedTime desc'
                ).execute()
            )

            result_file = result.get('files', [])
            file = [create_file_info(data) for data in result_file]
            logger.info(f'list_file found: {len(file)}')
            return OperationResult.success(detail={
                "files": file,
                "files_total_count": len(file),
                "next_page_token": result.get('nextPageToken')
            })
        except Exception as e:
            error_message = f'list_file error: {e}'
            logger.error(error_message)
            return OperationResult.fail(detail=error_message)

    async def search_mindmup_file(self, folder_id: Optional[str] = None, name_contain: Optional[str] = None) -> List:
        """Search for MindMup files in Google Drive."""
        try:
            mindmup_file = []
            all_search_patterns = []

            # Primary search patterns
            if name_contain:
                # If user provides specific search term, prioritize it
                all_search_patterns.append(name_contain)
                # Also try variations
                all_search_patterns.extend([f'{name_contain}.mup', f'{name_contain} mindmap'])

            # Always search for .mup files and common mindmap patterns
            all_search_patterns.extend(['.mup', 'mindmap', 'mindmup', 'mind map', 'mind-map'])

            # Remove duplicate while preserving order
            seen_pattern = set()
            unique_pattern = []
            for pattern in all_search_patterns:
                if pattern.lower() not in seen_pattern:
                    unique_pattern.append(pattern)
                    seen_pattern.add(pattern.lower())

            logger.info(f'Searching for MindMup file with pattern: {unique_pattern}')

            # Search with each pattern
            for pattern in unique_pattern:
                logger.info(f'Searching with pattern: {pattern}')
                query_pattern = SearchQuery(
                    max_result=1000,
                    folder_id=folder_id,
                    name_contain=pattern,
                    include_trashed=False
                )

                pattern_result = await self.list_file(query=query_pattern)
                if pattern_result.is_success:
                    pattern_file = pattern_result.detail.get('files', [])
                    logger.info(f'Pattern "{pattern}" found {len(pattern_file)} file')

                    # Filter for potential mindmup file
                    for f in pattern_file:
                        if f.is_mindmup() and f.id not in [existing.id for existing in mindmup_file]:
                            mindmup_file.append(f)
                            logger.info(f'Added potential MindMup file: {f.name} (ID: {f.id})')

            # If still no results, try broader MIME type search
            if not mindmup_file:
                logger.info('Pattern search found no MindMup files, trying MIME type search')

                # Search with broader MIME type
                mime_type_to_try = [
                    [MimeType.JSON],
                    [MimeType.TEXT],
                    [MimeType.MINDMUP],
                    [MimeType.OCTET],
                    [MimeType.JSON, MimeType.TEXT]  # Combined search
                ]

                for mime_type_list in mime_type_to_try:
                    query_mime = SearchQuery(
                        max_result=1000,
                        folder_id=folder_id,
                        mime_type=mime_type_list,
                        include_trashed=False
                    )

                    mime_result = await self.list_file(query=query_mime)
                    if mime_result.is_success:
                        all_file = mime_result.detail.get('files', [])
                        logger.info(f'MIME type {mime_type_list} search found {len(all_file)} file')

                        for f in all_file:
                            if f.is_mindmup() and f.id not in [existing.id for existing in mindmup_file]:
                                mindmup_file.append(f)
                                logger.info(f'Added MindMup file from MIME search: {f.name} (ID: {f.id})')

                    # Stop if we found some files
                    if mindmup_file:
                        break

            # Sort by modification time (newest first)
            mindmup_file.sort(key=lambda x: x.modified_time or x.created_time, reverse=True)

            logger.info(f'search_mindmup_file found {len(mindmup_file)} MindMup file total')
            for f in mindmup_file:
                logger.info(f'  - {f.name} (ID: {f.id}, MIME: {f.mime_type})')

            return mindmup_file

        except Exception as e:
            error_message = f'search_mindmup_file error: {e}'
            logger.error(error_message)
            return []

    async def get_file_metadata(self, file_id: str) -> Dict[str, Any]:
        """Get file metadata without downloading content."""
        try:
            file_metadata = await self.client.run_sync(
                lambda: self.client.service.files().get(
                    fileId=file_id,
                    fields='id,name,mimeType,size'
                ).execute()
            )
            return file_metadata
        except Exception as e:
            logger.error(f'get_file_metadata error: {file_id}, {e}')
            return {}

    async def download_file_content(self, file_id: str) -> OperationResult:
        """Download file from GDrive, include cache."""
        try:
            # Check cache
            if file_id in self._file_cache:
                cached_data, cached_time = self._file_cache[file_id]
                if time.time() - cached_time < self._cache_ttl:
                    logger.info(f'Using cached content for file: {file_id}')
                    return OperationResult.success(detail=cached_data)
                else:
                    # If almost expire then clean cache
                    del self._file_cache[file_id]

            logger.info(f'download_file_content: {file_id}')

            file_metadata = await self.client.run_sync(
                lambda: self.client.service.files().get(
                    fileId=file_id,
                    fields='id,name,mimeType,size'
                ).execute()
            )

            # Since we now filter out Google Apps files in is_mindmup(),
            # we only need to handle regular file downloads
            file_content = await self.client.run_sync(
                lambda: self.client.service.files().get_media(fileId=file_id).execute()
            )

            # Check content valid or not
            if file_content is None:
                return OperationResult.fail(
                    detail=f'{file_id} cannot be downloaded.')

            # According to MIME do decode
            if isinstance(file_content, bytes):
                try:
                    content_str = file_content.decode('utf-8')
                except UnicodeDecodeError:
                    content_str = file_content.decode('utf-8', errors='ignore')
            else:
                content_str = str(file_content)

            # Check content is null or not
            if not content_str:
                return OperationResult.fail(
                    detail=f'{file_id} empty or unreadable.')

            logger.info(
                f'download_file_content success: {file_metadata.get("name")} ({len(content_str)} characters)')

            result_data = {
                "file_id": file_id,
                "name": file_metadata.get('name'),
                "mime_type": file_metadata.get('mimeType'),
                "size": file_metadata.get('size'),
                "content_str": content_str
            }

            # The result add to cache
            self._file_cache[file_id] = (result_data, time.time())
            logger.info(f'Cached file content for: {file_id}')

            # Clean up the cache almost expire
            self._cleanup_cache()

            return OperationResult.success(detail=result_data)

        except Exception as e:
            error_message = f'download_file_content error: {file_id}, {e}'
            logger.error(error_message)
            return OperationResult.fail(error_message)

    def check_file_size(self, file_size_bytes: int, file_name: str) -> bool:
        """Check if file size is within acceptable limits."""
        if file_size_bytes > self.MAX_FILE_SIZE_BYTES:
            logger.warning(
                f'Skipping large file {file_name}: {file_size_bytes} bytes > {self.MAX_FILE_SIZE_BYTES} bytes limit')
            return False
        return True

    def _cleanup_cache(self):
        """Clean up the cache almost expire or already expired"""
        current_time = time.time()

        # Clean up the cache almost expire
        expired_key = [
            file_id for file_id, (_, timestamp) in self._file_cache.items()
            if current_time - timestamp > self._cache_ttl
        ]

        for key in expired_key:
            del self._file_cache[key]
            logger.info(f'Removed expired cache for: {key}')

        # If cache key too much, then remove the oldest one
        if len(self._file_cache) > self._max_cache_size:
            # order by time
            sorted_item = sorted(
                self._file_cache.items(),
                key=lambda x: x[1][1]  # order by time
            )

            item_to_remove = len(self._file_cache) - self._max_cache_size
            for i in range(item_to_remove):
                file_id = sorted_item[i][0]
                del self._file_cache[file_id]
                logger.info(f'Removed old cache for: {file_id}')

        if expired_key or len(self._file_cache) != len(self._file_cache):
            logger.info(
                f'Cache cleanup: {len(self._file_cache)}')
