import json
import re
from typing import Dict, Any, Optional
from ..llm.llm_client import AIForgeLLMClient


class InstructionParser:
    """指令解析器 - 负责AI返回结果的解析和默认分析"""

    def __init__(self, llm_client: Optional[AIForgeLLMClient] = None):
        self.llm_client = llm_client

    def parse_standardized_instruction(self, response: str) -> Dict[str, Any]:
        """解析AI返回的标准化指令"""
        # 先尝试提取```json代码块
        code_block_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # 回退到直接提取JSON
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败时返回默认结构
        return self.get_default_analysis(response[:100])

    def get_default_analysis(self, instruction: str) -> Dict[str, Any]:
        """获取默认分析结果"""
        from .extractor import ParameterExtractor

        return {
            "task_type": "general",
            "action": "process",
            "target": instruction[:100],
            "parameters": {},
            "cache_key": f"general_{hash(instruction) % 10000}",
            "confidence": 0.3,
            "source": "default",
            "expected_output": ParameterExtractor.get_default_expected_output("general"),
        }
