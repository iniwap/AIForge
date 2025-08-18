from typing import Dict, Any, List
from .task_type_detector import TaskTypeDetector
from .ui_type_recommender import UITypeRecommender
from ...core.result import AIForgeResult


class RuleBasedAdapter:
    """基于规则的UI适配器 - 统一处理AIForge核心数据结构，返回语义化数据格式"""

    def __init__(self):
        self.task_type_detector = TaskTypeDetector()
        self.ui_type_recommender = UITypeRecommender()

        # 统一的语义化UI模板定义
        self.ui_templates = {
            # 数据获取任务
            "data_fetch": {
                "card": {
                    "primary_field": "title",
                    "secondary_fields": ["content", "source", "date"],
                    "max_items": None,
                    "respect_user_requirements": True,
                    "data_structure": "key_value",
                    "capabilities": ["expandable", "searchable"],
                },
                "table": {
                    "columns": ["title", "content", "source", "date"],
                    "max_content_length": 200,
                    "sortable": ["date", "title"],
                    "searchable": True,
                    "data_structure": "tabular",
                    "capabilities": ["sortable", "filterable", "exportable"],
                },
                "map": {
                    "location_field": "location",
                    "coordinate_fields": ["lat", "lng", "latitude", "longitude"],
                    "info_fields": ["title", "address", "description"],
                    "data_structure": "geospatial",
                    "capabilities": ["zoomable", "interactive"],
                },
                "list": {
                    "title_field": "title",
                    "subtitle_field": "source",
                    "detail_fields": ["content", "date"],
                    "data_structure": "hierarchical",
                    "capabilities": ["scrollable", "selectable"],
                },
                "text": {
                    "format": "simple_text",
                    "fields": ["title", "content", "source"],
                    "data_structure": "plain_text",
                    "capabilities": ["copyable", "exportable"],
                },
            },
            # 数据分析任务
            "data_analysis": {
                "dashboard": {
                    "metrics_field": "metrics",
                    "charts_field": "charts",
                    "sections": ["overview", "details", "trends"],
                    "data_structure": "multi_section",
                    "capabilities": ["interactive", "refreshable", "drilldown"],
                },
                "chart": {
                    "data_field": "chart_data",
                    "chart_type": "auto",
                    "x_axis": "category",
                    "y_axis": "value",
                    "data_structure": "numerical",
                    "capabilities": ["interactive", "exportable", "type_switchable"],
                },
                "table": {
                    "columns": ["metric", "value", "change", "status"],
                    "max_content_length": 150,
                    "sortable": ["value", "change"],
                    "data_structure": "tabular",
                    "capabilities": ["sortable", "filterable"],
                },
                "timeline": {
                    "step_field": "analysis_steps",
                    "time_field": "timestamp",
                    "data_structure": "temporal",
                    "capabilities": ["chronological", "expandable"],
                },
                "card": {
                    "primary_field": "summary",
                    "secondary_fields": ["total", "average", "trend"],
                    "data_structure": "summary",
                    "capabilities": ["expandable"],
                },
            },
            # 文件操作任务
            "file_operation": {
                "table": {
                    "columns": ["filename", "status", "size", "operation"],
                    "max_content_length": 100,
                    "sortable": ["filename", "size"],
                    "data_structure": "file_listing",
                    "capabilities": ["sortable", "filterable", "batch_operations"],
                },
                "progress": {
                    "total_field": "total_files",
                    "completed_field": "processed_files",
                    "status_field": "status",
                    "data_structure": "progress_tracking",
                    "capabilities": ["real_time", "cancellable"],
                },
                "timeline": {
                    "step_field": "operations",
                    "status_field": "status",
                    "data_structure": "operation_log",
                    "capabilities": ["chronological", "retryable"],
                },
                "list": {
                    "title_field": "filename",
                    "subtitle_field": "status",
                    "detail_fields": ["size", "operation"],
                    "data_structure": "file_listing",
                    "capabilities": ["selectable", "batch_operations"],
                },
            },
            # 内容生成任务
            "content_generation": {
                "editor": {
                    "content_field": "generated_content",
                    "metadata_fields": ["title", "summary", "word_count"],
                    "editable": True,
                    "syntax_highlighting": True,
                    "data_structure": "long_text",
                    "capabilities": ["editable", "copyable", "downloadable", "regeneratable"],
                },
                "card": {
                    "primary_field": "content",
                    "secondary_fields": ["title", "summary"],
                    "data_structure": "text_summary",
                    "capabilities": ["copyable", "expandable"],
                },
            },
            # 代码生成任务
            "code_generation": {
                "editor": {
                    "content_field": "generated_code",
                    "metadata_fields": ["language", "description", "lines"],
                    "editable": True,
                    "syntax_highlighting": True,
                    "data_structure": "source_code",
                    "capabilities": [
                        "editable",
                        "syntax_highlighted",
                        "copyable",
                        "downloadable",
                        "executable",
                    ],
                },
                "card": {
                    "primary_field": "code",
                    "secondary_fields": ["language", "description"],
                    "data_structure": "code_summary",
                    "capabilities": ["copyable", "syntax_highlighted"],
                },
            },
            # 数据处理任务
            "data_process": {
                "table": {
                    "columns": ["item", "status", "result", "timestamp"],
                    "max_content_length": 200,
                    "sortable": ["timestamp", "status"],
                    "data_structure": "processing_log",
                    "capabilities": ["sortable", "filterable", "exportable"],
                },
                "dashboard": {
                    "metrics_field": "processing_stats",
                    "sections": ["summary", "details", "errors"],
                    "data_structure": "processing_metrics",
                    "capabilities": ["real_time", "drilldown"],
                },
                "card": {
                    "primary_field": "summary",
                    "secondary_fields": ["total_processed", "success_rate"],
                    "data_structure": "processing_summary",
                    "capabilities": ["refreshable"],
                },
            },
            # 自动化任务
            "automation": {
                "timeline": {
                    "step_field": "automation_steps",
                    "status_field": "step_status",
                    "time_field": "execution_time",
                    "data_structure": "workflow",
                    "capabilities": ["chronological", "retryable", "pausable"],
                },
                "calendar": {
                    "event_field": "scheduled_tasks",
                    "date_field": "schedule_date",
                    "time_field": "schedule_time",
                    "data_structure": "scheduled_events",
                    "capabilities": ["schedulable", "recurring", "editable"],
                },
                "progress": {
                    "total_field": "total_tasks",
                    "completed_field": "completed_tasks",
                    "status_field": "automation_status",
                    "data_structure": "task_progress",
                    "capabilities": ["real_time", "cancellable"],
                },
                "card": {
                    "primary_field": "automation_summary",
                    "secondary_fields": ["status", "next_run"],
                    "data_structure": "automation_status",
                    "capabilities": ["controllable"],
                },
            },
            # 直接响应任务
            "direct_response": {
                "card": {
                    "primary_field": "response",
                    "secondary_fields": ["source", "confidence"],
                    "data_structure": "qa_response",
                    "capabilities": ["copyable", "citable"],
                },
                "editor": {
                    "content_field": "detailed_response",
                    "metadata_fields": ["topic", "references"],
                    "editable": False,
                    "data_structure": "detailed_text",
                    "capabilities": ["copyable", "citable", "referenceable"],
                },
                "text": {
                    "format": "simple_text",
                    "fields": ["response"],
                    "data_structure": "plain_text",
                    "capabilities": ["copyable"],
                },
            },
            # 搜索任务
            "search": {
                "table": {
                    "columns": ["title", "snippet", "source", "relevance"],
                    "max_content_length": 300,
                    "sortable": ["relevance", "title"],
                    "searchable": True,
                    "data_structure": "search_results",
                    "capabilities": ["sortable", "filterable", "linkable"],
                },
                "card": {
                    "primary_field": "title",
                    "secondary_fields": ["snippet", "source", "url"],
                    "data_structure": "search_results",
                    "capabilities": ["linkable", "expandable"],
                },
                "list": {
                    "title_field": "title",
                    "subtitle_field": "source",
                    "detail_fields": ["snippet", "url"],
                    "data_structure": "search_results",
                    "capabilities": ["linkable", "selectable"],
                },
            },
            # 图像处理任务
            "image_processing": {
                "gallery": {
                    "image_field": "processed_images",
                    "thumbnail_field": "thumbnails",
                    "metadata_fields": ["filename", "size", "format"],
                    "data_structure": "image_collection",
                    "capabilities": ["zoomable", "downloadable", "slideshow"],
                },
                "card": {
                    "primary_field": "image_info",
                    "secondary_fields": ["dimensions", "format", "size"],
                    "data_structure": "image_metadata",
                    "capabilities": ["previewable"],
                },
                "dashboard": {
                    "metrics_field": "processing_stats",
                    "sections": ["images", "analysis", "results"],
                    "data_structure": "image_analytics",
                    "capabilities": ["analytical", "comparative"],
                },
            },
            # API集成任务
            "api_integration": {
                "table": {
                    "columns": ["endpoint", "method", "status", "response_time"],
                    "max_content_length": 150,
                    "sortable": ["status", "response_time"],
                    "data_structure": "api_logs",
                    "capabilities": ["sortable", "filterable", "retryable"],
                },
                "card": {
                    "primary_field": "api_summary",
                    "secondary_fields": ["status", "data_count", "errors"],
                    "data_structure": "api_summary",
                    "capabilities": ["refreshable", "retryable"],
                },
                "dashboard": {
                    "metrics_field": "api_metrics",
                    "sections": ["overview", "performance", "errors"],
                    "data_structure": "api_analytics",
                    "capabilities": ["real_time", "alerting"],
                },
            },
            # 通用任务
            "general": {
                "card": {
                    "primary_field": "content",
                    "secondary_fields": ["status", "summary"],
                    "data_structure": "generic",
                    "capabilities": ["basic"],
                },
            },
        }

    def can_handle(self, task_type: str, ui_type: str) -> bool:
        """检查是否能处理指定的任务类型和UI类型"""
        return (
            task_type in self.ui_templates and ui_type in self.ui_templates[task_type]
        ) or task_type == "general"

    def adapt(self, result_dict: Dict[str, Any], task_type: str, ui_type: str) -> Dict[str, Any]:
        """统一适配入口

        Args:
            result_dict: 完整的AIForgeResult字典格式
        """
        # 格式验证失败时使用基本回退，不抛异常
        if not AIForgeResult.is_valid_format(result_dict):
            # 保留原始metadata，只添加转换标记
            if isinstance(result_dict, dict) and result_dict.get("metadata"):
                metadata = result_dict["metadata"].copy()
                metadata["format_converted"] = True
            else:
                metadata = {"format_converted": True}

            result_dict = {
                "task_type": task_type,
                "ui_type": ui_type,
                "data": (
                    result_dict.get("data", result_dict)
                    if isinstance(result_dict, dict)
                    else {"content": str(result_dict)}
                ),
                "status": "success",
                "summary": (
                    result_dict.get("summary", "数据处理完成")
                    if isinstance(result_dict, dict)
                    else "数据处理完成"
                ),
                "metadata": metadata,
            }

        # 使用 AIForgeResult 中的 task_type
        actual_task_type = result_dict.get("task_type") or task_type

        # 选择适配方法
        adapter_methods = {
            "table": self._adapt_to_table,
            "card": self._adapt_to_card,
            "dashboard": self._adapt_to_dashboard,
            "progress": self._adapt_to_progress,
            "timeline": self._adapt_to_timeline,
            "editor": self._adapt_to_editor,
            "map": self._adapt_to_map,
            "chart": self._adapt_to_chart,
            "gallery": self._adapt_to_gallery,
            "calendar": self._adapt_to_calendar,
            "list": self._adapt_to_list,
            "text": self._adapt_to_text,
        }

        # 获取模板
        template = self._get_template(actual_task_type, ui_type)

        # 执行适配 - 传递完整的 result_dict
        adapter_method = adapter_methods.get(ui_type, self._adapt_generic)
        return adapter_method(result_dict, template)

    def _get_template(self, task_type: str, ui_type: str) -> Dict[str, Any]:
        """获取适配模板"""
        if task_type in self.ui_templates and ui_type in self.ui_templates[task_type]:
            return self.ui_templates[task_type][ui_type]
        elif ui_type in self.ui_templates.get("general", {}):
            return self.ui_templates["general"][ui_type]
        else:
            return {}

    def get_supported_combinations(self) -> Dict[str, List[str]]:
        """获取所有支持的任务类型和UI类型组合"""
        combinations = {}
        for task_type, ui_types in self.ui_templates.items():
            combinations[task_type] = list(ui_types.keys())
        return combinations

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
        capabilities = template.get("capabilities", ["expandable"])
        data_structure = template.get("data_structure", "key_value")

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
                        "type": "card",  # 语义化基础类型
                        "semantic_role": "search_result",
                        "data_structure": data_structure,
                        "title": title,
                        "content": {
                            "primary": title,
                            "secondary": {"content": content, "source": source, "date": date},
                        },
                        "capabilities": capabilities,
                        "priority": 10 - i,
                    }
                )

        return {
            "display_items": display_items,
            "layout_hints": {
                "primary_layout": "vertical_list",
                "content_type": "search_results",
                "interaction_level": "medium",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "compact",
            },
            "actions": [
                {"label": "查看更多", "action": "expand", "data": {"total": len(results)}},
                {"label": "新搜索", "action": "search", "data": {}},
            ],
            "summary_text": data.get("summary", f"搜索结果: {len(results)} 条"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "search_results",
                "structure": "card_list",
            },
        }

    def _adapt_default_card(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """默认卡片格式"""
        primary_field = template.get("primary_field", "content")
        secondary_fields = template.get("secondary_fields", [])
        capabilities = template.get("capabilities", ["basic"])
        data_structure = template.get("data_structure", "key_value")

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
                    "type": "card",  # 语义化基础类型
                    "semantic_role": "data_summary",
                    "data_structure": data_structure,
                    "title": "处理结果",
                    "content": {"primary": primary_content, "secondary": secondary_content},
                    "capabilities": capabilities,
                    "priority": 8,
                }
            ],
            "layout_hints": {
                "primary_layout": "single_item",
                "content_type": "summary_data",
                "interaction_level": "low",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "normal",
            },
            "actions": [{"label": "详情", "action": "detail", "data": data}],
            "summary_text": data.get("summary", "数据卡片视图"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "summary_card",
                "structure": "single_card",
            },
        }

    def _adapt_to_table(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为表格格式"""
        columns = template.get("columns", [])
        max_content_length = template.get("max_content_length", 200)
        capabilities = template.get("capabilities", ["sortable", "filterable"])
        data_structure = template.get("data_structure", "tabular")

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
                    "type": "table",  # 语义化基础类型
                    "semantic_role": "data_listing",
                    "data_structure": data_structure,
                    "title": "数据表格",
                    "content": {
                        "columns": columns,
                        "rows": processed_items,
                        "sortable": template.get("sortable", []),
                        "searchable": template.get("searchable", False),
                        "pagination": len(processed_items) > 50,
                    },
                    "capabilities": capabilities,
                    "priority": 9,
                }
            ],
            "layout_hints": {
                "primary_layout": "tabular",
                "content_type": "structured_data",
                "interaction_level": "high",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "normal",
            },
            "actions": [
                {"label": "导出", "action": "export", "data": {"format": "csv"}},
                {"label": "刷新", "action": "refresh", "data": {}},
                {"label": "筛选", "action": "filter", "data": {"columns": columns}},
            ],
            "summary_text": data.get("summary", f"共 {len(processed_items)} 条记录"),
            "metadata": data.get("metadata", {}),
            "data_schema": {"version": "1.0", "content_type": "tabular_data", "structure": "table"},
        }

    def _adapt_to_dashboard(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为仪表板格式"""
        capabilities = template.get("capabilities", ["interactive", "refreshable"])
        data_structure = template.get("data_structure", "multi_section")
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
                    "type": "dashboard",  # 语义化基础类型
                    "semantic_role": "analytics_overview",
                    "data_structure": data_structure,
                    "title": "数据仪表板",
                    "content": {"stats": stats, "charts": [], "summary": data.get("summary", "")},
                    "capabilities": capabilities,
                    "priority": 7,
                }
            ],
            "layout_hints": {
                "primary_layout": "grid",
                "content_type": "analytics_data",
                "interaction_level": "high",
                "layout_type": "grid",
                "columns": 2,
                "spacing": "wide",
            },
            "actions": [{"label": "刷新", "action": "refresh", "data": {}}],
            "summary_text": data.get("summary", "仪表板视图"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "dashboard",
                "structure": "multi_widget",
            },
        }

    def _adapt_to_progress(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为进度显示格式"""
        progress_field = template.get("progress_field", "success_count")
        total_field = template.get("total_field", "total_files")
        capabilities = template.get("capabilities", ["real_time", "cancellable"])
        data_structure = template.get("data_structure", "progress_tracking")

        # 从数据或元数据中获取进度信息
        metadata = data.get("metadata", {})
        progress = data.get(progress_field, metadata.get(progress_field, 0))
        total = data.get(total_field, metadata.get(total_field, len(data.get("data", []))))
        percentage = (progress / total * 100) if total > 0 else 0

        return {
            "display_items": [
                {
                    "type": "progress",  # 语义化基础类型
                    "semantic_role": "task_progress",
                    "data_structure": data_structure,
                    "title": "处理进度",
                    "content": {
                        "current": progress,
                        "total": total,
                        "percentage": percentage,
                        "status": data.get("status", "processing"),
                    },
                    "capabilities": capabilities,
                    "priority": 9,
                }
            ],
            "layout_hints": {
                "primary_layout": "progress_bar",
                "content_type": "progress_data",
                "interaction_level": "medium",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "compact",
            },
            "actions": [
                {"label": "查看详情", "action": "detail", "data": data},
                {"label": "停止处理", "action": "stop", "data": {}},
            ],
            "summary_text": data.get("summary", f"进度: {progress}/{total} ({percentage:.1f}%)"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "progress_tracking",
                "structure": "progress_indicator",
            },
        }

    def _adapt_to_timeline(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为时间线格式"""
        step_field = template.get("step_field", "executed_steps")
        capabilities = template.get("capabilities", ["chronological", "expandable"])
        data_structure = template.get("data_structure", "temporal")

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
                    "type": "timeline",  # 语义化基础类型
                    "semantic_role": "process_flow",
                    "data_structure": data_structure,
                    "title": "执行时间线",
                    "content": {"items": timeline_items},
                    "capabilities": capabilities,
                    "priority": 8,
                }
            ],
            "layout_hints": {
                "primary_layout": "chronological",
                "content_type": "process_data",
                "interaction_level": "medium",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "normal",
            },
            "actions": [{"label": "重新执行", "action": "retry", "data": data}],
            "summary_text": data.get("summary", f"已完成 {len(steps)} 个步骤"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "timeline",
                "structure": "chronological_steps",
            },
        }

    def _adapt_to_editor(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为编辑器格式"""
        content_field = template.get("content_field", "generated_content")
        metadata_fields = template.get("metadata_fields", [])
        capabilities = template.get("capabilities", ["editable", "copyable", "downloadable"])
        data_structure = template.get("data_structure", "long_text")

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

        # 根据任务类型和内容类型确定格式
        if template.get("syntax_highlighting"):
            # 检查是否为代码生成任务
            task_type = data.get("task_type", "")
            if task_type == "code_generation":
                # 可以从元数据中获取具体的编程语言
                language = data.get("metadata", {}).get("language", "python")
                content_format = language
            else:
                # 内容生成任务使用 markdown
                content_format = "markdown"
        else:
            content_format = "plain"

        return {
            "display_items": [
                {
                    "type": "editor",  # 语义化基础类型
                    "semantic_role": "content_output",
                    "data_structure": data_structure,
                    "title": "生成的内容",
                    "content": {
                        "text": content,
                        "format": content_format,
                        "metadata": metadata,
                        "editable": template.get("editable", False),
                    },
                    "capabilities": capabilities,
                    "priority": 9,
                }
            ],
            "layout_hints": {
                "primary_layout": "single_item",
                "content_type": "text_content",
                "interaction_level": "high",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "normal",
            },
            "actions": [
                {"label": "保存", "action": "save", "data": {"content": content}},
                {"label": "导出", "action": "export", "data": {"format": "txt"}},
                {"label": "重新生成", "action": "regenerate", "data": {}},
            ],
            "summary_text": data.get("summary", f"内容长度: {len(content)} 字符"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "generated_content",
                "structure": "editor_compatible",
            },
        }

    def _adapt_to_text(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为终端文本格式"""
        format_type = template.get("format", "simple_text")
        fields = template.get("fields", [])
        capabilities = template.get("capabilities", ["copyable", "exportable"])
        data_structure = template.get("data_structure", "plain_text")

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
                    "type": "text",  # 语义化基础类型
                    "semantic_role": "terminal_output",
                    "data_structure": data_structure,
                    "title": "文本输出",
                    "content": {"text": text_content, "format": "plain", "monospace": True},
                    "capabilities": capabilities,
                    "priority": 7,
                }
            ],
            "layout_hints": {
                "primary_layout": "monospace",
                "content_type": "terminal_data",
                "interaction_level": "low",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "normal",
            },
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
            "data_schema": {
                "version": "1.0",
                "content_type": "terminal_text",
                "structure": "plain_text",
            },
        }

    def _adapt_to_list(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为移动端列表格式"""
        title_field = template.get("title_field", "title")
        subtitle_field = template.get("subtitle_field", "source")
        detail_fields = template.get("detail_fields", [])
        capabilities = template.get("capabilities", ["scrollable", "selectable"])
        data_structure = template.get("data_structure", "hierarchical")

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
                    "type": "list",  # 语义化基础类型
                    "semantic_role": "item_listing",
                    "data_structure": data_structure,
                    "title": "列表视图",
                    "content": {
                        "items": list_items,
                        "layout": "vertical",
                        "item_spacing": "compact",
                    },
                    "capabilities": capabilities,
                    "priority": 8,
                }
            ],
            "layout_hints": {
                "primary_layout": "list",
                "content_type": "item_data",
                "interaction_level": "medium",
                "layout_type": "list",
                "columns": 1,
                "spacing": "compact",
            },
            "actions": [
                {"label": "刷新", "action": "refresh", "data": {}},
                {"label": "查看详情", "action": "detail", "data": data},
            ],
            "summary_text": data.get("summary", f"共 {len(list_items)} 个项目"),
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "item_list",
                "structure": "hierarchical_list",
            },
        }

    def _adapt_generic(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """通用适配方法"""
        capabilities = template.get("capabilities", ["basic"])
        data_structure = template.get("data_structure", "generic")

        return {
            "display_items": [
                {
                    "type": "generic",  # 语义化基础类型
                    "semantic_role": "fallback_display",
                    "data_structure": data_structure,
                    "title": "数据视图",
                    "content": {
                        "data": data.get("data", []),
                        "summary": data.get("summary", ""),
                        "status": data.get("status", ""),
                    },
                    "capabilities": capabilities,
                    "priority": 5,
                }
            ],
            "layout_hints": {
                "primary_layout": "simple",
                "content_type": "generic_data",
                "interaction_level": "low",
                "layout_type": "vertical",
                "columns": 1,
                "spacing": "normal",
            },
            "actions": [],
            "summary_text": data.get("summary", "通用数据视图"),
            "metadata": data.get("metadata", {}),
            "data_schema": {"version": "1.0", "content_type": "generic", "structure": "fallback"},
        }

    def _adapt_to_map(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为地图格式"""
        coordinate_fields = template.get("coordinate_fields", ["lat", "lng"])
        info_fields = template.get("info_fields", ["title", "description"])
        capabilities = template.get("capabilities", ["zoomable", "interactive"])
        data_structure = template.get("data_structure", "geospatial")

        data_items = data.get("data", [])
        map_items = []

        for item in data_items:
            if isinstance(item, dict):
                # 提取坐标信息
                coordinates = {}
                for coord_field in coordinate_fields:
                    if coord_field in item:
                        coordinates[coord_field] = item[coord_field]

                # 提取信息字段
                info = {field: item.get(field, "") for field in info_fields if field in item}

                if coordinates:
                    map_items.append(
                        {
                            "type": "map_marker",  # 语义化基础类型
                            "semantic_role": "location_point",
                            "data_structure": data_structure,
                            "coordinates": coordinates,
                            "info": info,
                            "capabilities": capabilities,
                            "priority": 8,
                        }
                    )

        return {
            "display_items": map_items,
            "layout_hints": {
                "primary_layout": "geospatial",
                "content_type": "location_data",
                "interaction_level": "high",
                "layout_type": "map",
                "center": "auto",
                "zoom": "auto",
            },
            "actions": [
                {"label": "重新定位", "action": "recenter", "data": {}},
                {"label": "切换图层", "action": "toggle_layer", "data": {}},
            ],
            "summary_text": f"地图显示 {len(map_items)} 个位置",
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "geospatial_data",
                "structure": "map_markers",
            },
        }

    def _adapt_to_chart(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为图表格式"""
        data_field = template.get("data_field", "chart_data")
        chart_type = template.get("chart_type", "auto")
        x_axis = template.get("x_axis", "category")
        y_axis = template.get("y_axis", "value")
        capabilities = template.get("capabilities", ["interactive", "exportable"])
        data_structure = template.get("data_structure", "numerical")

        chart_data = data.get(data_field, data.get("data", []))

        # 自动检测图表类型
        if chart_type == "auto":
            if isinstance(chart_data, list) and chart_data:
                if all(isinstance(item, dict) and len(item) == 2 for item in chart_data):
                    chart_type = "line"
                elif any(
                    isinstance(v, (int, float))
                    for item in chart_data
                    for v in item.values()
                    if isinstance(item, dict)
                ):
                    chart_type = "bar"
                else:
                    chart_type = "pie"

        return {
            "display_items": [
                {
                    "type": "chart",  # 语义化基础类型
                    "semantic_role": "data_visualization",
                    "data_structure": data_structure,
                    "chart_type": chart_type,
                    "data": chart_data,
                    "config": {"x_axis": x_axis, "y_axis": y_axis, "responsive": True},
                    "capabilities": capabilities,
                    "priority": 9,
                }
            ],
            "layout_hints": {
                "primary_layout": "visualization",
                "content_type": "chart_data",
                "interaction_level": "high",
                "layout_type": "single",
                "aspect_ratio": "16:9",
            },
            "actions": [
                {"label": "切换图表类型", "action": "change_chart_type", "data": {}},
                {"label": "导出图表", "action": "export_chart", "data": {}},
            ],
            "summary_text": f"{chart_type.title()} 图表",
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "chart_visualization",
                "structure": "chart_data",
            },
        }

    def _adapt_to_gallery(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为画廊格式"""
        image_field = template.get("image_field", "images")
        thumbnail_field = template.get("thumbnail_field", "thumbnails")
        metadata_fields = template.get("metadata_fields", ["filename", "size"])
        capabilities = template.get("capabilities", ["zoomable", "downloadable"])
        data_structure = template.get("data_structure", "image_collection")

        images = data.get(image_field, data.get("data", []))
        gallery_items = []

        for i, image in enumerate(images):
            if isinstance(image, dict):
                item = {
                    "type": "gallery_item",  # 语义化基础类型
                    "semantic_role": "image_display",
                    "data_structure": data_structure,
                    "image_url": image.get("url", image.get("path", "")),
                    "thumbnail_url": image.get(thumbnail_field, image.get("thumbnail", "")),
                    "metadata": {field: image.get(field, "") for field in metadata_fields},
                    "capabilities": capabilities,
                    "priority": 10 - i,
                }
                gallery_items.append(item)

        return {
            "display_items": gallery_items,
            "layout_hints": {
                "primary_layout": "grid",
                "content_type": "image_data",
                "interaction_level": "high",
                "layout_type": "grid",
                "columns": 3,
                "spacing": "normal",
            },
            "actions": [
                {"label": "幻灯片模式", "action": "slideshow", "data": {}},
                {"label": "下载全部", "action": "download_all", "data": {}},
            ],
            "summary_text": f"图片库 {len(gallery_items)} 张图片",
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "image_gallery",
                "structure": "image_grid",
            },
        }

    def _adapt_to_calendar(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为日历格式"""
        event_field = template.get("event_field", "events")
        date_field = template.get("date_field", "date")
        time_field = template.get("time_field", "time")
        capabilities = template.get("capabilities", ["schedulable", "editable"])
        data_structure = template.get("data_structure", "scheduled_events")

        events = data.get(event_field, data.get("data", []))
        calendar_events = []

        for event in events:
            if isinstance(event, dict):
                calendar_events.append(
                    {
                        "type": "calendar_event",  # 语义化基础类型
                        "semantic_role": "scheduled_item",
                        "data_structure": data_structure,
                        "title": event.get("title", "事件"),
                        "date": event.get(date_field, ""),
                        "time": event.get(time_field, ""),
                        "description": event.get("description", ""),
                        "capabilities": capabilities,
                        "priority": 8,
                    }
                )

        return {
            "display_items": calendar_events,
            "layout_hints": {
                "primary_layout": "calendar",
                "content_type": "schedule_data",
                "interaction_level": "high",
                "layout_type": "calendar",
                "view": "month",
            },
            "actions": [
                {"label": "切换视图", "action": "change_view", "data": {}},
                {"label": "添加事件", "action": "add_event", "data": {}},
            ],
            "summary_text": f"日历显示 {len(calendar_events)} 个事件",
            "metadata": data.get("metadata", {}),
            "data_schema": {
                "version": "1.0",
                "content_type": "calendar_events",
                "structure": "event_schedule",
            },
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
