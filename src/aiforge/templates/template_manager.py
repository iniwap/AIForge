# -*- coding: utf-8 -*-
"""
模板管理器 - 统一管理所有模板的注册、发现和调用
"""

from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import importlib
import inspect
from pathlib import Path


class TemplateType(Enum):
    """模板类型枚举"""

    SEARCH_DIRECT = "search_direct"
    SEARCH_GUIDED = "search_guided"
    SEARCH_FREE_FORM = "search_free_form"
    INSTRUCTION_GENERATION = "instruction_generation"
    CODE_GENERATION = "code_generation"
    DATA_PROCESSING = "data_processing"


class TemplateManager:
    """模板管理器 - 负责模板的注册、发现和统一调用"""

    def __init__(self, parameter_mapping_service=None):
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._template_configs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self.parameter_mapping_service = parameter_mapping_service

    def initialize(self):
        """初始化模板管理器，自动发现和注册模板"""
        if self._initialized:
            return

        # 注册搜索模板
        self._register_search_templates()

        # 可以在这里注册其他模板
        # self._register_other_templates()

        self._initialized = True

    def _validate_and_map_parameters(self, template: Dict[str, Any], kwargs: Dict[str, Any]):
        """使用参数映射服务进行参数验证和映射"""
        if self.parameter_mapping_service and template.get("func"):
            # 使用参数映射服务进行智能参数映射
            mapped_params = self.parameter_mapping_service.map_parameters(template["func"], kwargs)
            kwargs.update(mapped_params)

        # 原有的验证逻辑
        parameters = template.get("parameters", {})
        for param_name, param_info in parameters.items():
            if param_info.get("required", False) and param_name not in kwargs:
                raise ValueError(f"缺少必需参数: {param_name}")

    def _register_search_templates(self):
        """注册搜索相关模板"""
        try:
            from .search_template import (
                get_template_guided_search_instruction,
                get_free_form_ai_search_instruction,
                search_web,
            )

            # 注册引导式搜索模板
            self.register_template(
                template_id="search_guided",
                template_type=TemplateType.SEARCH_GUIDED,
                template_func=get_template_guided_search_instruction,
                description="引导式搜索指令生成模板，提供详细的CSS选择器和处理逻辑",
                parameters={
                    "search_query": {"type": "str", "required": True, "description": "搜索查询"},
                    "expected_output": {
                        "type": "dict",
                        "required": True,
                        "description": "期望输出",
                    },
                    "max_results": {"type": "int", "required": False, "description": "最大结果数"},
                    "min_abstract_len": {
                        "type": "str",
                        "required": False,
                        "description": "最少内容字数",
                    },
                },
            )

            # 注册自由形式搜索模板
            self.register_template(
                template_id="search_free_form",
                template_type=TemplateType.SEARCH_FREE_FORM,
                template_func=get_free_form_ai_search_instruction,
                description="自由形式搜索指令生成模板，允许创新性的搜索策略",
                parameters={
                    "search_query": {"type": "str", "required": True, "description": "搜索查询"},
                    "expected_output": {
                        "type": "dict",
                        "required": True,
                        "description": "期望输出",
                    },
                    "max_results": {"type": "int", "required": False, "description": "最大结果数"},
                    "min_abstract_len": {
                        "type": "str",
                        "required": False,
                        "description": "最少摘要字数",
                    },
                },
            )

            # 注册直接搜索函数
            self.register_template(
                template_id="search_direct",
                template_type=TemplateType.SEARCH_DIRECT,
                template_func=search_web,
                description="直接搜索执行函数，支持多搜索引擎",
                parameters={
                    "search_query": {"type": "str", "required": True, "description": "搜索查询"},
                    "max_results": {
                        "type": "int",
                        "required": False,
                        "default": 10,
                        "description": "最大结果数",
                    },
                    "min_abstract_len": {
                        "type": "str",
                        "required": False,
                        "description": "最少摘要字数",
                    },
                    "max_abstract_len": {
                        "type": "str",
                        "required": False,
                        "description": "最多摘要字数",
                    },
                },
            )

        except ImportError as e:
            print(f"[WARNING] 无法导入搜索模板: {e}")

    def register_template(
        self,
        template_id: str,
        template_type: TemplateType,
        template_func: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """注册模板"""
        self._templates[template_id] = {
            "id": template_id,
            "type": template_type,
            "func": template_func,
            "description": description,
            "parameters": parameters or {},
            "config": config or {},
            "module": template_func.__module__ if hasattr(template_func, "__module__") else None,
            "signature": str(inspect.signature(template_func)) if callable(template_func) else None,
        }

        # 保存配置
        if config:
            self._template_configs[template_id] = config.copy()

    def get_template(self, template_id: str, **kwargs) -> Optional[str]:
        """获取模板生成的指令"""
        if not self._initialized:
            self.initialize()

        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"未找到模板: {template_id}")

        try:
            # 验证参数
            self._validate_and_map_parameters(template, kwargs)

            # 调用模板函数
            result = template["func"](**kwargs)
            return result

        except Exception as e:
            raise RuntimeError(f"模板 {template_id} 执行失败: {e}")

    def execute_template(self, template_id: str, **kwargs) -> Any:
        """直接执行模板函数（用于非指令生成类模板）"""
        if not self._initialized:
            self.initialize()

        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"未找到模板: {template_id}")

        try:
            # 验证参数
            self._validate_and_map_parameters(template, kwargs)

            # 直接执行模板函数
            result = template["func"](**kwargs)
            return result

        except Exception as e:
            raise RuntimeError(f"模板 {template_id} 执行失败: {e}")

    def list_templates(self, template_type: Optional[TemplateType] = None) -> List[Dict[str, Any]]:
        """列出所有模板"""
        if not self._initialized:
            self.initialize()

        templates = []
        for template_id, template in self._templates.items():
            if template_type is None or template["type"] == template_type:
                templates.append(
                    {
                        "id": template_id,
                        "type": template["type"].value,
                        "description": template["description"],
                        "parameters": template["parameters"],
                        "signature": template["signature"],
                    }
                )

        return templates

    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板详细信息"""
        if not self._initialized:
            self.initialize()

        template = self._templates.get(template_id)
        if not template:
            return None

        return {
            "id": template["id"],
            "type": template["type"].value,
            "description": template["description"],
            "parameters": template["parameters"],
            "config": template["config"],
            "module": template["module"],
            "signature": template["signature"],
        }

    def update_template_config(self, template_id: str, config: Dict[str, Any]):
        """更新模板配置"""
        if template_id in self._templates:
            self._templates[template_id]["config"].update(config)
            self._template_configs[template_id] = self._templates[template_id]["config"].copy()

    def get_template_config(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板配置"""
        return self._template_configs.get(template_id)

    def discover_templates(self, module_path: str = "aiforge.templates"):
        """自动发现指定模块路径下的模板"""
        try:
            module = importlib.import_module(module_path)
            module_dir = Path(module.__file__).parent

            # 扫描模块文件
            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("_") or py_file.name == "__init__.py":
                    continue

                module_name = f"{module_path}.{py_file.stem}"
                try:
                    template_module = importlib.import_module(module_name)
                    self._register_module_templates(template_module, py_file.stem)
                except ImportError as e:
                    print(f"[WARNING] 无法导入模板模块 {module_name}: {e}")

        except Exception as e:
            print(f"[WARNING] 模板发现失败: {e}")

    def _register_module_templates(self, module, module_name: str):
        """注册模块中的模板函数"""
        # 查找以特定前缀命名的函数
        template_prefixes = ["get_", "generate_", "create_"]

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and any(attr_name.startswith(prefix) for prefix in template_prefixes):
                # 自动注册为模板
                template_id = f"{module_name}_{attr_name}"
                self.register_template(
                    template_id=template_id,
                    template_type=TemplateType.INSTRUCTION_GENERATION,
                    template_func=attr,
                    description=f"自动发现的模板函数: {attr_name}",
                    parameters=self._extract_function_parameters(attr),
                )

    def _extract_function_parameters(self, func: Callable) -> Dict[str, Any]:
        """从函数签名提取参数信息"""
        try:
            sig = inspect.signature(func)
            parameters = {}

            for param_name, param in sig.parameters.items():
                param_info = {"type": "any", "required": param.default == inspect.Parameter.empty}

                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default

                parameters[param_name] = param_info

            return parameters
        except Exception:
            return {}


# 全局模板管理器实例
template_manager = TemplateManager()


# 便捷函数
def get_template(template_id: str, **kwargs) -> Optional[str]:
    """获取模板指令的便捷函数"""
    return template_manager.get_template(template_id, **kwargs)


def execute_template(template_id: str, **kwargs) -> Any:
    """执行模板的便捷函数"""
    return template_manager.execute_template(template_id, **kwargs)


def list_templates(template_type: Optional[TemplateType] = None) -> List[Dict[str, Any]]:
    """列出模板的便捷函数"""
    return template_manager.list_templates(template_type)
