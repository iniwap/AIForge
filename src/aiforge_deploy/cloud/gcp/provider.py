import asyncio
import json
from typing import Dict, Any, List
from ..base_provider import CloudDeploymentProvider


class GCPDeploymentProvider(CloudDeploymentProvider):
    """GCP部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "cloud_gcp"

    async def _check_cloud_cli(self) -> bool:
        """检查GCP CLI是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                "gcloud",
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                print(self._i18n_manager.t("cloud.gcp_cli_installed"))
                return True
            else:
                print(self._i18n_manager.t("cloud.gcp_cli_not_installed"))
                return False
        except FileNotFoundError:
            print(self._i18n_manager.t("cloud.gcp_cli_not_in_path"))
            return False

    async def _check_credentials(self) -> bool:
        """检查GCP凭据是否配置"""
        try:
            result = await asyncio.create_subprocess_exec(
                "gcloud",
                "auth",
                "list",
                "--format=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0:
                accounts = json.loads(stdout.decode())
                if accounts and any(account.get("status") == "ACTIVE" for account in accounts):
                    print(self._i18n_manager.t("cloud.gcp_credentials_configured"))
                    return True

            print(self._i18n_manager.t("cloud.gcp_credentials_not_configured"))
            return False
        except Exception:
            print(self._i18n_manager.t("cloud.gcp_credentials_check_failed"))
            return False

    async def _create_instance(self, **kwargs) -> Dict[str, Any]:
        """创建GCP Compute Engine实例"""
        region = kwargs.get("region", "us-central1-a")
        instance_type = kwargs.get("instance_type", "e2-medium")
        image_family = kwargs.get("image_family", "ubuntu-2004-lts")
        image_project = kwargs.get("image_project", "ubuntu-os-cloud")
        project_id = kwargs.get("project_id", "")

        try:
            # 获取项目ID
            if not project_id:
                project_result = await self._get_current_project()
                if not project_result["success"]:
                    return project_result
                project_id = project_result["project_id"]

            # 创建防火墙规则（如果不存在）
            await self._create_firewall_rules(project_id)

            # 生成启动脚本
            startup_script = await self._generate_deploy_script()

            # 创建Compute Engine实例
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "create",
                "aiforge-instance",
                "--zone",
                region,
                "--machine-type",
                instance_type,
                "--image-family",
                image_family,
                "--image-project",
                image_project,
                "--boot-disk-size",
                "40GB",
                "--boot-disk-type",
                "pd-standard",
                "--tags",
                "aiforge-instance,http-server",
                "--metadata",
                f"startup-script={startup_script}",
                "--labels",
                "project=aiforge",
                "--format",
                "json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                instance_id = result[0]["id"]
                instance_name = result[0]["name"]

                print(
                    f"✅ {self._i18n_manager.t('cloud.gcp_instance_created', instance_id=instance_name)}"  # noqa 501
                )

                return {
                    "success": True,
                    "instance_id": instance_id,
                    "instance_name": instance_name,
                    "project_id": project_id,
                    "zone": region,
                    "instance_type": instance_type,
                }
            else:
                error_msg = stderr.decode()
                print(
                    f"❌ {self._i18n_manager.t('cloud.gcp_instance_create_failed', error=error_msg)}"
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_current_project(self) -> Dict[str, Any]:
        """获取当前项目ID"""
        try:
            cmd = [
                "gcloud",
                "config",
                "get-value",
                "project",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                project_id = stdout.decode().strip()
                if project_id:
                    return {"success": True, "project_id": project_id}

            return {"success": False, "error": "No project configured"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_firewall_rules(self, project_id: str):
        """创建防火墙规则"""
        try:
            # 创建SSH规则
            ssh_cmd = [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "aiforge-ssh",
                "--allow",
                "tcp:22",
                "--source-ranges",
                "0.0.0.0/0",
                "--target-tags",
                "aiforge-instance",
                "--description",
                "Allow SSH for AIForge instances",
            ]

            await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 创建HTTP规则
            http_cmd = [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "aiforge-http",
                "--allow",
                "tcp:8000",
                "--source-ranges",
                "0.0.0.0/0",
                "--target-tags",
                "aiforge-instance",
                "--description",
                "Allow HTTP for AIForge web interface",
            ]

            await asyncio.create_subprocess_exec(
                *http_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        except Exception:
            # 防火墙规则可能已存在，忽略错误
            pass

    async def _get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """获取实例状态"""
        try:
            # 从instance_id中提取实例名称和zone
            instance_name, zone = self._extract_instance_info_from_id(instance_id)

            cmd = [
                "gcloud",
                "compute",
                "instances",
                "describe",
                instance_name,
                "--zone",
                zone,
                "--format",
                "json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())

                # 获取外部IP
                external_ip = None
                if result.get("networkInterfaces"):
                    access_configs = result["networkInterfaces"][0].get("accessConfigs", [])
                    if access_configs:
                        external_ip = access_configs[0].get("natIP")

                return {
                    "state": result["status"].lower(),
                    "public_ip": external_ip,
                    "private_ip": result.get("networkInterfaces", [{}])[0].get("networkIP"),
                }

            return {"state": "unknown"}

        except Exception:
            return {"state": "unknown"}

    async def _terminate_instance(self, instance_id: str) -> bool:
        """终止实例"""
        try:
            instance_name, zone = self._extract_instance_info_from_id(instance_id)

            cmd = [
                "gcloud",
                "compute",
                "instances",
                "delete",
                instance_name,
                "--zone",
                zone,
                "--quiet",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.wait()

            return process.returncode == 0

        except Exception:
            return False

    async def _get_instance_logs(self, instance_id: str) -> str:
        """获取实例日志"""
        try:
            instance_name, zone = self._extract_instance_info_from_id(instance_id)

            cmd = [
                "gcloud",
                "compute",
                "instances",
                "get-serial-port-output",
                instance_name,
                "--zone",
                zone,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                return stdout.decode()

            return "No logs available"

        except Exception as e:
            return f"Failed to get logs: {str(e)}"

    async def _execute_remote_script(self, instance_id: str, script: str) -> Dict[str, Any]:
        """在远程实例上执行脚本"""
        try:
            instance_name, zone = self._extract_instance_info_from_id(instance_id)

            # 使用gcloud compute ssh执行脚本
            cmd = [
                "gcloud",
                "compute",
                "ssh",
                instance_name,
                "--zone",
                zone,
                "--command",
                script,
                "--quiet",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {"success": True, "output": stdout.decode()}
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _list_instances(self) -> List[Dict[str, Any]]:
        """列出所有AIForge相关实例"""
        try:
            cmd = [
                "gcloud",
                "compute",
                "instances",
                "list",
                "--filter",
                "labels.project=aiforge",
                "--format",
                "json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                instances = []

                for instance in result:
                    # 获取外部IP
                    external_ip = None
                    if instance.get("networkInterfaces"):
                        access_configs = instance["networkInterfaces"][0].get("accessConfigs", [])
                        if access_configs:
                            external_ip = access_configs[0].get("natIP")

                    instance_info = {
                        "instance_id": instance["id"],
                        "instance_name": instance["name"],
                        "state": instance["status"].lower(),
                        "instance_type": instance["machineType"].split("/")[-1],
                        "zone": instance["zone"].split("/")[-1],
                        "public_ip": external_ip,
                        "private_ip": instance.get("networkInterfaces", [{}])[0].get("networkIP"),
                        "creation_time": instance.get("creationTimestamp", ""),
                    }
                    instances.append(instance_info)

                return instances

            else:
                print(f"❌ {self._i18n_manager.t('cloud.gcp_list_instances_failed')}")
                return []

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.gcp_list_instances_error', error=str(e))}")
            return []

    async def _get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """获取实例详细信息"""
        try:
            instance_name, zone = self._extract_instance_info_from_id(instance_id)

            cmd = [
                "gcloud",
                "compute",
                "instances",
                "describe",
                instance_name,
                "--zone",
                zone,
                "--format",
                "json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())

                # 获取外部IP
                external_ip = None
                if result.get("networkInterfaces"):
                    access_configs = result["networkInterfaces"][0].get("accessConfigs", [])
                    if access_configs:
                        external_ip = access_configs[0].get("natIP")

                return {
                    "instance_id": result["id"],
                    "instance_name": result["name"],
                    "state": result["status"].lower(),
                    "instance_type": result["machineType"].split("/")[-1],
                    "zone": result["zone"].split("/")[-1],
                    "public_ip": external_ip,
                    "private_ip": result.get("networkInterfaces", [{}])[0].get("networkIP"),
                    "creation_time": result.get("creationTimestamp", ""),
                    "disk_size": result.get("disks", [{}])[0].get("diskSizeGb"),
                }

            return {}

        except Exception as e:
            return {"error": str(e)}

    def _extract_instance_info_from_id(self, instance_id: str) -> tuple[str, str]:
        """从GCP实例ID中提取实例名称和zone信息"""
        # GCP实例ID通常是数字ID，需要通过其他方式获取实例名称和zone
        # 这里我们使用默认值，实际使用中可能需要额外的查询
        # 或者在创建实例时保存这些信息的映射关系
        return "aiforge-instance", "us-central1-a"

    async def _cleanup_resources(self) -> bool:
        """清理GCP资源"""
        try:
            print(f"{self._i18n_manager.t('cloud.gcp_cleaning_resources')}")

            # 1. 获取所有相关实例
            instances = await self._list_instances()

            # 2. 删除所有实例
            for instance in instances:
                instance_id = instance.get("instance_id")
                if instance_id:
                    await self._terminate_instance(instance_id)

            # 3. 等待实例删除完成
            await asyncio.sleep(30)

            # 4. 清理防火墙规则（可选）
            await self._cleanup_firewall_rules()

            print(f"✅ {self._i18n_manager.t('cloud.gcp_cleanup_complete')}")
            return True

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.gcp_cleanup_failed', error=str(e))}")
            return False

    async def _cleanup_firewall_rules(self):
        """清理防火墙规则"""
        try:
            # 删除SSH规则
            ssh_cmd = [
                "gcloud",
                "compute",
                "firewall-rules",
                "delete",
                "aiforge-ssh",
                "--quiet",
            ]

            await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 删除HTTP规则
            http_cmd = [
                "gcloud",
                "compute",
                "firewall-rules",
                "delete",
                "aiforge-http",
                "--quiet",
            ]

            await asyncio.create_subprocess_exec(
                *http_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        except Exception:
            # 防火墙规则可能不存在，忽略错误
            pass
