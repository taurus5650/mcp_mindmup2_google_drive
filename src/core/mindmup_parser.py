# MindMup 解析器 - 負責解析 MindMup 格式的 JSON 檔案
# 提供解析、轉換、搜尋等功能

import json
from typing import Dict, Any, List

from src.models.mindmap_models import MindMapNode, MindMap
from src.utils.logger import get_logger

logger = get_logger(__name__)

class MindMupParser:
    """
    MindMup 檔案解析器
    負責處理 MindMup 格式的 JSON 檔案，包含：
    1. 解析 JSON 為心智圖物件
    2. 將心智圖轉換回 JSON 格式
    3. 提供內容搜尋功能
    所有方法都是靜態方法，不需要實例化
    """

    @staticmethod
    def parse_mindmup_content(content: str) -> MindMap:
        """從字串解析 MindMup 內容"""
        try:
            data = json.loads(content)
            return MindMupParser._parse_mindmup_data(data)
        except json.JSONDecodeError as e:
            logger.error(f'parse_mindmup_content error: {e}')
            raise ValueError(f'parse_mindmup_content error: {e}')

    @staticmethod
    def _parse_mindmup_data(data: Dict[str, Any]) -> MindMap:
        """解析 MindMup 的標題和節點結構"""
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
        """遞迴解析 MindMup 節點，處理樹狀結構"""
        node_id = node_data.get('id', 'root')
        title = node_data.get('title', 'Untitled')

        children = []
        ideas = node_data.get('ideas', {})

        # 解析子節點 - MindMup 的 'ideas' 字段包含所有子節點
        for key, child_data in ideas.items():
            if isinstance(child_data, dict):
                child_node = MindMupParser._parse_node(node_data=child_data)
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
        """將心智圖物件轉換為 MindMup 格式的 JSON 字串"""
        data = {
            "title": mindmap.title,
            "formatVersion": mindmap.version,
            **MindMupParser._node_to_dict(mindmap.root_node)
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _node_to_dict(node: MindMapNode) -> Dict[str, Any]:
        """將節點轉換為字典格式（遞迴處理）"""
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
            for idx, child in enumerate(node.children, 1):
                ideas[str(idx)] = MindMupParser._node_to_dict(node=child)
            result['ideas'] = ideas

        return result

    @staticmethod
    def extract_text_content(mindmap: MindMap) -> List[str]:
        """提取心智圖中所有節點的文字內容"""
        texts = []

        def extract_from_node(node: MindMapNode):
            texts.append(node.title)
            for child in node.children:
                extract_from_node(child)

        extract_from_node(node=mindmap.root_node)
        return texts

    @staticmethod
    def get_node_count(mindmap: MindMap) -> int:
        """計算心智圖中的節點總數"""
        def count_nodes(node: MindMapNode) -> int:
            count = 1  # current node
            for child in node.children:
                count += count_nodes(child)
            return count

        return count_nodes(node=mindmap.root_node)

    @staticmethod
    def search_content(mindmap: MindMap, keyword: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """在心智圖內容中搜尋關鍵字，返回匹配的節點及其上下文"""
        matches = []
        search_keyword = keyword if case_sensitive else keyword.lower()

        def search_in_node(node: MindMapNode, path: List[str] = None):
            if path is None:
                path = []

            current_path = path + [node.title]
            search_text = node.title if case_sensitive else node.title.lower()

            if search_keyword in search_text:
                matches.append({
                    "node_id": node.id,
                    "title": node.title,
                    "path": " > ".join(current_path),
                    "depth": len(current_path) - 1,
                    "attributes": node.attributes if node.attributes else {},
                    "children_count": len(node.children)
                })

            for child in node.children:
                search_in_node(child, current_path)

        search_in_node(mindmap.root_node)
        return matches

    @staticmethod
    def get_node_with_context(mindmap: MindMap, node_id: str, include_siblings: bool = False) -> Dict[str, Any]:
        """取得特定節點及其上下文（父節點、子節點、兄弟節點）"""

        def find_node_with_context(node: MindMapNode, parent: MindMapNode = None, siblings: List[MindMapNode] = None):
            """遞迴搜尋指定節點並返回其上下文資訊"""
            if node.id == node_id:
                result = {
                    "node": {
                        "id": node.id,
                        "title": node.title,
                        "attributes": node.attributes if node.attributes else {},
                        "position": node.position
                    },
                    "children": [
                        {"id": child.id, "title": child.title}
                        for child in node.children
                    ],
                    "parent": {
                        "id": parent.id,
                        "title": parent.title
                    } if parent else None
                }

                if include_siblings and siblings:
                    result["siblings"] = [
                        {"id": sibling.id, "title": sibling.title}
                        for sibling in siblings if sibling.id != node_id
                    ]

                return result

            for child in node.children:
                result = find_node_with_context(child, node, node.children)
                if result:
                    return result

            return None

        return find_node_with_context(mindmap.root_node)
