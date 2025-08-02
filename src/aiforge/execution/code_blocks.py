import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CodeBlock:
    """代码块数据结构"""

    code: str
    lang: str = "python"
    name: str = ""
    version: int = 1
    path: str = ""
    execution_time: float = 0.0
    success: bool = False
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class CodeBlockManager:
    """代码块管理器"""

    def __init__(self):
        self.blocks: Dict[str, CodeBlock] = {}
        self.execution_order: List[str] = []

    def parse_markdown_blocks(self, text: str) -> List[CodeBlock]:
        """从markdown文本中解析代码块"""
        blocks = []

        # 匹配 ```python...``` 格式
        pattern = r"```python\s*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            # 尝试 ```...``` 格式
            pattern = r"```\s*\n(.*?)\n```"
            matches = re.findall(pattern, text, re.DOTALL)

        for i, match in enumerate(matches):
            block = CodeBlock(code=match.strip(), name=f"block_{i+1}", version=1)
            blocks.append(block)

        return blocks

    def add_block(self, block: CodeBlock):
        """添加代码块到管理器"""
        self.blocks[block.name] = block
        if block.name not in self.execution_order:
            self.execution_order.append(block.name)

    def get_block(self, name: str) -> Optional[CodeBlock]:
        """获取指定名称的代码块"""
        return self.blocks.get(name)

    def get_execution_history(self) -> List[CodeBlock]:
        """获取按执行顺序排列的代码块历史"""
        return [self.blocks[name] for name in self.execution_order if name in self.blocks]

    def update_block_result(self, name: str, result: Dict[str, Any], execution_time: float = 0.0):
        """更新代码块的执行结果"""
        if name in self.blocks:
            self.blocks[name].result = result
            self.blocks[name].execution_time = execution_time
            self.blocks[name].success = result.get("success", False)

    def extract_code_blocks(self, text: str) -> List[str]:
        """从LLM响应中提取代码块"""
        import re

        # 匹配 ```python...``` 格式
        pattern = r"```python\s*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            # 尝试 ```...``` 格式
            pattern = r"```\s*\n(.*?)\n```"
            matches = re.findall(pattern, text, re.DOTALL)

        # 清理每个代码块
        cleaned_matches = []
        for match in matches:
            cleaned_code = match.strip()
            cleaned_matches.append(cleaned_code)

        return cleaned_matches
