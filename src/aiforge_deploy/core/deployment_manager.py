from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum
from .config_manager import DeploymentConfigManager


class DeploymentType(Enum):
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CLOUD_AWS = "aws"
    CLOUD_AZURE = "azure"
    CLOUD_GCP = "gcp"
    CLOUD_ALIYUN = "aliyun"


class DeploymentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class BaseDeploymentProvider(ABC):
    """部署提供商基类"""

    def __init__(self, config_manager: DeploymentConfigManager):
        self.config_manager = config_manager
        self.deployment_type = None

    @abstractmethod
    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署服务"""
        pass

    @abstractmethod
    async def status(self) -> Dict[str, Any]:
        """获取部署状态"""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """停止服务"""
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """清理资源"""
        pass


class DeploymentManager:
    """统一部署管理器"""

    def __init__(self, config_manager: Optional[DeploymentConfigManager] = None):
        self.config_manager = config_manager or DeploymentConfigManager()
        self.providers: Dict[DeploymentType, BaseDeploymentProvider] = {}
        self._provider_factories = {
            DeploymentType.DOCKER: self._create_docker_provider,
            DeploymentType.KUBERNETES: self._create_kubernetes_provider,
            DeploymentType.CLOUD_AWS: self._create_aws_provider,
            DeploymentType.CLOUD_AZURE: self._create_azure_provider,
            DeploymentType.CLOUD_GCP: self._create_gcp_provider,
            DeploymentType.CLOUD_ALIYUN: self._create_aliyun_provider,
        }

    def _get_provider(self, deployment_type: DeploymentType) -> BaseDeploymentProvider:
        """按需获取部署提供商"""
        if deployment_type not in self.providers:
            if deployment_type not in self._provider_factories:
                raise ValueError(f"Unsupported deployment type: {deployment_type}")

            factory = self._provider_factories[deployment_type]
            self.providers[deployment_type] = factory()

        return self.providers[deployment_type]

    def _create_docker_provider(self) -> BaseDeploymentProvider:
        """创建Docker提供商"""
        from ..docker.docker_provider import DockerDeploymentProvider

        return DockerDeploymentProvider(self.config_manager)

    def _create_kubernetes_provider(self) -> BaseDeploymentProvider:
        """创建Kubernetes提供商"""
        from ..kubernetes.k8s_provider import KubernetesDeploymentProvider

        return KubernetesDeploymentProvider(self.config_manager)

    def _create_aws_provider(self) -> BaseDeploymentProvider:
        """创建AWS提供商"""
        from ..cloud.aws.provider import AWSDeploymentProvider

        return AWSDeploymentProvider(self.config_manager)

    def _create_azure_provider(self) -> BaseDeploymentProvider:
        """创建Azure提供商"""
        from ..cloud.azure.provider import AzureDeploymentProvider

        return AzureDeploymentProvider(self.config_manager)

    def _create_gcp_provider(self) -> BaseDeploymentProvider:
        """创建GCP提供商"""
        from ..cloud.gcp.provider import GCPDeploymentProvider

        return GCPDeploymentProvider(self.config_manager)

    def _create_aliyun_provider(self) -> BaseDeploymentProvider:
        """创建阿里云提供商"""
        from ..cloud.aliyun.provider import AliyunDeploymentProvider

        return AliyunDeploymentProvider(self.config_manager)

    async def deploy(self, deployment_type: DeploymentType, **kwargs) -> Dict[str, Any]:
        """统一部署入口"""
        provider = self._get_provider(deployment_type)
        return await provider.deploy(**kwargs)

    async def status(self, deployment_type: DeploymentType) -> Dict[str, Any]:
        """获取部署状态"""
        provider = self._get_provider(deployment_type)
        return await provider.status()

    async def stop(self, deployment_type: DeploymentType) -> bool:
        """停止部署"""
        provider = self._get_provider(deployment_type)
        return await provider.stop()

    async def deep_cleanup(self, deployment_type: DeploymentType) -> bool:
        """深度清理部署资源"""
        provider = self._get_provider(deployment_type)
        if hasattr(provider, "deep_cleanup"):
            return await provider.deep_cleanup()
        else:
            return await provider.cleanup()

    async def cleanup(self, deployment_type: DeploymentType) -> bool:
        """清理部署资源"""
        provider = self._get_provider(deployment_type)
        return await provider.cleanup()

    def get_available_providers(self) -> List[DeploymentType]:
        """获取可用的部署提供商类型"""
        return list(self._provider_factories.keys())

    def get_loaded_providers(self) -> List[DeploymentType]:
        """获取已加载的部署提供商"""
        return list(self.providers.keys())

    def is_provider_loaded(self, deployment_type: DeploymentType) -> bool:
        """检查提供商是否已加载"""
        return deployment_type in self.providers

    def unload_provider(self, deployment_type: DeploymentType) -> bool:
        """卸载指定的提供商"""
        if deployment_type in self.providers:
            del self.providers[deployment_type]
            return True
        return False

    def clear_all_providers(self):
        """清理所有已加载的提供商"""
        self.providers.clear()
