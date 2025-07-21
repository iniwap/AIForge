from abc import ABC, abstractmethod
from typing import Any, Optional

"""
# 基本使用 - 使用默认执行器
forge = AIForgeCore("aiforge.toml")
result, code = forge.generate_and_execute_with_cache("获取天气信息")

# 自定义执行器
class WeatherModuleExecutor(CachedModuleExecutor):
    def can_handle(self, module):
        return hasattr(module, 'get_weather')

    def execute(self, module, instruction, **kwargs):
        return module.get_weather(kwargs.get('city', 'Beijing'))

# 添加自定义执行器
forge.add_module_executor(WeatherModuleExecutor())

# 带参数执行
result, code = forge.generate_and_execute_with_cache(
    "获取天气信息",
    city="Shanghai"
)
"""


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
