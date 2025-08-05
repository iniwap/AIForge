import ast
import time
import re
from typing import Dict, Any, List, Optional
from rich.console import Console
import traceback

from .analyzer import DataFlowAnalyzer
from .code_blocks import CodeBlockManager, CodeBlock
from .unified_executor import UnifiedExecutor
from .result_formatter import AIForgeResultFormatter
from .result_processor import AIForgeResultProcessor
from ..security.network_security import NetworkSecurityAnalyzer


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
        self.result_formatter = AIForgeResultFormatter(self.console)
        self.result_processor = AIForgeResultProcessor(self.console)

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

    def process_code_blocks_execution(
        self, code_blocks: List[str], llm_client=None
    ) -> List[Dict[str, Any]]:
        """处理多个代码块的执行"""
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

    def validate_parameter_usage_with_dataflow(
        self, code: str, standardized_instruction: Dict[str, Any]
    ) -> bool:
        """使用增强数据流分析的参数验证"""
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

            # 检查冲突
            if security_result.get("has_conflicts"):
                conflicts = security_result.get("conflicts", [])
                for conflict in conflicts:
                    if conflict["type"] in ["api_key_usage", "hardcoded_coordinates"]:
                        return False

            # 参数使用验证
            meaningful_uses = security_result.get("meaningful_uses", set())
            meaningful_param_count = 0
            for param_name in func_params:
                if param_name in required_params and param_name in meaningful_uses:
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
        """使用DataFlowAnalyzer进行安全分析，包含危险函数检测和网络安全检查"""
        analyzer = DataFlowAnalyzer(function_params)

        # 现有的危险函数检测
        dangerous_patterns = [
            r"subprocess\.",
            r"os\.system\(",
            r"eval\(",
            r"exec\(",
            r"__import__\(",
            r'open\([^)]*["\']w["\']',
            r"shutil\.rmtree\(",
            r"os\.remove\(",
            r"os\.rmdir\(",
            r"\.unlink\(\)",
            r"\.delete\(\)",
        ]

        security_issues = []
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                security_issues.append(f"检测到危险函数调用: {pattern}")

        # 网络安全分析
        network_analyzer = NetworkSecurityAnalyzer(
            self.components.get("config", {}).get("security", {})
        )
        network_analysis = network_analyzer.analyze_network_risk(code, {})

        # 合并网络安全问题
        if network_analysis["blocked_operations"]:
            security_issues.extend(
                [f"网络访问被阻止: {op}" for op in network_analysis["blocked_operations"]]
            )

        if network_analysis["suspicious_patterns"]:
            security_issues.extend(
                [
                    f"检测到可疑网络模式: {pattern}"
                    for pattern in network_analysis["suspicious_patterns"]
                ]
            )

        try:
            tree = ast.parse(code)
            analyzer.visit(tree)

            result = {
                "has_conflicts": len(analyzer.parameter_conflicts) > 0 or len(security_issues) > 0,
                "conflicts": analyzer.parameter_conflicts,
                "meaningful_uses": list(analyzer.meaningful_uses),
                "assignments": analyzer.assignments,
                "api_calls": analyzer.api_calls,
                "dangerous_functions": security_issues,
                "network_analysis": network_analysis,  # 新增网络分析结果
            }

            # 如果检测到危险函数或网络安全问题，将其添加到冲突列表中
            if security_issues:
                for issue in security_issues:
                    result["conflicts"].append(
                        {"type": "security_violation", "description": issue, "severity": "high"}
                    )

            return result
        except Exception as e:
            return {
                "has_conflicts": len(security_issues) > 0,
                "error": f"安全分析失败: {str(e)}",
                "dangerous_functions": security_issues,
                "network_analysis": network_analysis,  # 新增网络分析结果
                "conflicts": [],
                "meaningful_uses": [],
                "assignments": {},
                "api_calls": [],
            }

    def _preprocess_code(self, code: str) -> str:
        """智能代码预处理"""
        lines = code.split("\n")
        processed_lines = []

        for line in lines:
            line = line.expandtabs(4)
            processed_lines.append(line)

        return "\n".join(processed_lines)

    def _generate_intelligent_feedback(self, result: Dict[str, Any]) -> str:
        """生成智能反馈"""
        if not result:
            return "执行结果为空，请检查代码逻辑"

        error = result.get("error", "")
        if error:
            return f"执行出错：{error}。请检查代码语法和逻辑。"

        return "执行完成但可能存在问题，请检查输出结果"

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
