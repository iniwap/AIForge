from typing import Dict, Any, List
from .task_type_detector import TaskTypeDetector
from .ui_type_recommender import UITypeRecommender


class RuleBasedAdapter:
    """基于规则的UI适配器 - 统一处理AIForge核心数据结构"""

    def __init__(self):
        self.task_type_detector = TaskTypeDetector()
        self.ui_type_recommender = UITypeRecommender()

        # 统一的UI模板定义
        self.ui_templates = {
            "data_fetch": {
                "web_card": {
                    "primary_field": "title",
                    "secondary_fields": ["content", "source", "date"],
                    "max_items": None,  # 移除固定限制
                    "respect_user_requirements": True,  # 尊重用户需求
                },
                "web_table": {
                    "columns": ["title", "content", "source", "date"],
                    "max_content_length": 200,
                    "sortable": ["date", "title"],
                    "searchable": True,
                },
            },
            "file_operation": {
                "web_table": {
                    "columns": ["filename", "status", "size", "operation"],
                    "max_content_length": 100,
                }
            },
            "general": {
                "web_card": {"primary_field": "content", "secondary_fields": ["status", "summary"]}
            },
        }

    def _normalize_aiforge_data(self, data: Any) -> Dict[str, Any]:
        """统一处理AIForge核心返回的数据结构"""
        if isinstance(data, dict):
            # 处理标准的AIForge执行结果格式
            if "success" in data and "result" in data:
                result = data["result"]
                if isinstance(result, dict):
                    # 确保包含必要字段
                    normalized = {
                        "data": result.get("data", []),
                        "status": result.get("status", "success"),
                        "summary": result.get("summary", ""),
                        "metadata": result.get("metadata", {}),
                    }
                    return normalized
                else:
                    return {"data": [result], "status": "success", "summary": "单项结果"}

            # 处理已经是标准格式的数据
            elif "data" in data or "results" in data or "processed_files" in data:
                return data

            # 处理其他字典格式
            else:
                return {"data": [data], "status": "success", "summary": "数据项"}

        elif isinstance(data, list):
            return {"data": data, "status": "success", "summary": f"共 {len(data)} 条结果"}

        else:
            return {"data": [data], "status": "success", "summary": "单项结果"}

    def can_handle(self, task_type: str, ui_type: str) -> bool:
        """检查是否能处理指定的任务类型和UI类型"""
        return (
            task_type in self.ui_templates and ui_type in self.ui_templates[task_type]
        ) or task_type == "general"

    def adapt(self, data: Any, task_type: str, ui_type: str) -> Dict[str, Any]:
        """统一适配入口"""
        # 第一步：标准化数据格式
        normalized_data = self._normalize_aiforge_data(data)

        # 第二步：检测任务类型（如果未指定）
        if task_type == "general" or not task_type:
            detected_type = self.task_type_detector.detect_from_data(normalized_data)
            task_type = detected_type if detected_type != "general" else task_type

        # 第三步：选择适配方法
        adapter_methods = {
            "web_table": self._adapt_to_table,
            "web_card": self._adapt_to_card,
            "web_dashboard": self._adapt_to_dashboard,
            "web_progress": self._adapt_to_progress,
            "web_timeline": self._adapt_to_timeline,
            "web_editor": self._adapt_to_editor,
            "mobile_list": self._adapt_to_list,
            "terminal_text": self._adapt_to_text,
        }

        # 获取模板
        template = self._get_template(task_type, ui_type)

        # 执行适配
        adapter_method = adapter_methods.get(ui_type, self._adapt_generic)
        return adapter_method(normalized_data, template)

    def _get_template(self, task_type: str, ui_type: str) -> Dict[str, Any]:
        """获取适配模板"""
        if task_type in self.ui_templates and ui_type in self.ui_templates[task_type]:
            return self.ui_templates[task_type][ui_type]
        elif ui_type in self.ui_templates.get("general", {}):
            return self.ui_templates["general"][ui_type]
        else:
            return {}

    def _adapt_to_card(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为卡片格式"""
        if template.get("primary_field") == "title":
            return self._adapt_search_result_card(data, template)
        else:
            return self._adapt_default_card(data, template)

    def _adapt_search_result_card(
        self, data: Dict[str, Any], template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """搜索结果卡片格式"""
        results = data.get("data", [])

        # 从验证规则中获取用户期望的最小结果数
        metadata = data.get("metadata", {})
        validation_rules = metadata.get("validation_rules", {})
        min_items = validation_rules.get("min_items", 1)

        # 显示所有结果，但不少于用户要求的最小数量
        display_count = max(len(results), min_items) if results else min_items
        # 设置合理上限防止页面过长
        display_count = min(display_count, 20)

        display_items = []
        for i, result in enumerate(results[:display_count]):
            if isinstance(result, dict):
                title = result.get("title", f"结果 {i+1}")
                content = result.get("content", "")
                source = result.get("source", "")
                date = result.get("date", "")

                # 截断过长内容
                if len(content) > 150:
                    content = content[:150] + "..."

                display_items.append(
                    {
                        "type": "card",
                        "title": title,
                        "content": {
                            "primary": title,
                            "secondary": {"content": content, "source": source, "date": date},
                        },
                        "priority": 10 - i,
                    }
                )

        return {
            "display_items": display_items,
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "compact"},
            "actions": [
                {"label": "查看更多", "action": "expand", "data": {"total": len(results)}},
                {"label": "新搜索", "action": "search", "data": {}},
            ],
            "summary_text": data.get("summary", f"搜索结果: {len(results)} 条"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_default_card(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """默认卡片格式"""
        primary_field = template.get("primary_field", "content")
        secondary_fields = template.get("secondary_fields", [])

        # 处理数据内容
        data_items = data.get("data", [])
        if data_items and isinstance(data_items[0], dict):
            # 使用第一个数据项
            primary_data = data_items[0]
            primary_content = primary_data.get(primary_field, "")
            secondary_content = {
                field: primary_data.get(field, "")
                for field in secondary_fields
                if field in primary_data
            }
        else:
            # 使用汇总信息
            primary_content = data.get("summary", "数据处理完成")
            secondary_content = {
                "status": data.get("status", ""),
                "items": len(data_items) if isinstance(data_items, list) else 0,
            }

        # 添加系统信息
        secondary_content.update(
            {"summary": data.get("summary", ""), "status": data.get("status", "")}
        )

        return {
            "display_items": [
                {
                    "type": "card",
                    "title": "处理结果",
                    "content": {"primary": primary_content, "secondary": secondary_content},
                    "priority": 8,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [{"label": "详情", "action": "detail", "data": data}],
            "summary_text": data.get("summary", "数据卡片视图"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_table(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为表格格式"""
        columns = template.get("columns", [])
        max_content_length = template.get("max_content_length", 200)

        # 获取数据项
        items = data.get("data", [])
        if not items:
            items = data.get("results", [])
        if not items:
            items = data.get("processed_files", [])

        # 动态推断列名
        if not columns and items and isinstance(items[0], dict):
            columns = list(items[0].keys())[:6]  # 限制最多6列
        elif not columns:
            columns = ["content"]

        # 处理数据项
        processed_items = []
        for item in items:
            processed_item = {}
            if isinstance(item, dict):
                for col in columns:
                    value = item.get(col, "")
                    if isinstance(value, str) and len(value) > max_content_length:
                        value = value[:max_content_length] + "..."
                    processed_item[col] = value
            else:
                processed_item[columns[0] if columns else "content"] = str(item)
            processed_items.append(processed_item)

        return {
            "display_items": [
                {
                    "type": "table",
                    "title": "数据表格",
                    "content": {
                        "columns": columns,
                        "rows": processed_items,
                        "sortable": template.get("sortable", []),
                        "searchable": template.get("searchable", False),
                        "pagination": len(processed_items) > 50,
                    },
                    "priority": 9,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [
                {"label": "导出", "action": "export", "data": {"format": "csv"}},
                {"label": "刷新", "action": "refresh", "data": {}},
                {"label": "筛选", "action": "filter", "data": {"columns": columns}},
            ],
            "summary_text": data.get("summary", f"共 {len(processed_items)} 条记录"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_dashboard(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为仪表板格式"""
        items = data.get("data", [])

        # 生成统计信息
        stats = {
            "total_items": len(items),
            "status": data.get("status", "unknown"),
            "last_updated": data.get("metadata", {}).get("timestamp", ""),
        }

        return {
            "display_items": [
                {
                    "type": "dashboard",
                    "title": "数据仪表板",
                    "content": {"stats": stats, "charts": [], "summary": data.get("summary", "")},
                    "priority": 7,
                }
            ],
            "layout_hints": {"layout_type": "grid", "columns": 2, "spacing": "wide"},
            "actions": [{"label": "刷新", "action": "refresh", "data": {}}],
            "summary_text": data.get("summary", "仪表板视图"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_generic(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """通用适配方法"""
        return {
            "display_items": [
                {
                    "type": "generic",
                    "title": "数据视图",
                    "content": {
                        "data": data.get("data", []),
                        "summary": data.get("summary", ""),
                        "status": data.get("status", ""),
                    },
                    "priority": 5,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [],
            "summary_text": data.get("summary", "通用数据视图"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_list(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为移动端列表格式"""
        title_field = template.get("title_field", "title")
        subtitle_field = template.get("subtitle_field", "source")
        detail_fields = template.get("detail_fields", [])

        # 统一获取数据项
        items = data.get("data", [])
        if not items:
            items = data.get("results", [])
        if not items:
            items = data.get("processed_files", [])

        list_items = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                title = item.get(title_field, f"项目 {i+1}")
                subtitle = item.get(subtitle_field, "")
                details = {field: item.get(field, "") for field in detail_fields if field in item}
            else:
                title = f"项目 {i+1}"
                subtitle = str(item)
                details = {}

            list_items.append(
                {
                    "id": i,
                    "title": title,
                    "subtitle": subtitle,
                    "details": details,
                    "priority": len(items) - i,
                }
            )

        return {
            "display_items": [
                {
                    "type": "list",
                    "title": "列表视图",
                    "content": {
                        "items": list_items,
                        "layout": "vertical",
                        "item_spacing": "compact",
                    },
                    "priority": 8,
                }
            ],
            "layout_hints": {"layout_type": "list", "columns": 1, "spacing": "compact"},
            "actions": [
                {"label": "刷新", "action": "refresh", "data": {}},
                {"label": "查看详情", "action": "detail", "data": data},
            ],
            "summary_text": data.get("summary", f"共 {len(list_items)} 个项目"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_progress(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为进度显示格式"""
        progress_field = template.get("progress_field", "success_count")
        total_field = template.get("total_field", "total_files")

        # 从数据或元数据中获取进度信息
        metadata = data.get("metadata", {})
        progress = data.get(progress_field, metadata.get(progress_field, 0))
        total = data.get(total_field, metadata.get(total_field, len(data.get("data", []))))
        percentage = (progress / total * 100) if total > 0 else 0

        return {
            "display_items": [
                {
                    "type": "progress",
                    "title": "处理进度",
                    "content": {
                        "current": progress,
                        "total": total,
                        "percentage": percentage,
                        "status": data.get("status", "processing"),
                    },
                    "priority": 9,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "compact"},
            "actions": [
                {"label": "查看详情", "action": "detail", "data": data},
                {"label": "停止处理", "action": "stop", "data": {}},
            ],
            "summary_text": data.get("summary", f"进度: {progress}/{total} ({percentage:.1f}%)"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_timeline(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为时间线格式"""
        step_field = template.get("step_field", "executed_steps")

        # 从数据或元数据中获取步骤信息
        steps = data.get(step_field, [])
        if not steps and "data" in data:
            # 如果没有明确的步骤字段，尝试从数据中推断
            data_items = data["data"]
            if isinstance(data_items, list):
                steps = [f"处理项目 {i+1}" for i in range(len(data_items))]

        timeline_items = []
        for i, step in enumerate(steps):
            timeline_items.append(
                {
                    "step": i + 1,
                    "title": step if isinstance(step, str) else str(step),
                    "status": "completed",
                    "timestamp": data.get("metadata", {}).get("timestamp", f"Step {i + 1}"),
                }
            )

        return {
            "display_items": [
                {
                    "type": "timeline",
                    "title": "执行时间线",
                    "content": {"items": timeline_items},
                    "priority": 8,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [{"label": "重新执行", "action": "retry", "data": data}],
            "summary_text": data.get("summary", f"已完成 {len(steps)} 个步骤"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_editor(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为编辑器格式"""
        content_field = template.get("content_field", "generated_content")
        metadata_fields = template.get("metadata_fields", [])

        # 获取内容
        content = data.get(content_field, "")
        if not content and "data" in data:
            data_items = data["data"]
            if isinstance(data_items, list) and data_items:
                # 如果是列表，合并所有内容
                content = "\n".join([str(item) for item in data_items])
            else:
                content = str(data_items)

        # 获取元数据
        metadata = {field: data.get(field, "") for field in metadata_fields}
        metadata.update(data.get("metadata", {}))

        return {
            "display_items": [
                {
                    "type": "editor",
                    "title": "生成的内容",
                    "content": {
                        "text": content,
                        "metadata": metadata,
                        "editable": template.get("editable", False),
                    },
                    "priority": 9,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [
                {"label": "保存", "action": "save", "data": {"content": content}},
                {"label": "导出", "action": "export", "data": {"format": "txt"}},
                {"label": "重新生成", "action": "regenerate", "data": {}},
            ],
            "summary_text": data.get("summary", f"内容长度: {len(content)} 字符"),
            "metadata": data.get("metadata", {}),
        }

    def _adapt_to_text(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为终端文本格式"""
        format_type = template.get("format", "simple_text")
        fields = template.get("fields", [])

        # 根据格式类型生成文本内容
        if format_type == "simple_text":
            text_content = self._format_simple_text(data, fields)
        elif format_type == "structured_report":
            text_content = self._format_structured_report(data, fields)
        elif format_type == "progress_report":
            text_content = self._format_progress_report(data, fields)
        else:
            text_content = self._format_generic_text(data, fields)

        return {
            "display_items": [
                {
                    "type": "text",
                    "title": "文本输出",
                    "content": {"text": text_content, "format": "plain", "monospace": True},
                    "priority": 7,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [
                {"label": "复制", "action": "copy", "data": {"text": text_content}},
                {
                    "label": "导出",
                    "action": "export",
                    "data": {"format": "txt", "content": text_content},
                },
            ],
            "summary_text": data.get("summary", f"文本输出 ({len(text_content)} 字符)"),
            "metadata": data.get("metadata", {}),
        }

    def _format_simple_text(self, data: Dict[str, Any], fields: List[str]) -> str:
        """格式化简单文本"""
        lines = []

        # 添加汇总信息
        if data.get("summary"):
            lines.append(f"摘要: {data['summary']}")
        if data.get("status"):
            lines.append(f"状态: {data['status']}")
        lines.append("")

        # 处理数据项
        data_items = data.get("data", [])
        if isinstance(data_items, list):
            for i, item in enumerate(data_items):
                lines.append(f"项目 {i+1}:")
                if isinstance(item, dict):
                    for field in fields:
                        if field in item:
                            lines.append(f"  {field}: {item[field]}")
                else:
                    lines.append(f"  内容: {item}")
                lines.append("")

        return "\n".join(lines)

    def _format_structured_report(self, data: Dict[str, Any], fields: List[str]) -> str:
        """格式化结构化报告"""
        lines = ["=== 数据处理报告 ===", ""]

        # 基本信息
        lines.append(f"状态: {data.get('status', 'unknown')}")
        lines.append(f"摘要: {data.get('summary', '无')}")

        # 数据统计
        data_items = data.get("data", [])
        lines.append(f"数据项数量: {len(data_items) if isinstance(data_items, list) else 1}")
        lines.append("")

        # 详细数据
        if isinstance(data_items, list) and data_items:
            lines.append("=== 详细数据 ===")
            for i, item in enumerate(data_items[:5]):  # 限制显示前5项
                lines.append(f"项目 {i+1}:")
                if isinstance(item, dict):
                    for field in fields:
                        if field in item:
                            value = str(item[field])[:100]  # 限制长度
                            lines.append(f"  {field}: {value}")
                else:
                    lines.append(f"  内容: {str(item)[:100]}")
                lines.append("")

        return "\n".join(lines)

    def _format_progress_report(self, data: Dict[str, Any], fields: List[str]) -> str:
        """格式化进度报告"""
        lines = ["=== 处理进度报告 ===", ""]

        # 基本进度信息
        data_items = data.get("data", [])
        total_items = len(data_items) if isinstance(data_items, list) else 1

        lines.append(f"总项目数: {total_items}")
        lines.append(f"状态: {data.get('status', 'processing')}")
        lines.append(f"摘要: {data.get('summary', '处理中...')}")

        # 元数据信息
        metadata = data.get("metadata", {})
        if metadata:
            lines.append("")
            lines.append("=== 元数据 ===")
            for key, value in metadata.items():
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

    def _format_generic_text(self, data: Dict[str, Any], fields: List[str]) -> str:
        """格式化通用文本"""
        lines = []

        # 基本信息
        lines.append("=== 数据输出 ===")
        lines.append(f"状态: {data.get('status', 'unknown')}")
        lines.append(f"摘要: {data.get('summary', '无')}")
        lines.append("")

        # 数据内容
        data_items = data.get("data", [])
        if isinstance(data_items, list):
            lines.append(f"数据项: {len(data_items)} 个")
            for i, item in enumerate(data_items[:3]):  # 显示前3项
                lines.append(f"  {i+1}. {str(item)[:50]}...")
        else:
            lines.append(f"数据: {str(data_items)[:100]}")

        return "\n".join(lines)
