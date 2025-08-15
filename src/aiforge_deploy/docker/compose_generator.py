from typing import Dict, Any
import yaml
from ..core.config_manager import DeploymentConfigManager


class ComposeGenerator:
    """Docker Compose文件生成器"""

    def __init__(self, config_manager: DeploymentConfigManager):
        self.config_manager = config_manager

    def generate(self, dev_mode: bool = False, enable_searxng: bool = False, **kwargs) -> str:
        """生成Docker Compose配置"""
        docker_config = self.config_manager.get_docker_config()
        aiforge_config = self.config_manager.get_aiforge_config_for_deployment()

        compose_config = {
            "version": "3.8",
            "services": {},
            "networks": {"aiforge-network": {"driver": "bridge"}},
        }

        # 生成AIForge服务配置
        compose_config["services"]["aiforge-engine"] = self._generate_aiforge_service(
            docker_config, aiforge_config, dev_mode
        )

        # 如果启用SearXNG，添加相关服务
        if enable_searxng:
            compose_config["services"]["aiforge-searxng"] = self._generate_searxng_service()
            compose_config["services"]["aiforge-nginx"] = self._generate_nginx_service()

        return yaml.dump(compose_config, default_flow_style=False)

    def _generate_aiforge_service(
        self, docker_config: Dict[str, Any], aiforge_config, dev_mode: bool
    ) -> Dict[str, Any]:
        """生成AIForge服务配置"""
        service_config = docker_config.get("services", {}).get("aiforge-engine", {})

        base_config = {
            "build": {
                "context": ".",
                "dockerfile": "docker/templates/Dockerfile",
                "args": docker_config.get("build_args", {}),
            },
            "container_name": "aiforge-engine",
            "ports": service_config.get("ports", ["8000:8000"]),
            "volumes": service_config.get(
                "volumes",
                ["./aiforge_work:/app/aiforge_work", "./logs:/app/logs", "./config:/app/config"],
            ),
            "environment": self._generate_environment_vars(aiforge_config),
            "networks": ["aiforge-network"],
            "restart": "unless-stopped",
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "40s",
            },
        }

        if dev_mode:
            # 开发模式特殊配置
            base_config["volumes"].append("./src:/app/src")
            base_config["environment"]["AIFORGE_DEV_MODE"] = "true"

        return base_config

    def _generate_environment_vars(self, aiforge_config) -> Dict[str, str]:
        """生成环境变量"""
        env_vars = {"AIFORGE_DOCKER_MODE": "true", "PYTHONPATH": "/app/src"}

        # 从AIForge配置中提取环境变量
        if aiforge_config:
            llm_config = aiforge_config.get_llm_config()
            if llm_config:
                for provider, config in llm_config.items():
                    if "api_key" in config:
                        env_key = f"{provider.upper()}_API_KEY"
                        env_vars[env_key] = config["api_key"]

        return env_vars

    def _generate_searxng_service(self) -> Dict[str, Any]:
        """生成SearXNG服务配置"""
        return {
            "image": "searxng/searxng:latest",
            "container_name": "aiforge-searxng",
            "expose": ["8080"],
            "volumes": ["./searxng:/etc/searxng:rw"],
            "networks": ["aiforge-network"],
            "restart": "unless-stopped",
            "profiles": ["searxng"],
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8080"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
            },
        }

    def _generate_nginx_service(self) -> Dict[str, Any]:
        """生成Nginx服务配置"""
        return {
            "image": "nginx:alpine",
            "container_name": "aiforge-nginx",
            "ports": ["55510:80"],
            "volumes": ["./docker/templates/nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro"],
            "depends_on": ["aiforge-searxng"],
            "networks": ["aiforge-network"],
            "restart": "unless-stopped",
            "profiles": ["searxng"],
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:80"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
            },
        }
