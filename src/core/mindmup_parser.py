import json
from typing import Dict, Any, List

from src.models.mindmap_models import MindMapNode, MindMap
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MindMupParser:

    @staticmethod
    def parse_mindmup_content(content: str) -> MindMap:
        """Parse Mindmup content from a string."""
        try:
            data = json.loads(content)
            return MindMupParser._parse_mindmup_data(data)
        except json.JSONDecodeError as e:
            logger.error(f'parse_mindmup_content error: {e}')
            raise ValueError(f'parse_mindmup_content error: {e}')

    @staticmethod
    def _parse_mindmup_data(data: Dict[str, Any]) -> MindMap:
        """Parse mindmup title and node."""
        if 'title' in data:
            title = data['title']
        else:
            title = 'An untitled mindmap'

        root_node = MindMupParser._parse_node(data)

        return MindMap(
            title=title,
            root_node=root_node,
            version=data.get('formatVersion', '1.0'),
            raw_data=data
        )

    @staticmethod
    def _parse_node(node_data: Dict[str, Any]) -> MindMapNode:
        """Parse Mindmup node."""
        node_id = node_data.get('id', 'root')
        title = node_data.get('title', 'Untitled')

        children = []
        ideas = node_data.get('ideas', {})

        for key, child_data in ideas.items():
            if isinstance(child_data, dict):
                child_node = MindMupParser._parse_node(child_data)
                children.append(child_node)

        return MindMapNode(
            id=node_id,
            title=title,
            children=children,
            attributes=node_data.get('attr', {}),
            position=node_data.get('position', None)
        )

    @staticmethod
    def to_mindmup_format(mindmap: MindMap) -> str:
        """Convert Mindmup to JSON data."""
        data = {
            "title": mindmap.title,
            "formatVersion": mindmap.version,
            **MindMupParser._node_to_dict(mindmap.root_node)
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _node_to_dict(node: MindMapNode) -> Dict[str, Any]:
        """Node to dict."""
        result = {
            "id": node.id,
            "title": node.title
        }

        if node.attributes:
            result['attr'] = node.attributes

        if node.position:
            result['position'] = node.position

        if node.children:
            ideas = {}
            for i, child in enumerate(node.children, 1):
                ideas[str(i)] = MindMupParser._node_to_dict(child)
            result['ideas'] = ideas

        return result

    @staticmethod
    def extract_text_content(mindmap: MindMap) -> List[str]:
        """Extract all Mindmup content's text."""
        texts = []

        def extract_from_node(node: MindMapNode):
            texts.append(node.title)
            for child in node.children:
                extract_from_node(child)

        extract_from_node(mindmap.root_node)
        return texts

    @staticmethod
    def get_node_count(mindmap: MindMap) -> int:
        """Count the node numbers."""
        def count_nodes(node: MindMapNode) -> int:
            count = 1  # current node
            for child in node.children:
                count += count_nodes(child)
            return count

        return count_nodes(mindmap.root_node)
