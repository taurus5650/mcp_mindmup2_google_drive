from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class MindmupNode:
    id: str
    title: str
    children: List['MindmupNode'] = field(default_factory=list)
    attribute: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None

    def add_child_node(self, child: 'MindmupNode'):
        self.children.append(child)

    def remove_child_remove(self, child_id: str) -> bool:
        for idx, child in enumerate(self.children):
            if child.id == child_id:
                del self.children[idx]
                return True
        return False

    def find_node(self, node_id: str) -> Optional['MindmupNode']:
        if self.id == node_id:
            return self

        # Find all child node
        for child in self.children:
            result = child.find_node(node_id=node_id)
            if result:
                return result

    def get_depth(self) -> int:
        """Get the depth of node (include all child node)."""
        if not self.children:
            return 1

        return 1 + max(child.get_depth() for child in self.children)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "children": [child.to_dict() for child in self.children],
            "attribute": self.attribute,
            "position": self.position
        }


@dataclass
class Mindmup:
    title: str
    root_node: MindmupNode
    version: str = '1.0'
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    author: Optional[str] = None
    description: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def format_version(self) -> str:
        return self.version

    @property
    def id(self) -> str:
        return self.root_node.id

    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()
        if self.modified_time is None:
            self.modified_time = datetime.now()

    def find_the_specific_node(self, node_id: str) -> Optional[MindmupNode]:
        """Search all mindmup, and find the specific node id"""
        return self.root_node.find_node(node_id=node_id)

    def get_all_nodes(self) -> List[MindmupNode]:
        """Get all nodes in the mindmup (flattened list)."""
        nodes = []

        def collect_all_node(node: MindmupNode):
            """collect all node."""
            nodes.append(node)
            for child in node.children:
                collect_all_node(node=child)

        collect_all_node(self.root_node)
        return nodes

    def get_node_count(self) -> int:
        return len(self.get_all_nodes())

    def get_max_depth(self) -> int:
        return self.root_node.get_depth()

    def extract_text_content(self) -> List[str]:
        text = []

        def collect_text(node: MindmupNode):
            text.append(node.title)
            for child in node.children:
                collect_text(node=child)

        collect_text(self.root_node)
        return text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "created_time": self.created_time.isoformat() if self.created_time else None,
            "modified_time": self.modified_time.isoformat() if self.modified_time else None,
            "author": self.author,
            "description": self.description,
            "root_node": self.root_node.to_dict(),
            "node_count": self.get_node_count(),
            "max_depth": self.get_max_depth()
        }

    def update_modified_time(self):
        self.modified_time = datetime.now()
