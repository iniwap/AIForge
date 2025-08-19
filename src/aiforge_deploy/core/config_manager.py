from typing import Dict, Any, Optional
import os
from pathlib import Path


class DeploymentConfigManager:
    """统一部署配置管理器 - 支持所有部署方式的配置读取"""

    def __init__(self):
        self.deployment_config: Optional[Dict[str, Any]] = None
        self._runtime_overrides: Dict[str, Any] = {}

        # 存储各种部署方式的用户配置文件路径
        self._user_config_paths: Dict[str, Optional[str]] = {
            "docker_compose": None,  # docker-compose.yml
            "kubernetes": None,  # k8s.yaml
            "terraform": None,  # main.tf
            "deployment_config": None,  # 统一 TOML 配置
        }

    def initialize_deployment_config(
        self,
        deployment_config_file: Optional[str] = None,  # 统一 TOML 配置文件
        docker_compose_file: Optional[str] = None,  # Docker Compose 文件
        kubernetes_config_file: Optional[str] = None,  # K8s 配置文件
        terraform_config_file: Optional[str] = None,  # Terraform 配置文件
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """初始化部署专用配置 - 支持多种配置方式"""

        # 存储用户传递的各种配置文件路径
        self._user_config_paths.update(
            {
                "docker_compose": docker_compose_file,
                "kubernetes": kubernetes_config_file,
                "terraform": terraform_config_file,
                "deployment_config": deployment_config_file,
            }
        )

        # 按优先级加载配置
        config_loaded = False

        # 1. 优先加载特定部署方式的配置文件
        if docker_compose_file and Path(docker_compose_file).exists():
            self.deployment_config = self._load_docker_compose_file(docker_compose_file)
            config_loaded = True
        elif kubernetes_config_file and Path(kubernetes_config_file).exists():
            self.deployment_config = self._load_kubernetes_config_file(kubernetes_config_file)
            config_loaded = True
        elif terraform_config_file and Path(terraform_config_file).exists():
            self.deployment_config = self._load_terraform_config_file(terraform_config_file)
            config_loaded = True

        # 2. 如果没有特定配置，尝试加载统一 TOML 配置
        if not config_loaded and deployment_config_file and os.path.exists(deployment_config_file):
            self.deployment_config = self._load_deployment_config_file(deployment_config_file)
            config_loaded = True

        # 3. 都没有则返回 None，让各个 provider 使用默认值
        if not config_loaded:
            self.deployment_config = None

        # 应用运行时覆盖
        if self._runtime_overrides and self.deployment_config:
            self.deployment_config.update(self._runtime_overrides)

        return self.deployment_config

    def _load_docker_compose_file(self, compose_file: str) -> Dict[str, Any]:
        """加载 Docker Compose 配置文件"""
        import yaml

        try:
            with open(compose_file, "r", encoding="utf-8") as f:
                compose_content = yaml.safe_load(f)

            return {
                "docker": {
                    "compose_content": compose_content,
                    "compose_file_path": compose_file,
                    "config_source": "docker_compose_file",
                }
            }
        except Exception:
            return None

    def _load_kubernetes_config_file(self, k8s_file: str) -> Dict[str, Any]:
        """加载 Kubernetes 配置文件"""
        import yaml

        try:
            with open(k8s_file, "r", encoding="utf-8") as f:
                k8s_content = yaml.safe_load(f)

            return {
                "kubernetes": {
                    "manifest_content": k8s_content,
                    "manifest_file_path": k8s_file,
                    "config_source": "kubernetes_file",
                }
            }
        except Exception:
            return None

    def _load_terraform_config_file(self, tf_file: str) -> Dict[str, Any]:
        """加载 Terraform 配置文件"""
        try:
            with open(tf_file, "r", encoding="utf-8") as f:
                tf_content = f.read()

            return {
                "cloud": {
                    "terraform_content": tf_content,
                    "terraform_file_path": tf_file,
                    "config_source": "terraform_file",
                }
            }
        except Exception:
            return None

    def _load_deployment_config_file(self, config_file: str) -> Dict[str, Any]:
        """加载统一部署配置文件（TOML格式）"""
        import tomlkit

        try:
            with open(config_file, "rb") as f:
                config = tomlkit.load(f)

            result = {
                "docker": config.get("docker", {}),
                "kubernetes": config.get("kubernetes", {}),
                "cloud": config.get("cloud", {}),
                "deployment": config.get("deployment", {}),
            }

            # 标记配置来源
            for section in result.values():
                if isinstance(section, dict):
                    section["config_source"] = "toml_file"

            return result
        except Exception:
            return None

    def has_user_config(self) -> bool:
        """检查是否有用户传递的配置"""
        return self.deployment_config is not None

    def get_config_source(self) -> Optional[str]:
        """获取配置来源类型"""
        if not self.deployment_config:
            return None

        # 检查各个部分的配置来源
        for section in ["docker", "kubernetes", "cloud"]:
            if section in self.deployment_config:
                return self.deployment_config[section].get("config_source")
        return "unknown"

    # 各部署方式的配置获取方法
    def get_docker_config(self) -> Optional[Dict[str, Any]]:
        """获取 Docker 配置"""
        return self.deployment_config.get("docker", {}) if self.deployment_config else None

    def get_kubernetes_config(self) -> Optional[Dict[str, Any]]:
        """获取 Kubernetes 配置"""
        return self.deployment_config.get("kubernetes", {}) if self.deployment_config else None

    def get_cloud_config(self) -> Optional[Dict[str, Any]]:
        """获取云配置"""
        return self.deployment_config.get("cloud", {}) if self.deployment_config else None

    # 获取用户配置文件路径的方法
    def get_user_docker_compose_file_path(self) -> Optional[str]:
        """获取用户传递的 docker-compose.yml 文件路径"""
        return self._user_config_paths.get("docker_compose")

    def get_user_kubernetes_config_file_path(self) -> Optional[str]:
        """获取用户传递的 Kubernetes 配置文件路径"""
        return self._user_config_paths.get("kubernetes")

    def get_user_terraform_config_file_path(self) -> Optional[str]:
        """获取用户传递的 Terraform 配置文件路径"""
        return self._user_config_paths.get("terraform")

    def get_user_deployment_config_file_path(self) -> Optional[str]:
        """获取用户传递的统一部署配置文件路径"""
        return self._user_config_paths.get("deployment_config")
