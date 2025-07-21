from abc import ABC, abstractmethod
from typing import Any, Optional


class CachedModuleExecutor(ABC):
    """缓存模块执行器接口"""

    @abstractmethod
    def execute(self, module: Any, instruction: str, **kwargs) -> Optional[Any]:
        """执行缓存的模块"""
        pass

    @abstractmethod
    def can_handle(self, module: Any) -> bool:
        """判断是否能处理该模块"""
        pass
