from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class MindMapNode:
    """心智圖節點"""
    id: str
    title: str
    children: List['MindMapNode'] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None

    def add_child(self, child: 'MindMapNode'):
        """添加子節點"""
        self.children.append(child)

    def remove_child(self, child_id: str) -> bool:
        """移除子節點"""
        for i, child in enumerate(self.children):
            if child.id == child_id:
                del self.children[i]
                return True
        return False

    def find_node(self, node_id: str) -> Optional['MindMapNode']:
        """遞迴搜尋節點"""
        if self.id == node_id:
            return self

        for child in self.children:
            result = child.find_node(node_id)
            if result:
                return result

        return None

    def get_depth(self) -> int:
        """取得節點深度"""
        if not self.children:
            return 1

        return 1 + max(child.get_depth() for child in self.children)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'children': [child.to_dict() for child in self.children],
            'attributes': self.attributes,
            'position': self.position
        }


@dataclass
class MindMap:
    """心智圖"""
    title: str
    root_node: MindMapNode
    version: str = "1.0"
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    author: Optional[str] = None
    description: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def format_version(self) -> str:
        """Compatibility property for format_version"""
        return self.version

    @property
    def id(self) -> str:
        """Get the root node ID"""
        return self.root_node.id

    @property
    def created_time(self) -> Optional[datetime]:
        """Compatibility property for created_time"""
        return self.created_at

    @property
    def modified_time(self) -> Optional[datetime]:
        """Compatibility property for modified_time"""
        return self.modified_at

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.modified_at is None:
            self.modified_at = datetime.now()

    def find_node(self, node_id: str) -> Optional[MindMapNode]:
        """搜尋指定 ID 的節點"""
        return self.root_node.find_node(node_id)

    def get_all_nodes(self) -> List[MindMapNode]:
        """取得所有節點"""
        nodes = []

        def collect_nodes(node: MindMapNode):
            nodes.append(node)
            for child in node.children:
                collect_nodes(child)

        collect_nodes(self.root_node)
        return nodes

    def get_node_count(self) -> int:
        """取得節點總數"""
        return len(self.get_all_nodes())

    def get_max_depth(self) -> int:
        """取得最大深度"""
        return self.root_node.get_depth()

    def get_all_text(self) -> List[str]:
        """取得所有文字內容"""
        texts = []

        def collect_text(node: MindMapNode):
            texts.append(node.title)
            for child in node.children:
                collect_text(child)

        collect_text(self.root_node)
        return texts

    def extract_text_content(self) -> List[str]:
        """Extract all text content (compatibility method)"""
        return self.get_all_text()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'title': self.title,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'author': self.author,
            'description': self.description,
            'root_node': self.root_node.to_dict(),
            'node_count': self.get_node_count(),
            'max_depth': self.get_max_depth()
        }

    def update_modified_time(self):
        """更新修改時間"""
        self.modified_at = datetime.now()


@dataclass
class MindMapSearchResult:
    """心智圖搜尋結果"""
    mindmap: MindMap
    file_id: str
    file_name: str
    file_url: Optional[str] = None
    last_modified: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'file_url': self.file_url,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'mindmap': self.mindmap.to_dict()
        }


@dataclass
class MindMapStats:
    """心智圖統計資訊"""
    total_nodes: int
    max_depth: int
    total_text_length: int
    node_titles: List[str]
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None

    @classmethod
    def from_mindmap(cls, mindmap: MindMap) -> 'MindMapStats':
        """從心智圖創建統計資訊"""
        all_text = mindmap.get_all_text()
        return cls(
            total_nodes=mindmap.get_node_count(),
            max_depth=mindmap.get_max_depth(),
            total_text_length=sum(len(text) for text in all_text),
            node_titles=all_text,
            creation_date=mindmap.created_at,
            modification_date=mindmap.modified_at
        )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'total_nodes': self.total_nodes,
            'max_depth': self.max_depth,
            'total_text_length': self.total_text_length,
            'node_titles': self.node_titles,
            'creation_date': self.creation_date.isoformat() if self.creation_date else None,
            'modification_date': self.modification_date.isoformat() if self.modification_date else None
        }