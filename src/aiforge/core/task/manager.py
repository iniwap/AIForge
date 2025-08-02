from typing import Optional, Dict, Any
from rich.console import Console

from ...llm.llm_manager import AIForgeLLMManager
from ...llm.llm_client import AIForgeLLMClient
from .task import AIForgeTask


class AIForgeTaskManager:
    """任务管理器 - 负责任务的整体编排和生命周期管理"""

    def __init__(self, llm_manager: AIForgeLLMManager, components: Dict[str, Any] = None):
        self.llm_manager = llm_manager
        self.components = components or {}
        self.console = Console()

        # 活跃任务跟踪
        self.active_tasks = {}
        self.task_counter = 0

    def new_task(
        self, instruction: str | None = None, client: AIForgeLLMClient = None
    ) -> AIForgeTask:
        """创建新任务"""
        if not client:
            client = self.llm_manager.get_client()

        self.task_counter += 1
        task_id = f"task_{self.task_counter}"

        task = AIForgeTask(
            task_id=task_id,
            llm_client=client,
            max_rounds=self.llm_manager.config.get_max_rounds(),
            optimization=self.llm_manager.config.get_optimization_config(),
            max_optimization_attempts=self.llm_manager.config.get_max_optimization_attempts(),
            task_manager=self,
            components=self.components,
        )

        if instruction:
            task.instruction = instruction

        self.active_tasks[task_id] = task
        return task

    def complete_task(self, task_id: str):
        """完成任务"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    def get_active_task_count(self) -> int:
        """获取活跃任务数量"""
        return len(self.active_tasks)

    def get_task(self, task_id: str) -> Optional[AIForgeTask]:
        """获取指定任务"""
        return self.active_tasks.get(task_id)

    def list_active_tasks(self) -> Dict[str, AIForgeTask]:
        """列出所有活跃任务"""
        return self.active_tasks.copy()
