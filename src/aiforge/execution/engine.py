import ast
from typing import Dict, Any, List, Optional
from rich.console import Console
import traceback

from .code_blocks import CodeBlockManager, CodeBlock
from .unified_executor import UnifiedExecutor
from .result_formatter import AIForgeResultFormatter
from .result_processor import AIForgeResultProcessor

from ..security.security_middleware import SecurityMiddleware


class AIForgeExecutionEngine:
    """执行引擎"""

    def __init__(self, components: Dict[str, Any] = None):
        self.history = []
        self.console = Console()
        self.components = components or {}

        # 核心组件
        self.code_block_manager = CodeBlockManager()
        self.unified_executor = UnifiedExecutor(components)
        self.components["module_executors"] = [self.unified_executor]

        # 结果格式化器
        self.result_formatter = AIForgeResultFormatter(self.console, self.components)
        self.result_processor = AIForgeResultProcessor(self.console, self.components)

        # 安全中间件
        self._security_middleware = SecurityMiddleware(self.components)

        # 执行统计
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "timeout_executions": 0,
            "syntax_errors": 0,
            "runtime_errors": 0,
        }

    # === 核心执行方法 ===

    def execute_python_code(self, code: str) -> Dict[str, Any]:
        """使用安全执行器执行Python代码"""
        self.execution_stats["total_executions"] += 1

        # 获取安全runner
        runner = self.components.get("runner")
        if not runner:
            self.execution_stats["failed_executions"] += 1
            return {
                "success": False,
                "error": "安全执行器不可用",
                "code": code,
            }

        try:
            # 预处理代码
            code = self._preprocess_code(code)

            # 语法检查
            compile(code, "<string>", "exec")

            # 使用安全执行器执行
            result = runner.execute_code(code)

            if result["success"]:
                self.execution_stats["successful_executions"] += 1

                # 保持原有的历史记录格式
                execution_result = {
                    "success": True,
                    "result": result["result"],
                    "code": code,
                }

                business_success = True
                if isinstance(result["result"], dict) and result["result"].get("status") == "error":
                    business_success = False

                self.history.append(
                    {
                        "code": code,
                        "result": {"__result__": result["result"]},
                        "success": business_success,
                    }
                )

                return execution_result
            else:
                self.execution_stats["failed_executions"] += 1
                error_result = {
                    "success": False,
                    "error": result["error"],
                    "code": code,
                }
                self.history.append(
                    {
                        "code": code,
                        "result": {"__result__": None, "error": result["error"]},
                        "success": False,
                    }
                )
                return error_result

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
            self.execution_stats["failed_executions"] += 1
            error_result = {"success": False, "error": str(e), "code": code}
            self.history.append(
                {"code": code, "result": {"__result__": None, "error": str(e)}, "success": False}
            )
            return error_result

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

    def validate_parameter_usage_with_dataflow(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """参数验证"""
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

            # 分离的安全检查
            if not self._check_code_security(code, func_params):
                return False

            # 分离的参数使用检查
            return self._check_parameter_usage(code, func_params, required_params)

        except Exception:
            return False

    def _check_code_security(self, code: str, function_params: List[str]) -> bool:
        """独立的代码安全检查"""

        class VirtualModule:
            def __init__(self, code):
                self._code = code

        virtual_module = VirtualModule(code)
        context = {"function_params": function_params, "task_type": None, "parameters": {}}

        validation_result = self._security_middleware.validate_execution(
            virtual_module, context, "AIForgeExecutionEngine"
        )

        return validation_result.get("overall_allowed", True)

    def _check_parameter_usage(
        self, code: str, func_params: List[str], required_params: Dict
    ) -> bool:
        """独立的参数使用检查"""
        from .analyzer import DataFlowAnalyzer

        analyzer = DataFlowAnalyzer(func_params, self.components)
        tree = ast.parse(code)
        analyzer.visit(tree)

        # 检查参数使用情况
        meaningful_uses = analyzer.meaningful_uses
        meaningful_param_count = 0
        for param_name in func_params:
            if param_name in required_params and param_name in meaningful_uses:
                meaningful_param_count += 1

        total_required = len([p for p in func_params if p in required_params])
        if total_required == 0:
            return True

        usage_ratio = meaningful_param_count / total_required
        return usage_ratio >= 0.5

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
    def _analyze_code_security(self, code: str, function_params: List[str]) -> Dict[str, Any]:
        """重写的代码安全分析"""

        class VirtualModule:
            def __init__(self, code):
                self._code = code

        virtual_module = VirtualModule(code)
        context = {"function_params": function_params, "task_type": None, "parameters": {}}

        # 使用统一的安全中间件获取标准结果
        validation_result = self._security_middleware.validate_execution(
            virtual_module, context, "AIForgeExecutionEngine"
        )

        #  将标准结果转换为所需格式
        return self._adapt_security_result_for_dataflow_analysis(validation_result)

    def _adapt_security_result_for_dataflow_analysis(
        self, validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """适配安全验证结果用于数据流分析"""
        code_result = validation_result.get("code", {})
        network_result = validation_result.get("network", {})

        # 构建数据流分析所需的格式
        adapted_result = {
            "has_conflicts": False,
            "conflicts": [],
            "meaningful_uses": [],
            "assignments": {},
            "api_calls": [],
            "dangerous_functions": [],
            "network_analysis": {},
        }

        # 从代码验证结果中提取数据
        if code_result:
            adapted_result.update(
                {
                    "has_conflicts": code_result.get("has_conflicts", False),
                    "conflicts": code_result.get("conflicts", []),
                    "meaningful_uses": code_result.get("meaningful_uses", []),
                    "assignments": code_result.get("assignments", {}),
                    "api_calls": code_result.get("api_calls", []),
                    "dangerous_functions": code_result.get("dangerous_functions", []),
                }
            )

        # 从网络验证结果中提取数据
        if network_result:
            adapted_result["network_analysis"] = network_result.get("network_analysis", {})

            # 如果有网络安全问题，添加到冲突中
            if network_result.get("network_analysis", {}).get("blocked_operations"):
                adapted_result["has_conflicts"] = True
                for op in network_result["network_analysis"]["blocked_operations"]:
                    adapted_result["conflicts"].append(
                        {
                            "type": "network_security_violation",
                            "description": f"Network access is denied: {op}",
                            "severity": "high",
                        }
                    )

        return adapted_result

    def _preprocess_code(self, code: str) -> str:
        """智能代码预处理"""
        lines = code.split("\n")
        processed_lines = []

        for line in lines:
            line = line.expandtabs(4)
            processed_lines.append(line)

        return "\n".join(processed_lines)

    # === 格式化接口 ===

    def format_execution_result(
        self, code_block: str, result: Dict[str, Any], block_name: str = None
    ):
        """格式化执行结果"""
        return self.result_formatter.format_execution_result(code_block, result, block_name)

    def format_execution_summary(
        self, total_rounds: int, max_rounds: int, history_count: int, success: bool
    ):
        """格式化执行总结"""
        return self.result_formatter.format_execution_summary(
            total_rounds, max_rounds, history_count, success
        )

    def format_task_type_result(self, result: Dict[str, Any], task_type: str):
        """格式化任务类型结果"""
        return self.result_formatter.format_task_type_result(result, task_type)

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
        return self.result_processor.get_intelligent_feedback(result)

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
