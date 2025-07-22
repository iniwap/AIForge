import json
import time
import hashlib
from rich.console import Console
from typing import Optional, List, Dict, Any


from ..llm.llm_manager import AIForgeLLMManager
from ..llm.llm_client import AIForgeLLMClient
from ..execution.executor import AIForgeExecutor
from ..optimization.feedback_optimizer import FeedbackOptimizer
from ..formatting.result_formatter import AIForgeResultFormatter
from ..execution.code_blocks import CodeBlockManager, CodeBlock
from ..prompts.enhanced_prompts import get_base_aiforge_prompt
from .enhanced_error_analyzer import EnhancedErrorAnalyzer


class AIForgeTask:
    """AIForge 任务执行器"""

    def __init__(self, llm_client: AIForgeLLMClient, max_rounds, optimization):
        self.client = llm_client
        self.executor = AIForgeExecutor()
        self.console = Console()

        self.formatter = AIForgeResultFormatter(self.console)
        self.code_block_manager = CodeBlockManager()
        self.error_analyzer = EnhancedErrorAnalyzer()

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.optimization = optimization
        self.execution_history = []
        self.feedback_optimizer = (
            FeedbackOptimizer() if optimization.get("optimize_tokens", True) else None
        )

    def _is_execution_truly_successful(self, result):
        """判断执行是否真正成功（包括业务逻辑）"""
        # 首先检查代码执行是否成功
        if not result.get("success", False):
            return False

        # 然后检查业务逻辑是否成功
        result_content = result.get("result")
        if isinstance(result_content, dict):
            status = result_content.get("status")
            if status == "error":
                return False
            elif status == "success":
                return True

        # 如果没有明确的状态，但有数据且无错误，认为成功
        return result_content is not None

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
                "success": self._is_execution_truly_successful(result),
            }
            self.execution_history.append(execution_record)
            results.append(result)

            # 更新代码块管理器
            self.code_block_manager.add_block(block)
            self.code_block_manager.update_block_result(block.name, result, execution_time)

        # 使用 EnhancedErrorAnalyzer 生成智能反馈
        if not result.get("success"):
            self._send_intelligent_feedback(result)

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

    def _is_task_successful(self, result_content):
        """通用的任务成功判断逻辑"""
        if not isinstance(result_content, dict):
            return False

        # 优先级1: 明确的状态字段
        status = result_content.get("status")
        if status == "success":
            return True
        elif status == "error":
            return False

        # 优先级2: 传统的results字段
        if result_content.get("results"):
            return True

        # 优先级3: 有数据且无错误
        if result_content.get("data") is not None and not result_content.get("error"):
            return True

        return False

    def run(
        self,
        instruction: str | None = None,
        system_prompt: str | None = None,
        task_type: str | None = None,
    ):
        """执行方法"""
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

        self.console.print(
            f"[yellow]开始处理任务指令，最大尝试轮数{self.max_rounds}[/yellow]",
            style="bold",
        )

        rounds = 1
        success = False

        while rounds <= self.max_rounds:
            if rounds > 1:
                time.sleep(0.1)  # 100ms 延迟

            self.console.print(f"\n[cyan]===== 第 {rounds} 轮执行 =====[/cyan]")

            self.console.print("🤖 正在生成代码...", style="dim white")
            # 第一轮不使用历史，后续轮次使用历史上下文
            if rounds == 1:
                response = self.client.generate_code(self.instruction, self.system_prompt)
            else:
                # 后续轮次使用带历史的生成方法
                response = self.client.generate_code(
                    self.instruction, self.system_prompt, use_history=True
                )

            if not response:
                self.console.print(f"[red]第 {rounds} 轮：LLM 未返回响应[/red]")
                rounds += 1
                continue

            # 提取代码块
            code_blocks = self.executor.extract_code_blocks(response)
            if not code_blocks:
                self.console.print(f"[yellow]第 {rounds} 轮：未找到可执行的代码块[/yellow]")
                rounds += 1
                continue

            self.console.print(f"📝 找到 {len(code_blocks)} 个代码块")

            self.process_code_execution(code_blocks)

            # 检查是否成功
            if self.execution_history:
                last_execution = self.execution_history[-1]
                if last_execution["result"].get("success") and last_execution["result"].get(
                    "result"
                ):
                    processed_result = self._process_execution_result(
                        last_execution["result"].get("result"),
                        self.instruction,
                        getattr(self, "task_type", None),
                    )
                    last_execution["result"]["result"] = processed_result

                    if self._is_task_successful(last_execution["result"].get("result")):
                        # 只有业务逻辑也成功时才标记为成功
                        last_execution["success"] = True
                        # 同时需要更新 executor.history
                        if hasattr(self, "executor") and self.executor.history:
                            for history_entry in reversed(self.executor.history):
                                if history_entry.get("code") == last_execution["code"]:
                                    # 这里也需要检查业务逻辑成功
                                    if self._is_task_successful(
                                        history_entry.get("result", {}).get("__result__")
                                    ):
                                        history_entry["success"] = True
                                    break
                        success = True
                        self.console.print(
                            f"🎉 第 {rounds} 轮执行成功，任务完成！", style="bold green"
                        )
                        break

            rounds += 1

        # 使用格式化器显示总结
        self.formatter.format_execution_summary(
            rounds - 1 if rounds > 1 else rounds,
            self.max_rounds,
            len(self.execution_history),
            success,
        )

        return self.execution_history

    def done(self):
        """任务完成清理"""
        pass


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
        )
        if instruction:
            task.instruction = instruction
        self.tasks.append(task)
        return task
