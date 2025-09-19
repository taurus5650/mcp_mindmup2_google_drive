# 檔案模型 - 定義 Google Drive 檔案相關的資料結構
# 包含檔案資訊、搜尋查詢、操作結果等類別

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.utils.enum import MimeType, FileStatus


@dataclass
class FileInfo:
    """Google Drive 檔案資訊類別 - 封裝所有檔案相關的元數據"""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    modified_time: Optional[datetime] = None
    created_time: Optional[datetime] = None
    parents: List[str] = field(default_factory=list)
    web_view_link: Optional[str] = None
    web_content_link: Optional[str] = None
    status: FileStatus = FileStatus.ACTIVE

    description: Optional[str] = None
    starred: bool = False
    shared: bool = False
    owned_by_me: bool = True

    def is_folder(self) -> bool:
        """判斷是否為資料夾"""
        return self.mime_type == MimeType.FOLDER

    def is_mindmup(self) -> bool:
        """判斷是否為 MindMup 心智圖檔案
        透過多種方式檢查：MIME類型、檔案名稱模式、關鍵字
        """
        # 檢查官方 MindMup MIME 類型
        if self.mime_type == MimeType.MINDMUP:
            return True

        name_lower = self.name.lower()
        # 透過檔案名稱模式檢查 MindMup 檔案
        if (self.name.endswith('.mup') or
            'mindmap' in name_lower or
            'mindmup' in name_lower or
            'mind map' in name_lower or
                '.mup' in name_lower):
            return True

        # 檢查可能是 MindMup 檔案的 JSON 檔案
        if self.mime_type == MimeType.JSON and (
            'mind' in name_lower or
            'map' in name_lower or
            'diagram' in name_lower
        ):
            return True

        return False


@dataclass
class CreateFileRequest:
    """建立檔案請求類別 - 封裝建立新檔案所需的資訊"""
    name: str
    content: str
    mime_type: str = MimeType.JSON
    parent_id: Optional[str] = None

    def validate(self) -> List[str]:
        errors = []

        if not self.name.strip():
            errors.append('File name cannot be null or empty.')

        if not self.content:
            errors.append('Content cannot be null or empty.')

        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(c in self.name for c in invalid_chars):
            errors.append('File name contains invalid characters.')

        if self.mime_type == MimeType.JSON:
            try:
                json.loads(self.content)
            except json.JSONDecodeError:
                errors.append('Invalid JSON content.')

        return errors

    def to_metadata(self) -> Dict[str, Any]:
        """Convert to Gogole Drive metadata."""
        metadata = {
            "name": self.name,
            "mimeType": self.mime_type
        }

        if self.parent_id:
            metadata['parents'] = [self.parent_id]

        return metadata


@dataclass
class SearchQuery:
    """搜尋查詢類別 - 定義 Google Drive 檔案搜尋的條件"""
    query: Optional[str] = None
    folder_id: Optional[str] = None
    mime_types: List[str] = field(default_factory=list)
    max_results: int = 100
    include_trashed: bool = False
    name_contains: Optional[str] = None

    def to_drive_query(self) -> str:
        """轉換為 Google Drive API 的查詢字串"""
        conditions = []

        if not self.include_trashed:
            conditions.append('trashed=false')

        if self.folder_id:
            conditions.append(f'"{self.folder_id}" in parents')

        if self.query:
            conditions.append(f'name contains "{self.query}"')

        if self.name_contains:
            conditions.append(f'name contains "{self.name_contains}"')

        if self.mime_types:
            mime_conditions = [f'mimeType="{mt.value if hasattr(mt, "value") else str(mt)}"' for mt in self.mime_types]
            conditions.append(f"({' or '.join(mime_conditions)})")

        return ' and '.join(conditions) if conditions else ''


@dataclass
class OperationResult:
    """操作結果類別 - 標準化的操作返回結果，包含成功/失敗狀態和數據/錯誤訊息"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def ok(cls, data: Any = None) -> 'OperationResult':
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> 'OperationResult':
        return cls(success=False, error=error)


MINDMUP_QUERY = f'name contains ".mup" or (name contains "mindmup" and mimeType="{MimeType.JSON}")'
FOLDER_QUERY = f'mimeType={MimeType.FOLDER}'


def parse_drive_time(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse Google Drive time string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def create_file_info(data: Dict[str, Any]) -> FileInfo:
    """Create FileInfo object from Google Drive data."""
    return FileInfo(
        id=data['id'],
        name=data['name'],
        mime_type=data['mimeType'],
        size=data.get('size'),
        modified_time=parse_drive_time(data.get('modifiedTime')),
        created_time=parse_drive_time(data.get('createdTime')),
        parents=data.get('parents', []),
        web_view_link=data.get('webViewLink'),
        starred=data.get('starred', False),
        shared=data.get('shared', False)
    )


def success_result(data: Any = None) -> OperationResult:
    return OperationResult(success=True, data=data)


def error_result(error: str) -> OperationResult:
    return OperationResult(success=False, error=error)


def build_search_query(text: Optional[str] = None, folder_id: Optional[str] = None,
                       include_trashed: bool = False) -> str:
    query = SearchQuery(
        query=text,
        folder_id=folder_id,
        include_trashed=include_trashed
    )
    return query.to_drive_query()


def validate_file_name(name: str) -> bool:
    if not name.strip():
        return False

    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    return not any(c in name for c in invalid_chars)
