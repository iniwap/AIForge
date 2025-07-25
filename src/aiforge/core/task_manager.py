import json
import time
import hashlib
from rich.console import Console
from typing import Optional, List, Dict, Any, Tuple

from ..llm.llm_manager import AIForgeLLMManager
from ..llm.llm_client import AIForgeLLMClient
from ..execution.executor import AIForgeExecutor
from ..optimization.feedback_optimizer import FeedbackOptimizer
from ..formatting.result_formatter import AIForgeResultFormatter
from ..execution.code_blocks import CodeBlockManager, CodeBlock
from ..prompts.enhanced_prompts import get_base_aiforge_prompt
from .enhanced_error_analyzer import EnhancedErrorAnalyzer
from ..validation.result_validator import IntelligentResultValidator  # 新增导入


class AIForgeTask:
    """AIForge 任务执行器"""

    def __init__(
        self, llm_client: AIForgeLLMClient, max_rounds, optimization, max_optimization_attempts
    ):
        self.client = llm_client
        self.executor = AIForgeExecutor()
        self.console = Console()

        self.formatter = AIForgeResultFormatter(self.console)
        self.code_block_manager = CodeBlockManager()
        self.error_analyzer = EnhancedErrorAnalyzer()

        # 新增智能结果验证器
        self.result_validator = IntelligentResultValidator(llm_client)
        self.expected_output = None  # 存储预期输出规则

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.max_optimization_attempts = max_optimization_attempts
        self.optimization = optimization
        self.execution_history = []
        self.feedback_optimizer = (
            FeedbackOptimizer() if optimization.get("optimize_tokens", True) else None
        )

    def set_expected_output(self, expected_output: Dict[str, Any]):
        """设置预期输出规则"""
        self.expected_output = expected_output

    def _validate_execution_result_intelligent(
        self, result: Dict[str, Any], instruction: str, task_type: str = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """使用智能验证器验证执行结果"""

        if not self.expected_output:
            # 如果没有预期输出规则，使用基础验证
            return self._basic_execution_check(result), "", {}

        return self.result_validator.validate_execution_result(
            result, self.expected_output, instruction, task_type or "general"
        )

    def _basic_execution_check(self, result: Dict[str, Any]) -> bool:
        """基础执行检查（当没有预期输出规则时使用）"""
        # 首先检查代码执行是否成功
        if not result.get("success", False):
            return False

        # 然后检查业务逻辑是否成功
        result_content = result.get("result")
        if result_content is None:
            return False

        if isinstance(result_content, dict):
            status = result_content.get("status")
            if status == "error":
                return False
            elif status == "success":
                return True
            # 检查是否包含错误信息
            if "error" in result_content or "exception" in result_content:
                return False

        # 如果没有明确的状态，但有数据且无错误，认为成功
        return True

    def process_code_execution(self, code_blocks: List[str]) -> Optional[str]:
        """处理代码块执行并格式化结果"""
        results = []

        for i, code_text in enumerate(code_blocks):
            if not code_text.strip():
                continue

            # 创建代码块对象
            block = CodeBlock(code=code_text, name=f"block_{i+1}", version=1)

            self.console.print(f"⚡ 开始执行代码块: {block.name}", style="dim white")

            # 记录执行开始时间
            start_time = time.time()

            # 执行代码
            result = self.executor.execute_python_code(code_text)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 添加块名称到结果中
            result["block_name"] = block.name
            result["execution_time"] = execution_time

            # 格式化显示结果
            self.formatter.format_execution_result(code_text, result, block.name)

            # 记录到历史
            execution_record = {
                "code": code_text,
                "result": result,
                "block_name": block.name,
                "timestamp": time.time(),
                "execution_time": execution_time,
                "success": self._basic_execution_check(result),  # 使用基础检查
            }
            self.execution_history.append(execution_record)

            # 使用 EnhancedErrorAnalyzer 生成智能反馈
            if not result.get("success"):
                self._send_intelligent_feedback(result)

            results.append(result)

            # 更新代码块管理器
            self.code_block_manager.add_block(block)
            self.code_block_manager.update_block_result(block.name, result, execution_time)
        return results

    def _send_intelligent_feedback(self, result: Dict[str, Any]):
        """使用 EnhancedErrorAnalyzer 发送智能反馈"""
        error_info = result.get("error", "")
        traceback_info = result.get("traceback", "")

        # 使用增强的错误分析器
        error_analysis = self.error_analyzer.analyze_error(error_info, traceback_info)

        # 构建智能反馈
        feedback = {
            "message": "代码执行失败，已分析错误原因",
            "error_analysis": {
                "type": error_analysis["error_type"],
                "severity": error_analysis["severity"],
                "compressed_info": error_analysis["compressed_info"],
                "fix_suggestions": error_analysis["fix_suggestions"][:2],  # 只发送前2个建议
            },
            "success": False,
        }

        feedback_json = json.dumps(feedback, ensure_ascii=False)
        self.client.send_feedback(feedback_json)

    def _send_validation_feedback(self, failure_reason: str, validation_details: Dict[str, Any]):
        """发送验证失败的反馈给AI"""
        feedback = {
            "message": f"执行结果不符合预期: {failure_reason}",
            "validation_details": validation_details,
            "expected_output": self.expected_output,
            "improvement_needed": True,
            "validation_type": "result_validation",
        }

        feedback_json = json.dumps(feedback, ensure_ascii=False)
        self.client.send_feedback(feedback_json)

    def _process_execution_result(self, result_content, instruction, task_type=None):
        """后处理执行结果，强制标准化格式"""
        from datetime import datetime

        # 使用传入的task_type，如果没有则使用general
        task_type = task_type or "general"

        # 强制标准化结果格式
        if not isinstance(result_content, dict):
            result_content = {
                "data": result_content,
                "status": "success" if result_content else "error",
                "summary": "执行完成" if result_content else "执行失败",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "auto_wrapped": True,
                },
            }
        else:
            # 确保必要字段存在
            result_content.setdefault("status", "success")
            result_content.setdefault("summary", "操作完成")
            result_content.setdefault("metadata", {})
            result_content["metadata"].update(
                {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "instruction_hash": hashlib.md5(instruction.encode()).hexdigest(),
                }
            )

        # 应用任务类型特定的格式化
        processed_result = self.formatter.format_task_type_result(result_content, task_type)
        return processed_result

    def run(
        self,
        instruction: str | None = None,
        system_prompt: str | None = None,
        task_type: str | None = None,
    ):
        """执行方法 - 支持单轮内有限次数优化"""
        if instruction and system_prompt:
            # 只有直接生成代码一种情况
            self.instruction = instruction
            self.system_prompt = system_prompt
        elif instruction and not system_prompt:
            # 可能是直接生成代码，也可能是标准化指令失败的情况
            self.instruction = instruction
            self.system_prompt = get_base_aiforge_prompt(
                optimize_tokens=self.optimization.get("optimize_tokens", True)
            )
        elif not instruction and system_prompt:
            self.instruction = "请根据系统提示生成代码"
            self.system_prompt = system_prompt
        elif not instruction and not system_prompt:
            return []

        # 存储task_type供后续使用
        self.task_type = task_type

        # 单轮内最大优化次数
        max_optimization_attempts = getattr(self, "max_optimization_attempts", 3)

        self.console.print(
            f"[yellow]开始处理任务指令，最大尝试轮数{self.max_rounds}，单轮最大优化次数{max_optimization_attempts}[/yellow]",  # noqa 501
            style="bold",
        )

        rounds = 1
        success = False

        while rounds <= self.max_rounds:
            if rounds > 1:
                time.sleep(0.1)  # 100ms 延迟

            self.console.print(f"\n[cyan]===== 第 {rounds} 轮执行 =====[/cyan]")

            # 执行单轮，包含内部优化循环
            round_success = self._execute_single_round_with_optimization(
                rounds, max_optimization_attempts
            )

            if round_success:
                success = True
                self.console.print(f"🎉 第 {rounds} 轮执行成功，任务完成！", style="bold green")
                break
            else:
                self.console.print(f"⚠️ 第 {rounds} 轮执行失败，进入下一轮重新开始", style="yellow")
                # 重置会话历史，为下一轮提供干净的环境
                if hasattr(self.client, "reset_conversation"):
                    self.client.reset_conversation()

            rounds += 1

        # 使用格式化器显示总结
        self.formatter.format_execution_summary(
            rounds - 1 if not success else rounds,
            self.max_rounds,
            len(self.execution_history),
            success,
        )

        return self.execution_history

    def _execute_single_round_with_optimization(
        self, round_num: int, max_optimization_attempts: int
    ) -> bool:
        """执行单轮，包含内部优化循环"""

        optimization_attempt = 1

        while optimization_attempt <= max_optimization_attempts:
            self.console.print(
                f"🔄 第 {round_num} 轮，第 {optimization_attempt} 次尝试", style="dim cyan"
            )

            # 第一步：代码生成
            self.console.print("🤖 正在生成代码...", style="dim white")

            if optimization_attempt == 1:
                # 第一次尝试：使用原始指令
                response = self.client.generate_code(self.instruction, self.system_prompt)
            else:
                # 后续尝试：使用历史上下文（包含之前的反馈）
                response = self.client.generate_code(
                    self.instruction, self.system_prompt, use_history=True
                )

            if not response:
                self.console.print(f"[red]第 {optimization_attempt} 次尝试：LLM 未返回响应[/red]")
                optimization_attempt += 1
                continue

            # 第二步：代码提取
            code_blocks = self.executor.extract_code_blocks(response)
            if not code_blocks:
                self.console.print(
                    f"[yellow]第 {optimization_attempt} 次尝试：未找到可执行的代码块[/yellow]"
                )
                optimization_attempt += 1
                continue

            self.console.print(f"📝 找到 {len(code_blocks)} 个代码块")

            # 第三步：代码执行
            self.process_code_execution(code_blocks)

            # 第四步：结果验证
            if not self.execution_history:
                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行失败[/red]")
                optimization_attempt += 1
                continue

            last_execution = self.execution_history[-1]

            # 检查基础执行是否成功
            if not (
                last_execution["result"].get("success") and last_execution["result"].get("result")
            ):
                # 代码执行错误，发送错误反馈
                if not last_execution["result"].get("success"):
                    self._send_intelligent_feedback(last_execution["result"])

                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行出错[/red]")
                optimization_attempt += 1
                continue

            # 处理执行结果
            processed_result = self._process_execution_result(
                last_execution["result"].get("result"),
                self.instruction,
                getattr(self, "task_type", None),
            )
            last_execution["result"]["result"] = processed_result

            # 第五步：智能验证
            is_valid, failure_reason, validation_details = (
                self._validate_execution_result_intelligent(
                    last_execution["result"],
                    self.instruction,
                    getattr(self, "task_type", None),
                )
            )

            if is_valid:
                # 验证通过，标记成功
                last_execution["success"] = True
                # 同步更新 executor.history
                if hasattr(self, "executor") and self.executor.history:
                    for history_entry in reversed(self.executor.history):
                        if history_entry.get("code") == last_execution["code"]:
                            history_entry["success"] = True
                            break

                self.console.print(
                    f"✅ 第 {optimization_attempt} 次尝试验证通过！", style="bold green"
                )
                return True
            else:
                # 验证失败
                last_execution["success"] = False

                if optimization_attempt < max_optimization_attempts:
                    # 还有优化机会，发送优化的反馈
                    self.console.print(
                        f"⚠️ 第 {optimization_attempt} 次尝试验证失败: {failure_reason}，发送优化反馈",
                        style="yellow",
                    )
                    # 使用优化的反馈方法，传入尝试次数
                    self._send_contextual_feedback(
                        failure_reason, validation_details, optimization_attempt
                    )
                    optimization_attempt += 1
                else:
                    # 已达到最大优化次数，放弃当前轮
                    self.console.print(
                        f"❌ 第 {optimization_attempt} 次尝试验证失败，已达到最大优化次数，放弃当前轮",
                        style="red",
                    )
                    return False

        # 所有优化尝试都失败
        self.console.print(f"❌ 单轮内 {max_optimization_attempts} 次优化尝试全部失败", style="red")
        return False

    def _send_optimized_validation_feedback(
        self, failure_reason: str, validation_details: Dict[str, Any], attempt_num: int
    ):
        """发送优化的验证失败反馈给AI"""

        # 获取配置的最大反馈长度
        max_length = self.optimization.get("max_feedback_length", 200)

        # 根据尝试次数决定反馈详细程度
        if self._should_send_detailed_feedback(attempt_num):
            # 详细反馈用于首次失败
            feedback = self._build_detailed_feedback(failure_reason, validation_details)
        else:
            # 简化反馈用于重复失败
            feedback = self._build_simple_feedback(failure_reason)

        # 应用 TOKEN 长度限制
        feedback_json = json.dumps(feedback, ensure_ascii=False)
        if len(feedback_json) > max_length:
            feedback_json = self._truncate_feedback(feedback_json, max_length)

        self.client.send_feedback(feedback_json)

    def _should_send_detailed_feedback(self, attempt_num: int) -> bool:
        """根据尝试次数决定反馈详细程度"""
        # 第一次失败：发送详细反馈
        # 后续失败：发送简化反馈
        return attempt_num == 1

    def _build_detailed_feedback(
        self, failure_reason: str, validation_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建详细反馈信息"""
        compressed_reason = self._compress_failure_reason(failure_reason)
        key_issues = self._extract_key_validation_issues(validation_details)

        return {
            "type": "validation_fail",
            "reason": compressed_reason,
            "issues": key_issues[:2],  # 最多2个关键问题
            "expected": self._compress_expected_output(),
            "validation_details": validation_details,
            "improvement_needed": True,
        }

    def _build_simple_feedback(self, failure_reason: str) -> Dict[str, Any]:
        """构建简化反馈信息"""
        return {
            "type": "retry",
            "hint": self._compress_failure_reason(failure_reason)[:30],  # 只保留30字符提示
            "retry": True,
        }

    def _compress_failure_reason(self, reason: str) -> str:
        """压缩失败原因描述"""
        # 移除冗余词汇，保留核心信息
        compressed = reason.replace("执行结果不符合预期: ", "")
        compressed = compressed.replace("验证失败: ", "")
        compressed = compressed.replace("本地验证失败: ", "")
        compressed = compressed.replace("业务逻辑验证失败: ", "")
        compressed = compressed.replace("AI验证失败: ", "")
        return compressed[:50]  # 限制长度

    def _extract_key_validation_issues(self, details: Dict[str, Any]) -> List[str]:
        """提取关键验证问题"""
        issues = []
        validation_type = details.get("validation_type", "")

        if validation_type == "local_basic":
            issues.append("基础验证失败")
        elif validation_type == "local_business":
            issues.append("业务逻辑错误")
        elif validation_type == "ai_deep":
            issues.append("目标未达成")
        else:
            issues.append("验证失败")

        return issues

    def _compress_expected_output(self) -> Dict[str, Any]:
        """压缩预期输出信息"""
        if not self.expected_output:
            return {}

        # 只保留关键字段
        compressed = {
            "type": self.expected_output.get("expected_data_type", "dict"),
            "fields": self.expected_output.get("required_fields", [])[:3],  # 最多3个字段
        }

        # 添加关键验证规则
        validation_rules = self.expected_output.get("validation_rules", {})
        if validation_rules.get("non_empty_fields"):
            compressed["non_empty"] = validation_rules["non_empty_fields"][:2]  # 最多2个

        return compressed

    def _truncate_feedback(self, feedback_json: str, max_length: int) -> str:
        """截断反馈信息以符合长度限制"""
        if len(feedback_json) <= max_length:
            return feedback_json

        try:
            feedback = json.loads(feedback_json)

            # 逐步移除非关键信息
            if "validation_details" in feedback:
                del feedback["validation_details"]

            if "expected" in feedback and len(json.dumps(feedback)) > max_length:
                feedback["expected"] = {}

            if "issues" in feedback and len(json.dumps(feedback)) > max_length:
                feedback["issues"] = feedback["issues"][:1]  # 只保留1个问题

            truncated = json.dumps(feedback, ensure_ascii=False)

            # 如果还是太长，进行硬截断
            if len(truncated) > max_length:
                truncated = truncated[: max_length - 3] + "..."

            return truncated
        except Exception:
            # 如果解析失败，直接截断
            return feedback_json[: max_length - 3] + "..."

    def _send_contextual_feedback(
        self, failure_reason: str, validation_details: Dict[str, Any], attempt_num: int
    ):
        """根据上下文发送适当详细程度的反馈"""
        # 使用优化的反馈方法
        self._send_optimized_validation_feedback(failure_reason, validation_details, attempt_num)

    def done(self):
        """任务完成清理"""
        pass


# AIForgeManager 类保持不变
class AIForgeManager:
    """AIForge任务管理器"""

    def __init__(self, llm_manager: AIForgeLLMManager):
        self.llm_manager = llm_manager
        self.tasks = []

    def new_task(
        self,
        instruction: str | None = None,
        client: AIForgeLLMClient = None,
    ) -> AIForgeTask:
        """创建新任务"""
        if not client:
            client = self.llm_manager.get_client()

        task = AIForgeTask(
            client,
            self.llm_manager.config.get_max_rounds(),
            self.llm_manager.config.get_optimization_config(),
            self.llm_manager.config.get_max_optimization_attempts(),
        )
        if instruction:
            task.instruction = instruction
        self.tasks.append(task)
        return task
