from typing import Dict, Any, List
import tomlkit


class ExtensionConfig:
    """扩展配置管理器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.extensions_config = {}
        if config_path:
            self.load_config()

    def load_config(self):
        """从配置文件加载扩展配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = tomlkit.load(f)
                self.extensions_config = config.get("extensions", {})
        except Exception:
            self.extensions_config = {}

    def get_template_extensions(self) -> List[Dict[str, Any]]:
        """获取模板扩展配置"""
        return self.extensions_config.get("templates", [])

    def add_template_extension(self, domain: str, extension_config: Dict[str, Any]):
        """添加模板扩展配置"""
        if "templates" not in self.extensions_config:
            self.extensions_config["templates"] = []

        extension_config["domain"] = domain
        self.extensions_config["templates"].append(extension_config)
        self.save_config()

    def save_config(self):
        """保存配置到文件"""
        if not self.config_path:
            return

        try:
            config = {"extensions": self.extensions_config}
            with open(self.config_path, "w", encoding="utf-8") as f:
                tomlkit.dump(config, f)
        except Exception:
            pass
