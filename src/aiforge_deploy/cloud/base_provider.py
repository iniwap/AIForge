from abc import abstractmethod
from typing import Dict, Any, Optional
from ..core.deployment_manager import BaseDeploymentProvider


class CloudDeploymentProvider(BaseDeploymentProvider):
    """云部署提供商基类"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.cloud_config = {}

    @abstractmethod
    async def _create_instance(self, **kwargs) -> Dict[str, Any]:
        """创建云实例"""
        pass

    @abstractmethod
    async def _get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """获取实例状态"""
        pass

    @abstractmethod
    async def _terminate_instance(self, instance_id: str) -> bool:
        """终止实例"""
        pass

    @abstractmethod
    async def _get_instance_logs(self, instance_id: str) -> str:
        """获取实例日志"""
        pass

    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署到云平台"""
        try:
            # 1. 获取云配置
            provider_name = self.deployment_type.replace("cloud_", "")
            self.cloud_config = self.config_manager.get_cloud_config(provider_name)

            # 2. 创建实例
            instance_result = await self._create_instance(**kwargs)
            if not instance_result["success"]:
                return instance_result

            # 3. 等待实例启动
            instance_id = instance_result["instance_id"]
            await self._wait_for_instance_ready(instance_id)

            # 4. 部署AIForge应用
            deploy_result = await self._deploy_application(instance_id)

            return {
                "success": True,
                "instance_id": instance_id,
                "deployment_type": self.deployment_type,
                "deploy_result": deploy_result,
            }

        except Exception as e:
            return {"success": False, "message": f"Cloud deployment failed: {str(e)}"}

    async def _wait_for_instance_ready(self, instance_id: str, timeout: int = 300):
        """等待实例就绪"""
        import asyncio

        for _ in range(timeout // 10):
            status = await self._get_instance_status(instance_id)
            if status.get("state") == "running":
                return True
            await asyncio.sleep(10)

        raise TimeoutError(f"Instance {instance_id} not ready within {timeout} seconds")

    async def _deploy_application(self, instance_id: str) -> Dict[str, Any]:
        """在实例上部署AIForge应用"""
        # 生成部署脚本
        deploy_script = self._generate_deploy_script()

        # 执行部署脚本（具体实现由子类提供）
        return await self._execute_remote_script(instance_id, deploy_script)

    def _generate_deploy_script(self) -> str:
        """生成部署脚本"""
        aiforge_config = self.config_manager.get_aiforge_config_for_deployment()

        script = """#!/bin/bash
set -e

# 更新系统
sudo apt-get update

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装AIForge
pip3 install aiforge-deploy

# 创建配置文件
mkdir -p /opt/aiforge
cat > /opt/aiforge/aiforge.toml << 'EOF'
"""

        # 添加AIForge配置
        if aiforge_config:
            import tomlkit

            script += tomlkit.dumps(aiforge_config.to_dict())

        script += """
EOF

# 启动AIForge服务
cd /opt/aiforge
aiforge-deploy docker deploy --config aiforge.toml

echo "AIForge deployment completed successfully"
"""

        return script

    @abstractmethod
    async def _execute_remote_script(self, instance_id: str, script: str) -> Dict[str, Any]:
        """在远程实例上执行脚本"""
        pass

    async def status(self) -> Dict[str, Any]:
        """获取云部署状态"""
        # 实现获取所有相关实例状态的逻辑
        pass

    async def stop(self) -> bool:
        """停止云部署"""
        # 实现停止所有相关实例的逻辑
        pass

    async def cleanup(self) -> bool:
        """清理云资源"""
        # 实现清理所有相关云资源的逻辑
        pass

    async def logs(self, service: Optional[str] = None) -> str:
        """获取云部署日志"""
        # 实现获取实例日志的逻辑
        pass
