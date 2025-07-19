import time
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from .enhanced_cache import EnhancedAiForgeCodeCache


class TemplateBasedCodeCache(EnhancedAiForgeCodeCache):
    """基于模板的代码缓存管理器"""

    def __init__(self, cache_dir: Path, config: dict | None = None):
        super().__init__(cache_dir, config)

        # 预定义的任务模板模式
        self.task_templates = {
            # 数据获取类模板
            "web_search_news": {
                "pattern": r"搜索.*新闻|search.*news|查找.*资讯",
                "key_params": ["query", "max_results", "time_range", "source"],
                "template_id": "web_search_news_v1",
            },
            "web_search_general": {
                "pattern": r"请生成一个搜索函数.*搜索引擎URL模式.*返回数据格式",
                "key_params": ["topic", "max_results", "min_results"],
                "template_id": "web_search_v1",
            },
            "web_scraping": {
                "pattern": r"爬取.*网页|抓取.*数据|spider.*crawl",
                "key_params": ["url", "selectors", "output_format"],
                "template_id": "web_scraping_v1",
            },
            "api_data_fetch": {
                "pattern": r"调用.*api|获取.*接口数据|fetch.*data",
                "key_params": ["endpoint", "method", "headers", "params"],
                "template_id": "api_fetch_v1",
            },
            "database_query": {
                "pattern": r"查询.*数据库|database.*query|sql.*select",
                "key_params": ["connection", "query", "format"],
                "template_id": "db_query_v1",
            },
            # 数据处理类模板
            "data_analysis": {
                "pattern": r"分析.*数据.*生成报告",
                "key_params": ["data_source", "analysis_type"],
                "template_id": "data_analysis_v1",
            },
            "data_analysis_csv": {
                "pattern": r"分析.*csv|处理.*表格数据|pandas.*analyze",
                "key_params": ["file_path", "analysis_type", "columns"],
                "template_id": "csv_analysis_v1",
            },
            "data_transformation": {
                "pattern": r"转换.*数据格式|transform.*data|格式化.*数据",
                "key_params": ["input_format", "output_format", "rules"],
                "template_id": "data_transform_v1",
            },
            "data_visualization": {
                "pattern": r"可视化.*数据|绘制.*图表|plot.*chart",
                "key_params": ["data", "chart_type", "style"],
                "template_id": "data_viz_v1",
            },
            # 文件操作类模板
            "file_processing": {
                "pattern": r"处理.*文件.*批量操作",
                "key_params": ["file_pattern", "operation_type"],
                "template_id": "file_processing_v1",
            },
            "file_batch_processing": {
                "pattern": r"批量.*处理文件|batch.*file.*operation",
                "key_params": ["file_pattern", "operation_type", "output_dir"],
                "template_id": "batch_file_v1",
            },
            "document_parsing": {
                "pattern": r"解析.*文档|parse.*document|提取.*pdf",
                "key_params": ["file_type", "extraction_rules", "output_format"],
                "template_id": "doc_parse_v1",
            },
            "file_conversion": {
                "pattern": r"转换.*文件格式|convert.*file|格式转换",
                "key_params": ["input_format", "output_format", "quality"],
                "template_id": "file_convert_v1",
            },
            # 网络通信类模板
            "http_request": {
                "pattern": r"发送.*http请求|make.*request|调用.*接口",
                "key_params": ["url", "method", "headers", "payload"],
                "template_id": "http_req_v1",
            },
            "webhook_handler": {
                "pattern": r"处理.*webhook|回调.*处理|event.*handler",
                "key_params": ["endpoint", "event_type", "response_format"],
                "template_id": "webhook_v1",
            },
            "api_integration": {
                "pattern": r"集成.*api|第三方.*服务|service.*integration",
                "key_params": ["service", "auth_method", "operations"],
                "template_id": "api_integration_v1",
            },
            # 自动化任务类模板
            "scheduled_task": {
                "pattern": r"定时.*任务|schedule.*task|cron.*job",
                "key_params": ["frequency", "task_definition", "conditions"],
                "template_id": "scheduled_v1",
            },
            "workflow_automation": {
                "pattern": r"自动化.*流程|workflow.*automation|批量.*自动",
                "key_params": ["steps", "dependencies", "error_handling"],
                "template_id": "workflow_v1",
            },
            "monitoring_alert": {
                "pattern": r"监控.*告警|monitor.*alert|健康.*检查",
                "key_params": ["metrics", "thresholds", "notification"],
                "template_id": "monitor_v1",
            },
            # 内容生成类模板
            "report_generation": {
                "pattern": r"生成.*报告|create.*report|文档.*生成",
                "key_params": ["template", "data_source", "format"],
                "template_id": "report_gen_v1",
            },
            "code_generation": {
                "pattern": r"生成.*代码|code.*generation|编程.*自动",
                "key_params": ["language", "framework", "requirements"],
                "template_id": "code_gen_v1",
            },
            "document_creation": {
                "pattern": r"创建.*文档|generate.*document|写作.*自动",
                "key_params": ["document_type", "content", "styling"],
                "template_id": "doc_create_v1",
            },
            # 系统集成类模板
            "service_integration": {
                "pattern": r"系统.*集成|service.*integration|连接.*系统",
                "key_params": ["source_system", "target_system", "mapping"],
                "template_id": "sys_integration_v1",
            },
            "data_synchronization": {
                "pattern": r"数据.*同步|sync.*data|实时.*同步",
                "key_params": ["systems", "sync_rules", "conflict_resolution"],
                "template_id": "data_sync_v1",
            },
        }

    def get_cached_modules_by_standardized_instruction(
        self, standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """基于标准化指令获取缓存模块"""
        cache_key = standardized_instruction.get("cache_key")
        task_type = standardized_instruction.get("task_type")

        # 首先尝试精确匹配
        exact_matches = self._get_modules_by_key(cache_key)
        if exact_matches:
            return exact_matches

        # 然后尝试任务类型匹配
        type_key = f"{task_type}_{standardized_instruction.get('action', 'general')}"
        type_matches = self._get_modules_by_key(type_key)
        if type_matches:
            return type_matches

        # 最后回退到原有逻辑
        return []

    def _get_modules_by_key(self, cache_key: str) -> List[Any]:
        """根据缓存键获取模块"""
        with self._lock:
            try:
                modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.instruction_hash == cache_key)
                    .order_by(self.CodeModule.success_count.desc())
                )

                return [
                    (m.module_id, m.file_path, m.success_count, m.failure_count, {})
                    for m in modules
                ]
            except Exception:
                return []

    def save_module(
        self, instruction_or_standardized: Any, code: str, metadata: dict = None
    ) -> str | None:
        """统一的模块保存入口"""
        if isinstance(instruction_or_standardized, dict):
            # 标准化指令保存
            return self.save_standardized_module(instruction_or_standardized, code)
        else:
            # 传统指令保存 - 使用模板缓存逻辑
            return self.save_template_module(instruction_or_standardized, code, metadata)

    def save_standardized_module(
        self, standardized_instruction: Dict[str, Any], code: str
    ) -> str | None:
        """保存基于标准化指令的模块"""
        if not self._validate_code(code):
            return None

        cache_key = standardized_instruction.get("cache_key")
        task_type = standardized_instruction.get("task_type")

        module_id = f"std_{task_type}_{int(time.time())}"
        file_path = self.modules_dir / f"{module_id}.py"

        try:
            # 生成参数化代码
            parameterized_code = self._parameterize_standardized_code(
                code, standardized_instruction.get("parameters", {})
            )

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(parameterized_code)

            # 保存元数据
            metadata = {
                "standardized_instruction": standardized_instruction,
                "task_type": task_type,
                "cache_key": cache_key,
                "is_standardized": True,
                "created_at": time.time(),
            }

            with self._lock:
                self.CodeModule.create(
                    module_id=module_id,
                    instruction_hash=cache_key,
                    file_path=str(file_path),
                    created_at=time.time(),
                    last_used=time.time(),
                    metadata=json.dumps(metadata),
                )

            return module_id

        except Exception:
            if file_path.exists():
                file_path.unlink()
            return None

    def _parameterize_standardized_code(self, code: str, params: Dict) -> str:
        """将标准化指令的代码参数化"""
        parameterized_code = code
        for param_name, param_value in params.items():
            if isinstance(param_value, str) and param_value in code:
                placeholder = f"{{{{ {param_name} }}}}"
                parameterized_code = parameterized_code.replace(param_value, placeholder)
        return parameterized_code

    def save_template_module(
        self, instruction: str, code: str, metadata: dict | None = None
    ) -> str | None:
        """保存模板化代码模块"""
        if not self._validate_code(code):
            return None

        template_info = self._extract_template_info(instruction)
        cache_key = template_info["cache_key"]

        # 根据是否有模板匹配选择不同的保存策略
        if template_info["template_id"]:
            # 模板化保存
            module_id = f"template_{template_info['template_name']}_{int(time.time())}"
            file_path = self.modules_dir / f"{module_id}.py"

            try:
                # 生成参数化代码模板
                template_code = self._parameterize_code(code, template_info["parameters"])

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(template_code)

                # 扩展元数据
                extended_metadata = {
                    "template_id": template_info["template_id"],
                    "template_name": template_info["template_name"],
                    "parameters": template_info["parameters"],
                    "original_instruction": instruction,
                    "is_template": True,
                    **(metadata or {}),
                }

                current_time = time.time()
                with self._lock:
                    self.CodeModule.create(
                        module_id=module_id,
                        instruction_hash=cache_key,
                        file_path=str(file_path),
                        created_at=current_time,
                        last_used=current_time,
                        metadata=json.dumps(extended_metadata),
                    )

                return module_id

            except Exception:
                if file_path.exists():
                    file_path.unlink()
                return None
        else:
            # 回退到增强缓存的保存策略
            return self.save_enhanced_module(instruction, code, metadata=metadata)

    def get_cached_modules_by_template(self, instruction: str) -> List[Any]:
        """基于模板获取缓存模块"""
        template_info = self._extract_template_info(instruction)

        # 如果有模板匹配，使用模板缓存逻辑
        if template_info["template_id"]:
            cache_key = template_info["cache_key"]

            with self._lock:
                try:
                    modules = (
                        self.CodeModule.select()
                        .where(self.CodeModule.instruction_hash == cache_key)
                        .order_by(self.CodeModule.success_count.desc())
                    )

                    results = []
                    for module in modules:
                        metadata = json.loads(module.metadata)

                        if self._is_template_compatible(template_info, metadata):
                            results.append(
                                (
                                    module.module_id,
                                    module.file_path,
                                    module.success_count,
                                    module.failure_count,
                                    metadata.get("parameters", {}),
                                )
                            )

                    return results
                except Exception:
                    return []
        else:
            # 没有模板匹配，使用父类的增强缓存策略
            enhanced_results = self.get_cached_modules_enhanced(instruction)
            # 转换格式以匹配模板缓存的返回格式
            return [(r[0], r[1], r[2], r[3], {}) for r in enhanced_results]

    def _generate_cache_key(
        self,
        instruction: str,
        executor_type: str | None = None,
        task_category: str | None = None,
        use_semantic: bool = True,
    ) -> str:
        """重写缓存键生成，优先使用模板匹配"""
        # 策略1: 模板匹配（最高优先级）
        template_info = self._extract_template_info(instruction)
        if template_info["template_id"]:
            return template_info["cache_key"]

        # 策略2-4: 回退到父类的增强缓存策略
        return super()._generate_cache_key(instruction, executor_type, task_category, use_semantic)

    def _extract_template_info(self, instruction: str) -> Dict:
        """从指令中提取模板信息"""
        for template_name, template_config in self.task_templates.items():
            if re.search(template_config["pattern"], instruction, re.DOTALL | re.IGNORECASE):
                # 提取参数值
                params = self._extract_parameters(instruction, template_config["key_params"])
                return {
                    "template_id": template_config["template_id"],
                    "template_name": template_name,
                    "parameters": params,
                    "cache_key": template_config["template_id"],
                }

        # 如果没有匹配的模板，回退到语义分析
        analyzed_type = self._analyze_task_type(instruction)
        return {
            "template_id": None,
            "template_name": "semantic",
            "parameters": {},
            "cache_key": f"semantic_{analyzed_type}",
        }

    def _extract_parameters(self, instruction: str, param_names: List[str]) -> Dict:
        """从指令中提取参数值 - 扩展支持更多参数类型"""
        params = {}

        # 针对搜索任务的参数提取
        if "topic" in param_names or "query" in param_names:
            query_patterns = [
                r'search_web\\("([^"]+)"',
                r'搜索["""]([^"""]+)["""]',
                r'查找["""]([^"""]+)["""]',
            ]
            for pattern in query_patterns:
                match = re.search(pattern, instruction)
                if match:
                    params["query"] = match.group(1)
                    params["topic"] = match.group(1)
                    break

        if "max_results" in param_names:
            result_patterns = [
                r'search_web\\("[^"]+",\\s*(\\d+)',
                r"最多.*?(\\d+).*?条",
                r"(\\d+).*?个结果",
            ]
            for pattern in result_patterns:
                match = re.search(pattern, instruction)
                if match:
                    params["max_results"] = int(match.group(1))
                    break

        # 针对文件处理任务的参数提取
        if "file_pattern" in param_names:
            file_patterns = [
                r"文件.*?([*\\w\\.]+)",
                r"处理.*?([*\\w\\.]+)",
                r"([^\\s]+\\.[a-zA-Z]+)",
            ]
            for pattern in file_patterns:
                match = re.search(pattern, instruction)
                if match:
                    params["file_pattern"] = match.group(1)
                    break

        if "file_path" in param_names:
            path_match = re.search(r"([^\\s]+\\.[a-zA-Z]+)", instruction)
            if path_match:
                params["file_path"] = path_match.group(1)

        # 针对API调用的参数提取
        if "url" in param_names or "endpoint" in param_names:
            url_match = re.search(r"(https?://[^\\s]+)", instruction)
            if url_match:
                params["url"] = url_match.group(1)
                params["endpoint"] = url_match.group(1)

        if "method" in param_names:
            method_patterns = [
                r"\\b(GET|POST|PUT|DELETE|PATCH)\\b",
                r"(get|post|put|delete|patch).*?请求",
            ]
            for pattern in method_patterns:
                match = re.search(pattern, instruction, re.IGNORECASE)
                if match:
                    params["method"] = match.group(1).upper()
                    break

        # 针对数据分析的参数提取
        if "analysis_type" in param_names:
            analysis_patterns = [
                r"(统计|描述性|相关性|回归|聚类).*?分析",
                r"(statistical|descriptive|correlation|regression|clustering).*?analysis",
            ]
            for pattern in analysis_patterns:
                match = re.search(pattern, instruction, re.IGNORECASE)
                if match:
                    params["analysis_type"] = match.group(1)
                    break

        return params

    def _is_template_compatible(self, template_info: Dict, metadata: Dict) -> bool:
        """检查模板兼容性"""
        return metadata.get("template_id") == template_info.get("template_id")

    def _parameterize_code(self, code: str, params: Dict) -> str:
        """将代码参数化"""
        parameterized_code = code
        for param_name, param_value in params.items():
            if isinstance(param_value, str) and param_value in code:
                placeholder = f"{{{{ {param_name} }}}}"
                parameterized_code = parameterized_code.replace(param_value, placeholder)
        return parameterized_code

    def execute_template_module(self, module_id: str, current_params: Dict) -> Any:
        """执行模板模块，动态替换参数"""
        module = self.load_module(module_id)
        if not module:
            return None

        try:
            module_record = self.CodeModule.get(self.CodeModule.module_id == module_id)
            metadata = json.loads(module_record.metadata)

            # 如果是标准化模块或模板模块，进行参数替换
            if metadata.get("is_template", False) or metadata.get("is_standardized", False):
                original_params = metadata.get("parameters", {})

                # 动态替换参数执行
                if hasattr(module, "search_web"):

                    def parameterized_search(topic, max_results):
                        return module.search_web(topic, max_results)

                    result = parameterized_search(
                        current_params.get("topic", original_params.get("topic")),
                        current_params.get("max_results", original_params.get("max_results", 10)),
                    )
                    return result

            # 通用执行逻辑
            if hasattr(module, "__result__"):
                return getattr(module, "__result__")

            return None

        except Exception:
            return None
