from typing import Dict, Any
from textual.widgets import Static, DataTable, Tree
from textual.containers import Vertical, Horizontal


class SmartDisplayWidget(Static):
    """智能显示组件"""

    def __init__(self, aiforge_core):
        super().__init__()
        self.aiforge_core = aiforge_core

    def display_result(self, result: Dict[str, Any]):
        """显示结果"""
        # 1. 基础显示（总是可用）
        try:
            # 2. 尝试智能适配
            adapted_result = self.aiforge_core.adapt_result_for_ui(result, "textual_widget")
            return self._render_adapted_result(adapted_result)
        except Exception:
            # 回退到基础显示
            return self._render_basic_result(result)

    def _render_adapted_result(self, adapted_result: Dict[str, Any]) -> Static:
        """渲染适配后的结果"""
        display_items = adapted_result.get("display_items", [])
        layout_hints = adapted_result.get("layout_hints", {})

        # 根据布局提示选择容器
        if layout_hints.get("layout_type") == "horizontal":
            container = Horizontal()
        else:
            container = Vertical()

        # 渲染显示项
        for item in sorted(display_items, key=lambda x: x.get("priority", 5), reverse=True):
            widget = self._create_widget_for_item(item)
            if widget:
                container.mount(widget)

        return container

    def _create_widget_for_item(self, item: Dict[str, Any]) -> Static:
        """为显示项创建组件"""
        item_type = item.get("type", "text")
        content = item.get("content", "")
        title = item.get("title", "")

        if item_type == "table":
            return self._create_table_widget(content, title)
        elif item_type == "list":
            return self._create_list_widget(content, title)
        elif item_type == "card":
            return self._create_card_widget(content, title)
        else:
            return Static(f"[bold]{title}[/bold]\n{content}")

    def _create_table_widget(self, content: Dict[str, Any], title: str) -> DataTable:
        """创建表格组件"""
        table = DataTable()
        table.title = title

        columns = content.get("columns", [])
        rows = content.get("rows", [])

        # 添加列
        for col in columns:
            table.add_column(col)

        # 添加行
        for row in rows:
            table.add_row(*[str(row.get(col, "")) for col in columns])

        return table

    def _create_list_widget(self, content: Dict[str, Any], title: str) -> Tree:
        """创建列表组件"""
        tree = Tree(title)
        items = content.get("items", [])

        for item in items:
            item_title = item.get("title", "")
            item_subtitle = item.get("subtitle", "")
            display_text = f"{item_title} - {item_subtitle}" if item_subtitle else item_title
            tree.root.add(display_text)

        return tree

    def _create_card_widget(self, content: Dict[str, Any], title: str) -> Static:
        """创建卡片组件"""
        primary = content.get("primary", "")
        secondary = content.get("secondary", {})

        card_content = f"[bold]{title}[/bold]\n{primary}\n"
        for key, value in secondary.items():
            card_content += f"{key}: {value}\n"

        return Static(card_content)

    def _render_basic_result(self, result: Dict[str, Any]) -> Static:
        """基础结果渲染"""
        import json

        return Static(json.dumps(result, ensure_ascii=False, indent=2))
