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

    @abstractmethod
    async def logs(self, service: Optional[str] = None) -> str:
        """获取日志"""
        pass


class DeploymentManager:
    """统一部署管理器"""

    def __init__(self, config_manager: Optional[DeploymentConfigManager] = None):
        self.config_manager = config_manager or DeploymentConfigManager()
        self.providers: Dict[DeploymentType, BaseDeploymentProvider] = {}
        self._register_providers()

    def _register_providers(self):
        """注册部署提供商"""
        from ..docker.docker_provider import DockerDeploymentProvider
        from ..kubernetes.k8s_provider import KubernetesDeploymentProvider
        from ..cloud.aws.provider import AWSDeploymentProvider
        from ..cloud.azure.provider import AzureDeploymentProvider
        from ..cloud.gcp.provider import GCPDeploymentProvider

        self.providers[DeploymentType.DOCKER] = DockerDeploymentProvider(self.config_manager)
        self.providers[DeploymentType.KUBERNETES] = KubernetesDeploymentProvider(
            self.config_manager
        )
        self.providers[DeploymentType.CLOUD_AWS] = AWSDeploymentProvider(self.config_manager)
        self.providers[DeploymentType.CLOUD_AZURE] = AzureDeploymentProvider(self.config_manager)
        self.providers[DeploymentType.CLOUD_GCP] = GCPDeploymentProvider(self.config_manager)

    async def deploy(self, deployment_type: DeploymentType, **kwargs) -> Dict[str, Any]:
        """统一部署入口"""
        provider = self.providers.get(deployment_type)
        if not provider:
            raise ValueError(f"Unsupported deployment type: {deployment_type}")

        return await provider.deploy(**kwargs)

    async def status(self, deployment_type: DeploymentType) -> Dict[str, Any]:
        """获取部署状态"""
        provider = self.providers.get(deployment_type)
        if not provider:
            raise ValueError(f"Unsupported deployment type: {deployment_type}")

        return await provider.status()

    async def stop(self, deployment_type: DeploymentType) -> bool:
        """停止部署"""
        provider = self.providers.get(deployment_type)
        if not provider:
            raise ValueError(f"Unsupported deployment type: {deployment_type}")

        return await provider.stop()

    async def cleanup(self, deployment_type: DeploymentType) -> bool:
        """清理部署资源"""
        provider = self.providers.get(deployment_type)
        if not provider:
            raise ValueError(f"Unsupported deployment type: {deployment_type}")

        return await provider.cleanup()

    def get_available_providers(self) -> List[DeploymentType]:
        """获取可用的部署提供商"""
        return list(self.providers.keys())
