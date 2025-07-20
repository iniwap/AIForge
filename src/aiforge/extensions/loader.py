import importlib
import re
from typing import Dict, Any, List, Optional
from .extension_manager import ExtensionManager
from .template_extension import DomainTemplateExtension


class ExtensionLoader:
    """扩展动态加载器"""

    def __init__(self, extension_manager: ExtensionManager):
        self.extension_manager = extension_manager
        self.loaded_extensions = {}

    def load_from_config(self, config: Dict[str, Any]) -> bool:
        """从配置加载扩展"""
        try:
            templates = config.get("templates", [])

            for template_config in templates:
                if not self.load_template_extension(template_config):
                    return False

            # 加载领域模板
            domain_templates = config.get("domain_templates", {})
            if domain_templates:
                self.load_domain_templates(domain_templates)

            return True
        except Exception:
            return False

    def load_template_extension(self, config: Dict[str, Any]) -> bool:
        """加载单个模板扩展"""
        try:
            domain = config.get("domain")

            if "class" in config:
                # 直接指定类
                extension_class = config["class"]
                if isinstance(extension_class, str):
                    extension_class = self._import_class(extension_class)
            elif "module" in config and "class" in config:
                # 从模块导入类
                module_name = config["module"]
                class_name = config["class"]
                extension_class = self._import_class_from_module(module_name, class_name)
            else:
                return False

            # 创建扩展实例
            extension = extension_class(domain, config)
            return self.extension_manager.register_template_extension(extension)

        except Exception:
            return False

    def load_domain_templates(self, domain_templates: Dict[str, Any]):
        """加载领域模板"""
        for domain_name, domain_config in domain_templates.items():
            templates = domain_config.get("templates", {})
            keywords = domain_config.get("keywords", [])
            priority = domain_config.get("priority", 0)

            # 创建简化的领域扩展
            extension = self._create_simple_domain_extension(
                domain_name, templates, keywords, priority
            )
            self.extension_manager.register_template_extension(extension)

    def _import_class(self, class_path: str):
        """导入类"""
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    def _import_class_from_module(self, module_name: str, class_name: str):
        """从模块导入类"""
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    def _create_simple_domain_extension(
        self, domain_name: str, templates: Dict, keywords: List[str], priority: int
    ) -> DomainTemplateExtension:
        """创建简化的领域扩展"""

        class SimpleDomainExtension(DomainTemplateExtension):
            def __init__(self, domain: str, templates_dict: Dict, kw: List[str], prio: int):
                self.domain_name = domain
                self.templates = templates_dict
                self.keywords = kw
                self.config = {"priority": prio}

            def can_handle(self, standardized_instruction: Dict[str, Any]) -> bool:
                target = standardized_instruction.get("target", "").lower()
                return any(keyword.lower() in target for keyword in self.keywords)

            def get_template_match(
                self, standardized_instruction: Dict[str, Any]
            ) -> Optional[Dict]:
                target = standardized_instruction.get("target", "")
                for template_name, template_config in self.templates.items():
                    pattern = template_config.get("pattern", "")
                    if pattern and re.search(pattern, target, re.IGNORECASE):
                        return {
                            "template_name": template_name,
                            "template_config": template_config,
                            "domain": self.domain_name,
                        }
                return None

            def load_templates(self):
                pass  # 已在初始化时设置

        return SimpleDomainExtension(domain_name, templates, keywords, priority)
