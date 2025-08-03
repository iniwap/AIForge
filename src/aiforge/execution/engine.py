import ast
import importlib
import platform
import threading
import signal
import time
from typing import Dict, Any, List, Set, Optional
from rich.console import Console
import traceback

from .analyzer import DataFlowAnalyzer
from .code_blocks import CodeBlockManager, CodeBlock
from .unified_executor import UnifiedParameterizedExecutor


class AIForgeExecutionEngine:
    """执行引擎"""

    MAX_EXECUTE_TIMEOUT = 30

    def __init__(self, components: Dict[str, Any] = None):
        self.history = []  # 代码级别的执行历史
        self.console = Console()
        self.components = components or {}

        # 整合子组件
        self.code_block_manager = CodeBlockManager()
        self.unified_executor = UnifiedParameterizedExecutor(components)
        # 可以注册自定义策略
        # unified_executor.register_custom_strategy(CustomSearchStrategy())

        self.components["module_executors"] = [self.unified_executor]

        # 集成结果处理器
        try:
            from .result_processor import AIForgeResultProcessor

            self.result_processor = AIForgeResultProcessor(self.console)
        except ImportError:
            self.result_processor = None

        # 集成结果格式化器
        from .result_formatter import AIForgeResultFormatter

        self.result_formatter = AIForgeResultFormatter(self.console)

        # 执行统计
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "timeout_executions": 0,
            "syntax_errors": 0,
            "runtime_errors": 0,
        }

    # === 核心执行方法 - 基于原有AIForgeExecutor逻辑 ===

    def execute_python_code(self, code: str) -> Dict[str, Any]:
        """主要的Python代码执行方法 - 保持原有逻辑"""
        self.execution_stats["total_executions"] += 1

        try:
            code = self._preprocess_code(code)
            compile(code, "<string>", "exec")
            exec_globals = self._build_smart_execution_environment(code)
            execution_result = self._execute_with_timeout(code, exec_globals)

            self.execution_stats["successful_executions"] += 1
            return execution_result

        except TimeoutError:
            self.execution_stats["timeout_executions"] += 1
            self.execution_stats["failed_executions"] += 1
            return {
                "success": False,
                "error": "代码执行超时（30秒限制）",
                "code": code,
            }
        except SyntaxError as e:
            self.execution_stats["syntax_errors"] += 1
            self.execution_stats["failed_executions"] += 1
            return {
                "success": False,
                "error": f"语法错误: {str(e)} (行 {e.lineno})",
                "traceback": traceback.format_exc(),
                "code": code,
            }
        except Exception as e:
            self.execution_stats["runtime_errors"] += 1
            self.execution_stats["failed_executions"] += 1
            error_result = {"success": False, "error": str(e), "code": code}
            self.history.append(
                {"code": code, "result": {"__result__": None, "error": str(e)}, "success": False}
            )
            return error_result

    def _execute_with_timeout(self, code: str, exec_globals: Dict[str, Any]) -> Dict[str, Any]:
        """跨平台超时执行 - 保持原有逻辑"""

        def timeout_handler(signum, frame):
            raise TimeoutError("代码执行超时")

        if platform.system() != "Windows":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.MAX_EXECUTE_TIMEOUT)
            try:
                exec(code, exec_globals, exec_globals)
            finally:
                signal.alarm(0)
        else:
            # Windows超时处理
            timeout_occurred = threading.Event()
            execution_exception = None

            def timeout_callback():
                timeout_occurred.set()

            def execute_with_timeout():
                nonlocal execution_exception
                try:
                    exec(code, exec_globals, exec_globals)
                except Exception as e:
                    execution_exception = e

            timer = threading.Timer(self.MAX_EXECUTE_TIMEOUT, timeout_callback)
            timer.start()
            exec_thread = threading.Thread(target=execute_with_timeout)
            exec_thread.start()
            exec_thread.join(self.MAX_EXECUTE_TIMEOUT + 1)
            timer.cancel()

            if timeout_occurred.is_set():
                raise TimeoutError("代码执行超时")
            if execution_exception:
                raise execution_exception

        result = self._extract_result(exec_globals)
        execution_result = {
            "success": True,
            "result": result,
            "code": code,
        }

        business_success = True
        if isinstance(result, dict) and result.get("status") == "error":
            business_success = False

        self.history.append(
            {
                "code": code,
                "result": {"__result__": result},
                "success": business_success,
            }
        )

        return execution_result

    # === 代码块管理接口 ===

    def extract_code_blocks(self, text: str) -> List[str]:
        """提取代码块"""
        return self.code_block_manager.extract_code_blocks(text)

    def add_block(self, code, name, version):
        """添加代码块到管理器"""

        block = CodeBlock(code=code, name=name, version=version)
        self.code_block_manager.add_block(block)

    def update_block_result(self, name: str, result: Dict[str, Any], execution_time: float = 0.0):
        """更新代码块的执行结果"""
        self.code_block_manager.update_block_result(name, result, execution_time)

    def get_block(self, name: str) -> Optional[CodeBlock]:
        """获取指定名称的代码块"""
        return self.code_block_manager.get_block(name)

    def get_execution_history(self) -> List[CodeBlock]:
        """获取按执行顺序排列的代码块历史"""
        return self.code_block_manager.get_execution_history()

    def parse_markdown_blocks(self, text: str) -> List[CodeBlock]:
        """从markdown文本中解析代码块"""
        return self.code_block_manager.parse_markdown_blocks(text)

    def process_code_blocks_execution(
        self, code_blocks: List[str], llm_client=None
    ) -> List[Dict[str, Any]]:
        """处理多个代码块的执行 - 完整的处理流程"""
        results = []

        for i, code_text in enumerate(code_blocks):
            if not code_text.strip():
                continue

            block = CodeBlock(code=code_text, name=f"block_{i+1}", version=1)
            self.console.print(f"⚡ 开始执行代码块: {block.name}", style="dim white")

            start_time = time.time()
            result = self.execute_python_code(code_text)
            execution_time = time.time() - start_time

            result["block_name"] = block.name
            result["execution_time"] = execution_time

            if not result.get("success") and llm_client:
                feedback = self._generate_intelligent_feedback(result)
                llm_client.send_feedback(feedback)

            results.append(result)
            self.code_block_manager.add_block(block)
            self.code_block_manager.update_block_result(block.name, result, execution_time)

        return results

    # === 统一执行器接口 ===

    def execute_with_unified_executor(self, module, instruction: str, **kwargs) -> Any:
        """使用统一执行器执行模块"""
        return self.unified_executor.execute(module, instruction, **kwargs)

    def can_handle_module(self, module) -> bool:
        """检查是否能处理指定模块"""
        return self.unified_executor.can_handle(module)

    def register_custom_strategy(self, strategy):
        """注册自定义执行策略"""
        self.unified_executor.register_custom_strategy(strategy)

    # === 数据流分析接口 ===

    def _analyze_code_security(self, code: str, function_params: List[str]) -> Dict[str, Any]:
        """使用DataFlowAnalyzer进行安全分析"""
        analyzer = DataFlowAnalyzer(function_params)

        try:
            tree = ast.parse(code)
            analyzer.visit(tree)

            return {
                "has_conflicts": len(analyzer.parameter_conflicts) > 0,
                "conflicts": analyzer.parameter_conflicts,
                "meaningful_uses": list(analyzer.meaningful_uses),
                "assignments": analyzer.assignments,
                "api_calls": analyzer.api_calls,
            }
        except Exception as e:
            return {"has_conflicts": False, "error": f"安全分析失败: {str(e)}"}

    def validate_parameter_usage_with_dataflow(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """使用增强数据流分析的参数验证 - 对外接口"""
        try:
            tree = ast.parse(code)

            function_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "execute_task":
                    function_def = node
                    break

            if not function_def:
                return False

            func_params = [arg.arg for arg in function_def.args.args]
            required_params = standardized_instruction.get("required_parameters", {})

            security_result = self._analyze_code_security(code, func_params)

            # 检查API密钥相关冲突
            if security_result.get("has_conflicts"):
                conflicts = security_result.get("conflicts", [])
                for conflict in conflicts:
                    if conflict["type"] == "api_key_usage":
                        return False

            # 检查参数冲突
            if security_result.get("has_conflicts"):
                conflicts = security_result.get("conflicts", [])
                for conflict in conflicts:
                    if (
                        conflict["type"] == "hardcoded_coordinates"
                        and conflict["parameter"] == "location"
                    ):
                        return False

            # 原有的参数使用验证
            meaningful_uses = security_result.get("meaningful_uses", set())

            meaningful_param_count = 0
            for param_name in func_params:
                if param_name in required_params:
                    if param_name in meaningful_uses:
                        meaningful_param_count += 1

            total_required = len([p for p in func_params if p in required_params])
            if total_required == 0:
                return True

            usage_ratio = meaningful_param_count / total_required

            return usage_ratio >= 0.5

        except Exception:
            return False

    def validate_code_for_caching(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """验证代码是否适合缓存"""
        return self.validate_parameter_usage_with_dataflow(code, standardized_instruction)

    # === 结果处理器接口 ===

    def validate_cached_result(
        self, result: Dict[str, Any], standardized_instruction: Dict[str, Any]
    ) -> bool:
        """验证缓存结果"""
        if self.result_processor:
            return self.result_processor.validate_cached_result(result, standardized_instruction)
        # 如果没有结果处理器，使用基本验证
        return result.get("status") == "success" and result.get("data")

    def basic_execution_check(self, result: Dict[str, Any]) -> bool:
        """基础执行检查"""
        if self.result_processor:
            return self.result_processor.basic_execution_check(result)
        return result.get("success", False)

    def get_intelligent_feedback(self, result: Dict[str, Any]) -> str:
        """获取智能反馈"""
        if self.result_processor:
            return self.result_processor.get_intelligent_feedback(result)
        return self._generate_intelligent_feedback(result)

    def validate_execution_result(
        self, result: Dict[str, Any], instruction: str, task_type: str = None, llm_client=None
    ):
        """验证执行结果"""
        if self.result_processor:
            return self.result_processor.validate_execution_result(
                result, instruction, task_type, llm_client
            )
        return True, "basic", "", {}

    def get_validation_feedback(self, failure_reason: str, validation_details: Dict[str, Any]):
        """获取验证反馈"""
        if self.result_processor:
            return self.result_processor.get_validation_feedback(failure_reason, validation_details)
        return f"验证失败: {failure_reason}"

    def process_execution_result(self, result_content, instruction: str, task_type: str = None):
        """处理执行结果"""
        if self.result_processor:
            return self.result_processor.process_execution_result(
                result_content, instruction, task_type
            )
        return result_content

    # === 执行统计接口 ===

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        total = self.execution_stats["total_executions"]
        if total == 0:
            return self.execution_stats

        stats = self.execution_stats.copy()
        stats["success_rate"] = self.execution_stats["successful_executions"] / total
        stats["failure_rate"] = self.execution_stats["failed_executions"] / total
        stats["timeout_rate"] = self.execution_stats["timeout_executions"] / total

        return stats

    def reset_stats(self):
        """重置执行统计"""
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "timeout_executions": 0,
            "syntax_errors": 0,
            "runtime_errors": 0,
        }

    # === 内部辅助方法 ===

    def _build_smart_execution_environment(self, code: str) -> Dict[str, Any]:
        """智能构建执行环境"""
        exec_globals = {"__builtins__": __builtins__}
        user_imports = self._extract_imports_from_code(code)
        used_names = self._extract_used_names(code)

        for name, import_info in user_imports.items():
            try:
                if import_info["type"] == "import":
                    module = importlib.import_module(import_info["module"])
                    exec_globals[name] = module
                elif import_info["type"] == "from_import":
                    module = importlib.import_module(import_info["module"])
                    if import_info["name"] == "*":
                        for attr_name in dir(module):
                            if not attr_name.startswith("_"):
                                exec_globals[attr_name] = getattr(module, attr_name)
                    else:
                        exec_globals[name] = getattr(module, import_info["name"])
            except (ImportError, AttributeError):
                fallback_module = self._smart_import_fallback(name, import_info)
                if fallback_module is not None:
                    exec_globals[name] = fallback_module

        missing_names = used_names - set(user_imports.keys()) - set(exec_globals.keys())
        for name in missing_names:
            if (
                name in ["__result__", "result", "data", "output", "response", "content"]
                or name.islower()
                and len(name) <= 3
                or name
                in [
                    "a",
                    "b",
                    "c",
                    "d",
                    "e",
                    "f",
                    "g",
                    "h",
                    "i",
                    "j",
                    "k",
                    "l",
                    "m",
                    "n",
                    "o",
                    "p",
                    "q",
                    "r",
                    "s",
                    "t",
                    "u",
                    "v",
                    "w",
                    "x",
                    "y",
                    "z",
                ]
            ):
                continue

            known_modules = ["requests", "json", "os", "sys", "re", "datetime", "time", "random"]
            if name in known_modules:
                smart_module = self._smart_import_missing(name)
                if smart_module is not None:
                    exec_globals[name] = smart_module

        return exec_globals

    def _extract_imports_from_code(self, code: str) -> Dict[str, Dict[str, Any]]:
        """提取代码中的所有导入语句"""
        try:
            tree = ast.parse(code)
            imports = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = {
                            "type": "from_import",
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }

            return imports
        except SyntaxError:
            return {}

    def _extract_used_names(self, code: str) -> Set[str]:
        """提取代码中使用的所有名称"""
        try:
            tree = ast.parse(code)
            used_names = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    current = node
                    while isinstance(current, ast.Attribute):
                        current = current.value
                    if isinstance(current, ast.Name):
                        used_names.add(current.id)

            return used_names
        except SyntaxError:
            return set()

    def _smart_import_fallback(self, name: str, import_info: Dict[str, Any]) -> Any:
        """智能导入回退机制"""
        try:
            fallback_mappings = {
                "feedparser": None,
                "requests": "requests",
                "datetime": "datetime",
                "BeautifulSoup": "bs4.BeautifulSoup",
                "json": "json",
                "os": "os",
                "re": "re",
                "sys": "sys",
                "time": "time",
                "random": "random",
            }

            if name in fallback_mappings:
                fallback_path = fallback_mappings[name]
                if fallback_path is None:
                    return None

                if "." in fallback_path:
                    module_path, attr_name = fallback_path.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    return getattr(module, attr_name)
                else:
                    return importlib.import_module(fallback_path)

            if import_info["type"] == "import":
                return importlib.import_module(import_info["module"])
            elif import_info["type"] == "from_import":
                module = importlib.import_module(import_info["module"])
                return getattr(module, import_info["name"])

        except Exception:
            return None

    def _smart_import_missing(self, name: str) -> Any:
        """为缺失的名称提供智能导入"""
        try:
            common_modules = {
                "requests": "requests",
                "json": "json",
                "os": "os",
                "re": "re",
                "sys": "sys",
                "time": "time",
                "random": "random",
                "datetime": "datetime",
                "BeautifulSoup": "bs4.BeautifulSoup",
                "pd": "pandas",
                "np": "numpy",
                "plt": "matplotlib.pyplot",
            }

            if name in common_modules:
                module_path = common_modules[name]
                if "." in module_path:
                    module_name, attr_name = module_path.rsplit(".", 1)
                    module = importlib.import_module(module_name)
                    return getattr(module, attr_name)
                else:
                    return importlib.import_module(module_path)

            return importlib.import_module(name)

        except Exception:
            return None

    def _preprocess_code(self, code: str) -> str:
        """智能代码预处理"""
        lines = code.split("\n")
        processed_lines = []

        for line in lines:
            line = line.expandtabs(4)
            processed_lines.append(line)

        return "\n".join(processed_lines)

    def _extract_result(self, namespace_dict: dict) -> Any:
        """强制验证数组格式的结果提取"""
        if "__result__" not in namespace_dict:
            return {
                "data": [],
                "status": "error",
                "summary": "代码未执行函数并赋值给 __result__ 变量",
                "metadata": {"error": "missing_result_variable"},
            }

        result = namespace_dict["__result__"]

        if not isinstance(result, dict):
            return {
                "data": [],
                "status": "error",
                "summary": "__result__ 必须是字典格式",
                "metadata": {"error": "invalid_result_type"},
            }

        if "data" not in result:
            return {
                "data": [],
                "status": "error",
                "summary": "__result__ 缺少 data 字段",
                "metadata": {"error": "missing_data_field"},
            }

        if not isinstance(result["data"], list):
            return {
                "data": [],
                "status": "error",
                "summary": "data 字段必须是数组格式",
                "metadata": {"error": "data_not_array"},
            }

        for i, item in enumerate(result["data"]):
            if not isinstance(item, dict):
                return {
                    "data": [],
                    "status": "error",
                    "summary": f"data[{i}] 必须是字典格式",
                    "metadata": {"error": "data_item_not_dict"},
                }

        return result

    def _generate_intelligent_feedback(self, result: Dict[str, Any]) -> str:
        """生成智能反馈"""
        if not result:
            return "执行结果为空，请检查代码逻辑"

        error = result.get("error", "")
        if error:
            return f"执行出错：{error}。请检查代码语法和逻辑。"

        return "执行完成但可能存在问题，请检查输出结果"

    # 提供统一的格式化接口
    def format_execution_result(
        self, code_block: str, result: Dict[str, Any], block_name: str = None
    ):
        """格式化执行结果 - 委托给格式化器"""
        return self.result_formatter.format_execution_result(code_block, result, block_name)

    def format_execution_summary(
        self, total_rounds: int, max_rounds: int, history_count: int, success: bool
    ):
        """格式化执行总结 - 委托给格式化器"""
        return self.result_formatter.format_execution_summary(
            total_rounds, max_rounds, history_count, success
        )

    def format_task_type_result(self, result: Dict[str, Any], task_type: str):
        """格式化任务类型结果 - 委托给格式化器"""
        return self.result_formatter.format_task_type_result(result, task_type)
