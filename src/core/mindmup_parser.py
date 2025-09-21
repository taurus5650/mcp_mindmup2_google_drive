import json
from typing import Dict, Any, List, Tuple

from src.model.mindmup_model import MindmupNode, Mindmup
from src.utility.logger import get_logger

logger = get_logger(__name__)


class MindmupParser:

    CLAUDE_MAX_CONTENT_LENGTH = 800000  # 800KB - Per chunk limit
    CHUNK_OVERLAP = 1000  # 1KB overlap between chunks for context

    @staticmethod
    def _parse_node(node_data: Dict[str, Any]) -> MindmupNode:
        """Parsing mindmup all node, and process tree structure (root and child)."""

        node_id = node_data.get('id', 'root')
        title = node_data.get('title', 'Untitled')

        children = []
        ideas = node_data.get('ideas', {})

        # Child node - mindmup's 'ideas'
        for key, child_data in ideas.items():
            if isinstance(child_data, dict):
                child_node = MindmupParser._parse_node(node_data=child_data)
                children.append(child_node)

        return MindmupNode(
            id=node_id,
            title=title,
            children=children,
            attribute=node_data.get('attr', {}),
            position=node_data.get('position', None)
        )

    @staticmethod
    def _parse_title_and_root_node(data: Dict[str, Any]) -> Mindmup:
        """Parse mindmup title and root node structure"""

        if 'title' in data:
            title = data['title']
        else:
            title = 'An untitled mindmap'

        root_node = MindmupParser._parse_node(data)

        return Mindmup(
            title=title,
            root_node=root_node,
            version=data.get('formatVersion', '1.0'),
            raw_data=data
        )

    @staticmethod
    def parse_content(content: str) -> Mindmup:
        """Parsing mindmup's all contents."""
        try:
            data = json.loads(content)
            return MindmupParser._parse_title_and_root_node(data=data)
        except json.JSONDecodeError as e:
            error_message = f'parse_content error: {e}'
            logger.error(error_message)
            raise ValueError(error_message)

    @staticmethod
    def extract_mindmap_structure(mindmap: Mindmup) -> Dict[str, Any]:
        """Extract structured information from large mindmaps focusing on hierarchy and key content."""
        try:
            # Extract key section for detailed analysis
            key_section = MindmupParser.extract_key_section(mindmap.root_node)

            # Create a focused summary of main test cases/scenarios
            test_case_summary = MindmupParser.extract_test_cases(mindmap.root_node, max_cases=10)

            structure = {
                "overview": {
                    "title": mindmap.title,
                    "total_nodes": mindmap.get_node_count(),
                    "max_depth": mindmap.get_max_depth(),
                    "created": mindmap.created_time.isoformat() if mindmap.created_time else None,
                    "modified": mindmap.modified_time.isoformat() if mindmap.modified_time else None
                },
                "hierarchy": MindmupParser.extract_node_hierarchy(mindmap.root_node, max_depth=10, max_children_per_level=10),
                "key_section": key_section,
                "test_cases": test_case_summary,
                "all_title": MindmupParser.get_all_node_title(mindmap.root_node, max_title=500)
            }
            return structure
        except Exception as e:
            logger.error(f'Error extracting mindmap structure: {e}')
            return {"error": f"Failed to extract structure: {e}"}

    @staticmethod
    def extract_node_hierarchy(node: MindmupNode, max_depth: int = 3, max_children_per_level: int = 10,
                               current_depth: int = 0) -> Dict[str, Any]:
        """Extract hierarchical structure with depth limits."""
        if current_depth >= max_depth:
            return {
                "title": node.title,
                "children_count": len(node.children),
                "has_more": len(node.children) > 0
            }

        children = []
        for i, child in enumerate(node.children[:max_children_per_level]):
            children.append(MindmupParser.extract_node_hierarchy(
                node=child,
                max_depth=max_depth,
                max_children_per_level=max_children_per_level,
                current_depth=current_depth + 1
            ))

        result = {
            "title": node.title,
            "children": children
        }

        if len(node.children) > max_children_per_level:
            result['truncated_children'] = len(node.children) - max_children_per_level

        return result

    @staticmethod
    def extract_key_section(root_node: MindmupNode) -> List[Dict[str, Any]]:
        """Extract key section (top-level and second-level nodes) with their immediate children."""
        key_section = []

        for main_section in root_node.children:
            section_info = {
                "title": main_section.title,
                "subsections": []
            }

            # Get immediate children (subsections)
            for subsection in main_section.children[:20]:  # Limit to 20 subsections
                subsection_info = {
                    "title": subsection.title,
                    "child_count": len(subsection.children)
                }

                # If subsection has children, get a few key ones
                if subsection.children:
                    subsection_info["key_items"] = [child.title for child in subsection.children[:5]]

                section_info["subsections"].append(subsection_info)

            if len(main_section.children) > 20:
                section_info["additional_subsections"] = len(main_section.children) - 20

            key_section.append(section_info)

        return key_section

    @staticmethod
    def extract_test_cases(root_node: MindmupNode, max_cases: int = 10) -> List[Dict[str, Any]]:
        """Extract test cases or main scenarios from the mindmap."""
        test_case_list = []
        main_section = []  # Store main sections

        # Look for nodes that might contain test cases
        case_keyword = ['case', 'test', 'scenario', '測試', '案例', '場景', 'story', 'flow', '流程',
                        '功能', 'feature', '模組', 'module', '需求', 'requirement']

        def find_test_nodes(node: MindmupNode, depth: int = 0, parent_title: str = ''):
            if len(test_case_list) >= max_cases * 2:  # Collect more initially
                return

            node_title_lower = node.title.lower()

            # Store main sections (depth 1)
            if depth == 1:
                main_section.append({
                    "title": node.title,
                    "children_count": len(node.children)
                })

            # Check if this node might be a test case
            is_potential_case = any(keyword in node_title_lower for keyword in case_keyword)

            # For app testing, also look for user action patterns
            action_keyword = ['註冊', '登入', '登錄', 'login', 'register', '匯款', '轉帳', 'transfer',
                              '查詢', 'query', '設定', 'setting', '驗證', 'verify', 'validation']
            is_action = any(keyword in node_title_lower for keyword in action_keyword)

            if is_potential_case or is_action or (depth <= 2 and len(node.children) > 0):
                case_info = {
                    "title": node.title,
                    "depth": depth,
                    "parent": parent_title,
                    "sub_items": [],
                    "priority": 0
                }

                # Calculate priority based on keywords
                if is_potential_case:
                    case_info["priority"] += 2
                if is_action:
                    case_info["priority"] += 1
                if depth <= 2:
                    case_info["priority"] += (3 - depth)

                # Get immediate children as sub-items
                for child in node.children[:8]:  # Get more sub-items for context
                    case_info["sub_items"].append(child.title)

                if case_info["sub_items"] or case_info["priority"] > 0:
                    test_case_list.append(case_info)

            # Continue searching in children
            for child in node.children:
                find_test_nodes(child, depth + 1, node.title)

        find_test_nodes(root_node)

        # Sort by priority and depth
        test_case_list.sort(key=lambda x: (-x['priority'], x['depth']))

        # If we have main sections, ensure they're represented
        result = []
        for section in main_section[:3]:  # Include top 3 main sections
            result.append({
                "title": section["title"],
                "type": "main_section",
                "children_count": section["children_count"]
            })

        # Add the most relevant test cases
        for case in test_case_list[:max_cases - len(result)]:
            result.append({
                "title": case["title"],
                "type": "test_case" if case["priority"] > 1 else "feature",
                "parent": case["parent"] if case["parent"] else None,
                "sub_items": case["sub_items"][:5] if case["sub_items"] else None
            })

        return result[:max_cases]

    @staticmethod
    def get_all_node_title(node: MindmupNode, max_title: int = 2000) -> List[str]:
        """Get all node title up to a maximum limit."""
        title_list = []

        def collect_title(current_node):
            if len(title_list) >= max_title:
                return
            title_list.append(current_node.title)
            for child in current_node.children:
                if len(title_list) >= max_title:
                    break
                collect_title(child)

        collect_title(node)
        return title_list

    @staticmethod
    def split_content_to_chunk(content: str, chunk_size: int = None) -> List[Dict[str, Any]]:
        """Split large content into manageable chunks."""
        if chunk_size is None:
            chunk_size = MindmupParser.CLAUDE_MAX_CONTENT_LENGTH

        if len(content) <= chunk_size:
            return [{
                "chunk_index": 0,
                "total_chunk": 1,
                "content": content,
                "start_pos": 0,
                "end_pos": len(content)
            }]

        chunk_list = []
        total_length = len(content)
        overlap = MindmupParser.CHUNK_OVERLAP

        pos = 0
        chunk_index = 0

        while pos < total_length:
            # Calculate chunk end position
            end_pos = min(pos + chunk_size, total_length)

            # Try to find a good break point (sentence or paragraph)
            if end_pos < total_length:
                # Look for paragraph break
                newline_pos = content.rfind('\n', pos + chunk_size - 1000, end_pos)
                if newline_pos > pos:
                    end_pos = newline_pos + 1
                else:
                    # Look for sentence break
                    period_pos = content.rfind('. ', pos + chunk_size - 500, end_pos)
                    if period_pos > pos:
                        end_pos = period_pos + 2

            chunk_list.append({
                "chunk_index": chunk_index,
                "content": content[pos:end_pos],
                "start_pos": pos,
                "end_pos": end_pos
            })

            # Move position with overlap
            pos = end_pos - overlap if end_pos < total_length else end_pos
            chunk_index += 1

        # Add total chunk count to each chunk
        for chunk in chunk_list:
            chunk["total_chunk"] = len(chunk_list)

        return chunk_list

    @staticmethod
    def handle_large_content(content: str, file_id: str) -> Tuple[str, bool, int]:
        """Handle large content that exceeds Claude's maximum content length."""
        original_length = len(content)
        content_truncated = False

        if original_length > MindmupParser.CLAUDE_MAX_CONTENT_LENGTH:
            # Smart truncation: try to keep complete sentences/nodes
            truncated_content = content[:MindmupParser.CLAUDE_MAX_CONTENT_LENGTH]

            # Find the last complete sentence or reasonable break point
            last_period = truncated_content.rfind('.')
            last_newline = truncated_content.rfind('\n')
            last_space = truncated_content.rfind(' ')

            # Use the best break point found
            break_point = max(last_period, last_newline, last_space)
            if break_point > MindmupParser.CLAUDE_MAX_CONTENT_LENGTH * 0.8:  # If break point is reasonably close
                content = truncated_content[:break_point + 1]
            else:
                content = truncated_content

            content_truncated = True
            logger.warning(
                f'Content truncated for file {file_id}: {original_length} -> {len(content)} characters')

        return content, content_truncated, original_length

    @staticmethod
    def create_content_summary(content: str, max_length: int = 1000) -> str:
        """Create a summary of the content focusing on key information."""
        if len(content) <= max_length:
            return content

        # Split by common delimiter and prioritize important content
        sentence_list = content.replace('\n', ' ').split('. ')
        summary_part = []
        current_length = 0

        # Add first few sentence
        for i, sentence in enumerate(sentence_list[:10]):  # Only first 10 sentence
            sentence = sentence.strip()
            if sentence and current_length + len(sentence) < max_length:
                summary_part.append(sentence)
                current_length += len(sentence) + 2  # +2 for '. '
            else:
                break

        summary = '. '.join(summary_part)
        if len(summary) < len(content):
            summary += f"... [Content truncated. Original length: {len(content)} chars]"

        return summary

    @staticmethod
    def search_node(node: MindmupNode, keyword: str, max_result: int = 50) -> List[Dict[str, Any]]:
        """Search for node containing keyword in title.

        Args:
            node: Root node to start search from
            keyword: Keyword to search for
            max_result: Maximum number of result to return

        Returns:
            List of matching node with path and children
        """
        result = []
        keyword_lower = keyword.lower()

        def search_recursive(current_node: MindmupNode, path: str = ""):
            if len(result) >= max_result:
                return

            current_path = f"{path} > {current_node.title}" if path else current_node.title

            # Check if keyword is in title
            if keyword_lower in current_node.title.lower():
                node_info = {
                    "title": current_node.title,
                    "path": current_path,
                    "children_count": len(current_node.children),
                    "children": [child.title for child in current_node.children[:10]]
                }

                # Add attribute if exists
                if current_node.attribute:
                    node_info['attribute'] = current_node.attribute

                result.append(node_info)

            # Search in children
            for child in current_node.children:
                search_recursive(current_node=child, path=current_path)

        search_recursive(node)
        return result
