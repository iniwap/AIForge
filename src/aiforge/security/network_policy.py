from typing import Dict, Any
from abc import ABC, abstractmethod


class NetworkPolicy(ABC):
    """网络策略基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def get_environment_variables(self) -> Dict[str, str]:
        """获取环境变量设置"""
        pass

    @abstractmethod
    def should_block_module(self, module_name: str) -> bool:
        """判断是否应该阻止模块导入"""
        pass

    @abstractmethod
    def should_allow_domain(self, domain: str) -> bool:
        """判断是否允许访问域名"""
        pass


class DisabledNetworkPolicy(NetworkPolicy):
    """禁用网络验证策略"""

    def get_environment_variables(self) -> Dict[str, str]:
        return {}

    def should_block_module(self, module_name: str) -> bool:
        return False

    def should_allow_domain(self, domain: str) -> bool:
        return True


class StrictNetworkPolicy(NetworkPolicy):
    """严格网络控制策略"""

    def get_environment_variables(self) -> Dict[str, str]:
        return {
            "HTTP_PROXY": "http://127.0.0.1:1",
            "HTTPS_PROXY": "http://127.0.0.1:1",
            "FTP_PROXY": "http://127.0.0.1:1",
            "SOCKS_PROXY": "http://127.0.0.1:1",
            "ALL_PROXY": "http://127.0.0.1:1",
            "NO_PROXY": "",
        }

    def should_block_module(self, module_name: str) -> bool:
        dangerous_modules = [
            "requests",
            "urllib",
            "http",
            "socket",
            "ssl",
            "ftplib",
            "smtplib",
            "poplib",
            "imaplib",
            "telnetlib",
            "xmlrpc",
        ]
        return any(module_name.startswith(dangerous) for dangerous in dangerous_modules)

    def should_allow_domain(self, domain: str) -> bool:
        return False


class FilteredNetworkPolicy(NetworkPolicy):
    """基于域名过滤的网络策略"""

    def get_environment_variables(self) -> Dict[str, str]:
        env_vars = {}

        if self.config.get("force_block_access", False):
            env_vars.update(
                {
                    "HTTP_PROXY": "http://127.0.0.1:1",
                    "HTTPS_PROXY": "http://127.0.0.1:1",
                    "ALL_PROXY": "http://127.0.0.1:1",
                }
            )

        return env_vars

    def should_block_module(self, module_name: str) -> bool:
        if self.config.get("force_block_modules", False):
            network_modules = ["requests", "urllib", "http", "socket"]
            return any(module_name.startswith(mod) for mod in network_modules)
        return False

    def should_allow_domain(self, domain: str) -> bool:
        if not self.config.get("domain_filtering_enabled", True):
            return True

        blacklist = self.config.get("domain_blacklist", [])
        if any(domain.endswith(blocked) for blocked in blacklist):
            return False

        whitelist = self.config.get("domain_whitelist", [])
        return any(domain.endswith(allowed) for allowed in whitelist)


class OpenNetworkPolicy(NetworkPolicy):
    """开放网络访问策略"""

    def get_environment_variables(self) -> Dict[str, str]:
        return {}

    def should_block_module(self, module_name: str) -> bool:
        return False

    def should_allow_domain(self, domain: str) -> bool:
        return True


class NetworkPolicyFactory:
    """网络策略工厂"""

    @staticmethod
    def create_policy(policy_level: str, config: Dict[str, Any], i18n_manager) -> NetworkPolicy:
        """根据策略级别创建相应的网络策略"""
        if policy_level == "unrestricted":
            return DisabledNetworkPolicy(config)
        elif policy_level == "strict":
            return StrictNetworkPolicy(config)
        elif policy_level == "filtered":
            return FilteredNetworkPolicy(config)
        elif policy_level == "permissive":
            return OpenNetworkPolicy(config)
        else:
            error_message = i18n_manager.t(
                "network.unknown_policy_level", policy_level=policy_level
            )
            raise ValueError(error_message)
