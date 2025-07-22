from typing import Dict, List, Optional, Any
from .template_extension import DomainTemplateExtension


class ExtensionManager:
    """扩展管理器"""

    def __init__(self):
        self.template_extensions: List[DomainTemplateExtension] = []
        self.extension_registry: Dict[str, DomainTemplateExtension] = {}

    def register_template_extension(self, extension: DomainTemplateExtension) -> bool:
        """注册模板扩展"""
        try:
            # 按优先级插入
            priority = extension.get_priority()
            inserted = False

            for i, existing_ext in enumerate(self.template_extensions):
                if priority > existing_ext.get_priority():
                    self.template_extensions.insert(i, extension)
                    inserted = True
                    break

            if not inserted:
                self.template_extensions.append(extension)

            self.extension_registry[extension.domain_name] = extension
            return True
        except Exception:
            return False

    def find_template_match(self, standardized_instruction: Dict[str, Any]) -> Optional[Dict]:
        """查找匹配的模板扩展"""
        for extension in self.template_extensions:
            if extension.can_handle(standardized_instruction):
                match = extension.get_template_match(standardized_instruction)
                if match:
                    return match
        return None

    def get_extension(self, domain_name: str) -> Optional[DomainTemplateExtension]:
        """获取指定领域的扩展"""
        return self.extension_registry.get(domain_name)

    def list_extensions(self) -> List[str]:
        """列出所有已注册的扩展"""
        return list(self.extension_registry.keys())
