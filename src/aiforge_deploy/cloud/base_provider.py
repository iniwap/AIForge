import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import abstractmethod
from ..core.deployment_manager import BaseDeploymentProvider
from aiforge import GlobalI18nManager


class CloudDeploymentProvider(BaseDeploymentProvider):
    """云部署提供商基类 - 支持用户自定义配置"""

    def __init__(self, config_manager):
        super().__init__(config_manager)

        # 获取i18n管理器
        self._i18n_manager = GlobalI18nManager.get_instance()

        # 获取用户传递的云配置（可能为None）
        self.cloud_config = {}

        # 根据用户配置或默认配置设置脚本文件路径
        self._setup_script_file_paths()

    def _setup_script_file_paths(self):
        """设置脚本文件路径"""

        # 检查用户是否传递了自定义的脚本文件路径
        user_script_paths = self.config_manager.get_user_cloud_script_paths()

        if user_script_paths:
            # 用户传递了自定义的脚本文件路径
            self.script_files = {}
            for script_type, path in user_script_paths.items():
                if Path(path).exists():
                    self.script_files[script_type] = path
                else:
                    self.script_files[script_type] = self._get_default_script_file(script_type)
        else:
            # 使用默认配置
            self.script_files = {
                "deploy": self._get_default_script_file("deploy"),
                "setup": self._get_default_script_file("setup"),
                "cleanup": self._get_default_script_file("cleanup"),
            }

    def get_user_cloud_script_paths(self) -> Optional[Dict[str, str]]:
        """获取用户自定义的云部署脚本文件路径"""
        if not self._deployment_config:
            return None

        cloud_config = self._deployment_config.get("cloud", {})
        script_paths = cloud_config.get("script_paths", {})

        # 验证路径是否存在
        validated_paths = {}
        for script_type, path in script_paths.items():
            if isinstance(path, str) and Path(path).exists():
                validated_paths[script_type] = path

        return validated_paths if validated_paths else None

    def _get_default_script_file(self, script_type: str) -> str:
        """获取默认的脚本文件路径"""
        if self._is_source_environment():
            current_file = Path(__file__)
            templates_dir = current_file.parent / "templates"
            return str(templates_dir / f"{script_type}.sh")
        else:
            return self._get_template_path(f"{script_type}.sh")

    def _is_source_environment(self) -> bool:
        """检查是否在源码环境"""
        current_dir = Path.cwd()
        return (
            (current_dir / "src" / "aiforge").exists()
            and (
                current_dir / "src" / "aiforge_deploy" / "cloud" / "templates" / "deploy.sh"
            ).exists()
            and (current_dir / "pyproject.toml").exists()
        )

    def _get_template_path(self, filename: str) -> str:
        """获取模板文件路径"""
        try:
            from importlib import resources

            with resources.path("aiforge_deploy.cloud.templates", filename) as path:
                return str(path)
        except Exception:
            # 如果无法从包资源获取，回退到当前目录
            return filename

    async def _generate_deploy_script(self) -> str:
        """生成部署脚本"""
        # 使用模板文件或动态生成
        if "deploy" in self.script_files and Path(self.script_files["deploy"]).exists():
            # 使用模板文件
            with open(self.script_files["deploy"], "r") as f:
                script_template = f.read()

            # 替换模板变量（只使用部署相关的环境变量）
            script = script_template.replace("${DEPLOYMENT_TYPE}", self.deployment_type)
            script = script.replace("${CLOUD_PROVIDER}", self.deployment_type.replace("cloud_", ""))
            return script
        else:
            # 动态生成（不依赖 AIForge 配置）
            return self._generate_default_deploy_script()

    def _generate_default_deploy_script(self) -> str:
        """生成默认部署脚本（不依赖 AIForge 配置）"""
        script = """#!/bin/bash
set -e

echo "Starting AIForge deployment..."

# 更新系统
echo "Updating system packages..."
sudo apt-get update -y

# 安装Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装Python和pip
echo "Installing Python and pip..."
sudo apt-get install -y python3 python3-pip

# 安装AIForge
echo "Installing AIForge..."
pip3 install aiforge-deploy

# 创建工作目录
echo "Creating working directory..."
mkdir -p /opt/aiforge

# 启动AIForge服务（使用默认配置）
echo "Starting AIForge services..."
cd /opt/aiforge
aiforge-deploy docker deploy

echo "AIForge deployment completed successfully!"
echo "Access your AIForge instance at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
"""  # noqa 501

        return script

    # 其余方法保持不变，但移除所有对 aiforge_config 的引用
    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署到云平台"""
        region = kwargs.get("region", self.cloud_config.get("region", "us-west-2"))
        instance_type = kwargs.get(
            "instance_type", self.cloud_config.get("instance_type", "t3.medium")
        )

        print(self._i18n_manager.t("cloud.starting_deployment"))
        print("=" * 50)

        # 1. 环境检查
        env_check = await self._check_environment()
        if not env_check["success"]:
            return {"success": False, "message": "Environment check failed", "details": env_check}

        # 检查必要条件
        checks = env_check["checks"]
        if not checks["cloud_cli_available"]:
            print(f"\n{self._i18n_manager.t('cloud.cli_not_installed')}")
            return {"success": False, "message": "Cloud CLI not available"}

        if not checks["credentials_configured"]:
            print(f"\n{self._i18n_manager.t('cloud.credentials_not_configured')}")
            return {"success": False, "message": "Cloud credentials not configured"}

        print("\n" + "=" * 50)

        try:
            # 2. 获取云配置
            provider_name = self.deployment_type.replace("cloud_", "")
            self.cloud_config = self.config_manager.get_cloud_config(provider_name)

            # 3. 创建实例
            print(f"{self._i18n_manager.t('cloud.creating_instance')}")
            instance_result = await self._create_instance(
                region=region, instance_type=instance_type, **kwargs
            )
            if not instance_result["success"]:
                return instance_result

            # 4. 等待实例启动
            instance_id = instance_result["instance_id"]
            print(
                f"{self._i18n_manager.t('cloud.waiting_instance_ready', instance_id=instance_id)}"
            )
            await self._wait_for_instance_ready(instance_id)

            # 5. 部署AIForge应用
            print(f"{self._i18n_manager.t('cloud.deploying_application')}")
            deploy_result = await self._deploy_application(instance_id)

            print("\n" + "=" * 50)

            # 6. 显示部署信息
            await self._show_deployment_info(instance_id, deploy_result)

            return {
                "success": True,
                "instance_id": instance_id,
                "deployment_type": self.deployment_type,
                "deploy_result": deploy_result,
                "region": region,
                "instance_type": instance_type,
            }

        except Exception as e:
            print(self._i18n_manager.t("cloud.deployment_failed", error=str(e)))
            return {"success": False, "message": f"Cloud deployment failed: {str(e)}"}

    async def status(self) -> Dict[str, Any]:
        """获取云部署状态"""
        try:
            # 获取所有相关实例的状态
            instances = await self._list_instances()

            return {
                "success": True,
                "deployment_type": self.deployment_type,
                "instances": instances,
                "total_instances": len(instances),
                "running_instances": len([i for i in instances if i.get("state") == "running"]),
                "stopped_instances": len([i for i in instances if i.get("state") == "stopped"]),
                "pending_instances": len([i for i in instances if i.get("state") == "pending"]),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "deployment_type": self.deployment_type,
            }

    async def stop(self) -> bool:
        """停止云部署"""
        try:
            print(f"{self._i18n_manager.t('cloud.stopping_instances')}")

            instances = await self._list_instances()
            stopped_count = 0

            for instance in instances:
                instance_id = instance.get("instance_id")
                if instance_id and instance.get("state") == "running":
                    success = await self._terminate_instance(instance_id)
                    if success:
                        stopped_count += 1
                        print(
                            f"✅ {self._i18n_manager.t('cloud.instance_stopped', instance_id=instance_id)}"  # noqa 501
                        )
                    else:
                        print(
                            f"❌ {self._i18n_manager.t('cloud.instance_stop_failed', instance_id=instance_id)}"  # noqa 501
                        )

            print(f"{self._i18n_manager.t('cloud.stop_complete', count=stopped_count)}")
            return stopped_count > 0

        except Exception as e:
            print(f"{self._i18n_manager.t('cloud.stop_failed', error=str(e))}")
            return False

    async def cleanup(self) -> bool:
        """清理云资源"""
        try:
            print(f"{self._i18n_manager.t('cloud.cleaning_resources')}")

            # 1. 停止所有实例
            await self.stop()

            # 2. 等待实例完全停止
            print(f"{self._i18n_manager.t('cloud.waiting_instances_stop')}")
            await asyncio.sleep(30)

            # 3. 删除所有相关资源（由子类实现具体清理逻辑）
            cleanup_success = await self._cleanup_resources()

            if cleanup_success:
                print(f"✅ {self._i18n_manager.t('cloud.cleanup_success')}")
            else:
                print(f"❌ {self._i18n_manager.t('cloud.cleanup_failed')}")

            return cleanup_success

        except Exception as e:
            print(f"{self._i18n_manager.t('cloud.cleanup_exception', error=str(e))}")
            return False

    # 抽象方法和其他方法保持不变...
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

    @abstractmethod
    async def _execute_remote_script(self, instance_id: str, script: str) -> Dict[str, Any]:
        """在远程实例上执行脚本"""
        pass

    @abstractmethod
    async def _list_instances(self) -> List[Dict[str, Any]]:
        """列出所有相关实例"""
        pass

    @abstractmethod
    async def _check_cloud_cli(self) -> bool:
        """检查云CLI是否可用"""
        pass

    @abstractmethod
    async def _check_credentials(self) -> bool:
        """检查云凭据是否配置"""
        pass

    @abstractmethod
    async def _cleanup_resources(self) -> bool:
        """清理云资源"""
        pass

    @abstractmethod
    async def _get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """获取实例详细信息"""
        pass
