import json
import time
import hashlib
from rich.console import Console
import re
from typing import Optional, List


from ..llm.llm_manager import AIForgeLLMManager
from ..llm.llm_client import AIForgeLLMClient
from ..execution.executor import AIForgeExecutor
from ..optimization.feedback_optimizer import FeedbackOptimizer
from ..formatting.result_formatter import AIForgeResultFormatter
from ..execution.code_blocks import CodeBlockManager, CodeBlock
from ..prompts.enhanced_prompts import get_enhanced_aiforge_prompt, detect_task_type


class AIForgeTask:
    def __init__(self, llm_client: AIForgeLLMClient, max_rounds, optimization):
        self.client = llm_client
        self.executor = AIForgeExecutor()
        self.console = Console()

        # 新增组件
        self.formatter = AIForgeResultFormatter(self.console)
        self.code_block_manager = CodeBlockManager()

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.optimization = optimization
        self.execution_history = []
        self.feedback_optimizer = (
            FeedbackOptimizer() if optimization.get("optimize_tokens", True) else None
        )

    def _compress_error(self, error_msg: str, max_length: int = 200) -> str:
        """压缩错误信息以减少token消耗 - 保留现有逻辑"""
        if not error_msg or len(error_msg) <= max_length:
            return error_msg

        # 提取关键错误信息的正则模式
        key_patterns = [
            r"(NameError|TypeError|ValueError|AttributeError|ImportError|SyntaxError): (.+)",
            r"line (\\d+)",
            r'File "([^"]+)"',
            r"in (.+)",
            r"(\\w+Exception): (.+)",
        ]

        compressed_parts = []

        # 按优先级提取关键信息
        for pattern in key_patterns:
            matches = re.findall(pattern, error_msg)
            if matches:
                for match in matches[:2]:  # 最多保留2个匹配项
                    if isinstance(match, tuple):
                        compressed_parts.extend([str(m) for m in match])
                    else:
                        compressed_parts.append(str(match))

        # 如果没有匹配到关键模式，截取开头部分
        if not compressed_parts:
            return error_msg[:max_length] + "..." if len(error_msg) > max_length else error_msg

        # 组合压缩后的信息
        compressed = " | ".join(compressed_parts[:5])  # 最多保留5个关键信息

        # 确保不超过最大长度
        if len(compressed) > max_length:
            compressed = compressed[: max_length - 3] + "..."

        return compressed

    def process_code_execution(self, code_blocks: List[str]) -> Optional[str]:
        """处理代码块执行并格式化结果 - 参考aipyapp的处理流程"""

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
                "success": result.get("success", False),
            }
            self.execution_history.append(execution_record)
            results.append(result)

            # 更新代码块管理器
            self.code_block_manager.add_block(block)
            self.code_block_manager.update_block_result(block.name, result, execution_time)

        # 生成结构化反馈
        if not result.get("success"):
            feedback_msg = self.formatter.format_structured_feedback([result])
            self.console.print("📤 发送执行结果反馈...", style="dim white")
            feedback_json = json.dumps(feedback_msg, ensure_ascii=False, default=str)
            self.client.send_feedback(feedback_json)

    def _process_execution_result(self, result_content, instruction):
        """后处理执行结果，确保格式一致性"""
        # 检测任务类型
        task_type = detect_task_type(instruction)

        # 应用任务类型特定的格式化
        processed_result = self.formatter.format_task_type_result(result_content, task_type)

        # 添加通用元数据
        if isinstance(processed_result, dict):
            processed_result.setdefault("metadata", {})
            processed_result["metadata"].update(
                {
                    "task_type": task_type,
                    "timestamp": time.time(),
                    "instruction_hash": hashlib.md5(instruction.encode()).hexdigest(),
                }
            )

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

    def run(self, instruction: str | None = None, system_prompt: str | None = None):
        """修改后的执行方法"""
        if instruction:
            self.instruction = instruction
        if system_prompt:
            self.system_prompt = system_prompt

        # 动态构建 system prompt - 使用增强版本
        if not system_prompt:
            self.system_prompt = get_enhanced_aiforge_prompt(
                self.instruction, optimize_tokens=self.optimization.get("optimize_tokens", True)
            )

        if not self.instruction:
            self.console.print("[red]没有提供指令[/red]")
            return None

        max_rounds = getattr(self, "max_rounds", 5)
        self.console.print(
            f"[yellow]开始处理任务指令，最大尝试轮数{max_rounds}[/yellow]",
            style="bold",
        )

        rounds = 1
        success = False

        while rounds <= max_rounds:
            self.console.print(f"\n[cyan]===== 第 {rounds} 轮执行 =====[/cyan]")

            # 生成代码
            self.console.print("🤖 正在生成代码...", style="dim white")
            response = self.client.generate_code(self.instruction, self.system_prompt)

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
                        last_execution["result"].get("result"), self.instruction
                    )
                    last_execution["result"]["result"] = processed_result

                    if self._is_task_successful(last_execution["result"].get("result")):
                        last_execution["success"] = True  # 明确标记为成功
                        success = True
                        self.console.print(
                            f"🎉 第 {rounds} 轮执行成功，任务完成！", style="bold green"
                        )
                        break

            rounds += 1

        # 使用格式化器显示总结
        self.formatter.format_execution_summary(
            rounds, max_rounds, len(self.execution_history), success
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
