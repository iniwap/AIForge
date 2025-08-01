from typing import Dict, Any, List


class RuleBasedAdapter:
    """基于规则的UI适配器"""

    def __init__(self):
        # UI模板定义
        self.ui_templates = {
            "data_fetch": {
                "web_card": {
                    "primary_field": "content",
                    "secondary_fields": ["source", "location", "timestamp"],
                    "layout": "vertical",
                    "display_format": "key_value",
                },
                "web_table": {
                    "columns": ["content", "source", "timestamp"],
                    "sortable": ["timestamp"],
                    "searchable": False,
                },
                "mobile_list": {
                    "title_field": "content",
                    "subtitle_field": "source",
                    "detail_fields": ["timestamp", "location"],
                },
                "terminal_text": {"format": "simple_text", "fields": ["content", "source"]},
            },
            "data_analysis": {
                "web_dashboard": {
                    "sections": ["analysis", "summary", "visualizations"],
                    "layout": "grid",
                    "columns": 2,
                },
                "web_card": {
                    "primary_field": "key_findings",
                    "secondary_fields": ["total_records", "trends"],
                    "layout": "vertical",
                    "display_format": "analysis_summary",
                },
                "web_table": {
                    "columns": ["metric", "value", "trend"],
                    "sortable": ["value"],
                    "searchable": False,
                },
                "terminal_text": {
                    "format": "structured_report",
                    "fields": ["key_findings", "summary"],
                },
            },
            "file_operation": {
                "web_table": {
                    "columns": ["file", "status", "size", "operation"],
                    "sortable": ["file", "status", "size"],
                    "searchable": True,
                },
                "web_progress": {
                    "progress_field": "success_count",
                    "total_field": "total_files",
                    "error_field": "errors",
                },
                "mobile_list": {
                    "title_field": "file",
                    "subtitle_field": "status",
                    "detail_fields": ["size", "operation"],
                },
                "terminal_text": {
                    "format": "progress_report",
                    "fields": ["total_files", "success_count", "error_count"],
                },
            },
            "api_call": {
                "web_card": {
                    "primary_field": "endpoint",
                    "secondary_fields": ["status_code", "response_time"],
                    "layout": "horizontal",
                    "display_format": "api_status",
                },
                "web_table": {
                    "columns": ["endpoint", "status_code", "response_time", "success"],
                    "sortable": ["response_time", "status_code"],
                    "searchable": True,
                },
                "terminal_text": {
                    "format": "api_summary",
                    "fields": ["endpoint", "status_code", "success"],
                },
            },
            "automation": {
                "web_timeline": {
                    "step_field": "executed_steps",
                    "layout": "vertical",
                },
                "web_card": {
                    "primary_field": "workflow",
                    "secondary_fields": ["total_steps", "success_steps"],
                    "layout": "vertical",
                    "display_format": "workflow_status",
                },
                "terminal_text": {
                    "format": "step_by_step",
                    "fields": ["executed_steps", "results"],
                },
            },
            "content_generation": {
                "web_editor": {
                    "content_field": "generated_content",
                    "metadata_fields": ["content_type", "word_count"],
                    "editable": True,
                },
                "web_card": {
                    "primary_field": "generated_content",
                    "secondary_fields": ["content_type", "word_count"],
                    "layout": "vertical",
                    "display_format": "content_preview",
                },
                "terminal_text": {
                    "format": "content_summary",
                    "fields": ["content_type", "word_count"],
                },
            },
        }

    def can_handle(self, task_type: str, ui_type: str) -> bool:
        """检查是否可以处理特定的任务类型和UI类型"""
        return task_type in self.ui_templates and ui_type in self.ui_templates[task_type]

    def get_supported_combinations(self) -> Dict[str, List[str]]:
        """获取所有支持的任务类型和UI类型组合"""
        return {
            task_type: list(ui_types.keys()) for task_type, ui_types in self.ui_templates.items()
        }

    def adapt(self, data: Dict[str, Any], task_type: str, ui_type: str) -> Dict[str, Any]:
        """基于规则适配数据"""
        if not self.can_handle(task_type, ui_type):
            return self._adapt_generic(data, {})

        template = self.ui_templates[task_type][ui_type]

        # 根据UI类型选择适配方法
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

        adapter_method = adapter_methods.get(ui_type, self._adapt_generic)
        return adapter_method(data, template)

    def _adapt_to_dashboard(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为仪表板格式"""
        sections = template.get("sections", ["analysis"])
        columns = template.get("columns", 2)

        display_items = []
        for i, section in enumerate(sections):
            if section in data:
                display_items.append(
                    {
                        "type": "section",
                        "title": section.title(),
                        "content": data[section],
                        "priority": 10 - i,
                        "grid_position": {"row": i // columns, "col": i % columns},
                    }
                )

        return {
            "display_items": display_items,
            "layout_hints": {"layout_type": "grid", "columns": columns, "spacing": "normal"},
            "actions": [
                {"label": "导出报告", "action": "export", "data": {"format": "pdf"}},
                {"label": "刷新数据", "action": "refresh", "data": {}},
            ],
            "summary_text": f"数据分析仪表板 - {len(display_items)} 个部分",
        }

    def _adapt_to_progress(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为进度显示格式"""
        progress_field = template.get("progress_field", "success_count")
        total_field = template.get("total_field", "total_files")

        progress = data.get(progress_field, 0)
        total = data.get(total_field, 1)
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
                    },
                    "priority": 9,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "compact"},
            "actions": [
                {"label": "查看详情", "action": "detail", "data": data},
                {"label": "停止处理", "action": "stop", "data": {}},
            ],
            "summary_text": f"进度: {progress}/{total} ({percentage:.1f}%)",
        }

    def _adapt_to_timeline(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为时间线格式"""
        step_field = template.get("step_field", "executed_steps")
        steps = data.get(step_field, [])

        timeline_items = []
        for i, step in enumerate(steps):
            timeline_items.append(
                {
                    "step": i + 1,
                    "title": step if isinstance(step, str) else str(step),
                    "status": "completed",
                    "timestamp": f"Step {i + 1}",
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
            "summary_text": f"已完成 {len(steps)} 个步骤",
        }

    def _adapt_to_editor(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为编辑器格式"""
        content_field = template.get("content_field", "generated_content")
        metadata_fields = template.get("metadata_fields", [])

        content = data.get(content_field, "")
        metadata = {field: data.get(field, "") for field in metadata_fields}

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
            "summary_text": f"内容长度: {len(content)} 字符",
        }

    # 保留原有的适配方法，但增强功能
    def _adapt_to_table(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为表格格式"""
        columns = template.get("columns", [])
        max_content_length = template.get("max_content_length", 200)

        # 处理不同的数据结构
        if "results" in data:
            items = data["results"]
        elif "processed_files" in data:
            items = data["processed_files"]
        elif "response_data" in data:
            items = (
                [data["response_data"]]
                if not isinstance(data["response_data"], list)
                else data["response_data"]
            )
        else:
            items = [data] if not isinstance(data, list) else data

        # 截断过长的内容
        processed_items = []
        for item in items:
            processed_item = {}
            for col in columns:
                value = item.get(col, "")
                if isinstance(value, str) and len(value) > max_content_length:
                    value = value[:max_content_length] + "..."
                processed_item[col] = value
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
                    "priority": 8,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [
                {"label": "导出", "action": "export", "data": {"format": "csv"}},
                {"label": "刷新", "action": "refresh", "data": {}},
                {"label": "筛选", "action": "filter", "data": {"columns": columns}},
            ],
            "summary_text": f"共 {len(processed_items)} 条记录",
        }

    def _adapt_to_card(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """适配为卡片格式"""
        # primary_field = template.get("primary_field", "content")
        # secondary_fields = template.get("secondary_fields", [])
        display_format = template.get("display_format", "default")

        # 根据显示格式调整内容
        if display_format == "search_result":
            return self._adapt_search_result_card(data, template)
        elif display_format == "analysis_summary":
            return self._adapt_analysis_card(data, template)
        elif display_format == "api_status":
            return self._adapt_api_status_card(data, template)
        else:
            return self._adapt_default_card(data, template)

    def _adapt_search_result_card(
        self, data: Dict[str, Any], template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """搜索结果卡片格式"""
        results = data.get("results", [data])

        display_items = []
        for i, result in enumerate(results[:5]):  # 限制显示前5个结果
            display_items.append(
                {
                    "type": "card",
                    "title": result.get("title", f"结果 {i+1}"),
                    "content": {
                        "primary": result.get("title", ""),
                        "secondary": {
                            "url": result.get("url", ""),
                            "content": (
                                result.get("content", "")[:150] + "..."
                                if len(result.get("content", "")) > 150
                                else result.get("content", "")
                            ),
                        },
                    },
                    "priority": 9 - i,
                }
            )

        return {
            "display_items": display_items,
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "compact"},
            "actions": [
                {"label": "查看更多", "action": "expand", "data": {"total": len(results)}},
                {"label": "新搜索", "action": "search", "data": {}},
            ],
            "summary_text": f"搜索结果: {len(results)} 条",
        }

    def _adapt_analysis_card(
        self, data: Dict[str, Any], template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """数据分析卡片格式"""
        analysis = data.get("analysis", {})

        return {
            "display_items": [
                {
                    "type": "card",
                    "title": "分析摘要",
                    "content": {
                        "primary": analysis.get("key_findings", "无关键发现"),
                        "secondary": {
                            "记录数": data.get("summary", {}).get("total_records", 0),
                            "趋势": analysis.get("trends", "无明显趋势"),
                            "置信度": analysis.get("confidence", "中等"),
                        },
                    },
                    "priority": 9,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [
                {"label": "详细报告", "action": "detail", "data": data},
                {"label": "导出分析", "action": "export", "data": {"format": "pdf"}},
            ],
            "summary_text": "数据分析完成",
        }

    def _adapt_api_status_card(
        self, data: Dict[str, Any], template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """API状态卡片格式"""
        status_code = data.get("status_code", 0)
        is_success = 200 <= status_code < 300

        return {
            "display_items": [
                {
                    "type": "card",
                    "title": "API调用状态",
                    "content": {
                        "primary": data.get("endpoint", "未知端点"),
                        "secondary": {
                            "状态码": status_code,
                            "响应时间": f"{data.get('response_time', 0):.2f}ms",
                            "状态": "成功" if is_success else "失败",
                        },
                    },
                    "priority": 9,
                    "status": "success" if is_success else "error",
                }
            ],
            "layout_hints": {"layout_type": "horizontal", "columns": 2, "spacing": "compact"},
            "actions": [
                {"label": "重试", "action": "retry", "data": {"endpoint": data.get("endpoint")}},
                {"label": "查看响应", "action": "detail", "data": data},
            ],
            "summary_text": f"API调用{'成功' if is_success else '失败'}",
        }

    def _adapt_default_card(self, data: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """默认卡片格式"""
        primary_field = template.get("primary_field", "content")
        secondary_fields = template.get("secondary_fields", [])

        return {
            "display_items": [
                {
                    "type": "card",
                    "title": "数据卡片",
                    "content": {
                        "primary": data.get(primary_field, ""),
                        "secondary": {field: data.get(field, "") for field in secondary_fields},
                    },
                    "priority": 7,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [{"label": "详情", "action": "detail", "data": data}],
            "summary_text": "数据卡片视图",
        }
