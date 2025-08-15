from typing import Dict, Any, Optional
from pathlib import Path
from aiforge.core.managers.config_manager import AIForgeConfigManager
from aiforge.config.config import AIForgeConfig


class DeploymentConfigManager(AIForgeConfigManager):
    """部署配置管理器 - 扩展核心配置管理器"""

    def __init__(self):
        super().__init__()
        self._deployment_config: Optional[Dict[str, Any]] = None

    def initialize_deployment_config(
        self, deployment_config_file: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """初始化部署专用配置"""

        # 1. 加载基础AIForge配置
        if not self.config:
            # 使用默认配置或从环境变量获取
            self.initialize_config(**kwargs)

        # 2. 加载部署配置
        if deployment_config_file and Path(deployment_config_file).exists():
            import tomlkit

            with open(deployment_config_file, "r", encoding="utf-8") as f:
                self._deployment_config = tomlkit.load(f)
        else:
            self._deployment_config = self._get_default_deployment_config()

        return self._deployment_config

    def _get_default_deployment_config(self) -> Dict[str, Any]:
        """获取默认部署配置"""
        return {
            "docker": {
                "registry": "docker.io",
                "namespace": "aiforge",
                "image_tag": "latest",
                "build_args": {"INSTALL_PACKAGES": "aiforge-engine aiforge-web"},
                "services": {
                    "aiforge-engine": {
                        "ports": ["8000:8000"],
                        "environment": {},
                        "volumes": [
                            "./aiforge_work:/app/aiforge_work",
                            "./logs:/app/logs",
                            "./config:/app/config",
                        ],
                    },
                    "aiforge-searxng": {
                        "image": "searxng/searxng:latest",
                        "ports": ["8080:8080"],
                        "profiles": ["searxng"],
                    },
                },
            },
            "kubernetes": {
                "namespace": "aiforge",
                "replicas": 1,
                "resources": {
                    "requests": {"cpu": "100m", "memory": "256Mi"},
                    "limits": {"cpu": "500m", "memory": "512Mi"},
                },
                "ingress": {"enabled": True, "host": "aiforge.local", "tls": False},
            },
            "cloud": {
                "aws": {
                    "region": "us-west-2",
                    "instance_type": "t3.micro",
                    "vpc_id": "",
                    "subnet_id": "",
                },
                "azure": {"location": "East US", "vm_size": "Standard_B1s"},
                "gcp": {"zone": "us-central1-a", "machine_type": "e2-micro"},
            },
        }

    def get_docker_config(self) -> Dict[str, Any]:
        """获取Docker部署配置"""
        return self._deployment_config.get("docker", {})

    def get_kubernetes_config(self) -> Dict[str, Any]:
        """获取Kubernetes部署配置"""
        return self._deployment_config.get("kubernetes", {})

    def get_cloud_config(self, provider: str) -> Dict[str, Any]:
        """获取云提供商配置"""
        return self._deployment_config.get("cloud", {}).get(provider, {})

    def get_aiforge_config_for_deployment(self) -> AIForgeConfig:
        """获取用于部署的AIForge配置"""
        return self.config
