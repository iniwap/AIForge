import asyncio
import json
import base64
from typing import Dict, Any, List

from ..base_provider import CloudDeploymentProvider


class AzureDeploymentProvider(CloudDeploymentProvider):
    """Azure部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "cloud_azure"

    async def _check_cloud_cli(self) -> bool:
        """检查Azure CLI是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                "az",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                print(self._i18n_manager.t("cloud.azure_cli_installed"))
                return True
            else:
                print(self._i18n_manager.t("cloud.azure_cli_not_installed"))
                return False
        except FileNotFoundError:
            print(self._i18n_manager.t("cloud.azure_cli_not_in_path"))
            return False

    async def _check_credentials(self) -> bool:
        """检查Azure凭据是否配置"""
        try:
            result = await asyncio.create_subprocess_exec(
                "az",
                "account",
                "show",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0:
                account = json.loads(stdout.decode())
                if account.get("id"):
                    print(self._i18n_manager.t("cloud.azure_credentials_configured"))
                    return True

            print(self._i18n_manager.t("cloud.azure_credentials_not_configured"))
            return False
        except Exception:
            print(self._i18n_manager.t("cloud.azure_credentials_check_failed"))
            return False

    async def _create_instance(self, **kwargs) -> Dict[str, Any]:
        """创建Azure虚拟机实例"""
        region = kwargs.get("region", "eastus")
        instance_type = kwargs.get("instance_type", "Standard_B2s")
        image = kwargs.get("image", "UbuntuLTS")
        resource_group = kwargs.get("resource_group", "aiforge-rg")
        vm_name = kwargs.get("vm_name", "aiforge-vm")

        try:
            # 创建资源组
            rg_result = await self._create_resource_group(resource_group, region)
            if not rg_result["success"]:
                return rg_result

            # 创建网络安全组
            nsg_result = await self._create_network_security_group(resource_group, region)
            if not nsg_result["success"]:
                return nsg_result

            # 生成用户数据脚本
            user_data = await self._generate_deploy_script()
            user_data_b64 = base64.b64encode(user_data.encode()).decode()

            # 创建虚拟机
            cmd = [
                "az",
                "vm",
                "create",
                "--resource-group",
                resource_group,
                "--name",
                vm_name,
                "--image",
                image,
                "--size",
                instance_type,
                "--location",
                region,
                "--admin-username",
                "azureuser",
                "--generate-ssh-keys",
                "--nsg",
                "aiforge-nsg",
                "--custom-data",
                user_data_b64,
                "--tags",
                "Project=AIForge",
                "--output",
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
                vm_id = result["id"]

                print(
                    f"✅ {self._i18n_manager.t('cloud.azure_instance_created', instance_id=vm_id)}"
                )

                return {
                    "success": True,
                    "instance_id": vm_id,
                    "vm_name": vm_name,
                    "resource_group": resource_group,
                    "region": region,
                    "instance_type": instance_type,
                }
            else:
                error_msg = stderr.decode()
                print(
                    f"❌ {self._i18n_manager.t('cloud.azure_instance_create_failed', error=error_msg)}"  # noqa 501
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_resource_group(self, resource_group: str, region: str) -> Dict[str, Any]:
        """创建资源组"""
        try:
            cmd = [
                "az",
                "group",
                "create",
                "--name",
                resource_group,
                "--location",
                region,
                "--output",
                "json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {"success": True}
            else:
                # 如果资源组已存在，也认为是成功的
                if "already exists" in stderr.decode():
                    return {"success": True}
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_network_security_group(
        self, resource_group: str, region: str
    ) -> Dict[str, Any]:
        """创建网络安全组"""
        try:
            # 创建网络安全组
            cmd = [
                "az",
                "network",
                "nsg",
                "create",
                "--resource-group",
                resource_group,
                "--name",
                "aiforge-nsg",
                "--location",
                region,
                "--output",
                "json",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            # 添加安全规则：允许SSH (22) 和 HTTP (8000)
            await self._add_security_rule(resource_group, "aiforge-nsg", "SSH", "22")
            await self._add_security_rule(resource_group, "aiforge-nsg", "AIForge-Web", "8000")

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _add_security_rule(
        self, resource_group: str, nsg_name: str, rule_name: str, port: str
    ):
        """添加安全组规则"""
        cmd = [
            "az",
            "network",
            "nsg",
            "rule",
            "create",
            "--resource-group",
            resource_group,
            "--nsg-name",
            nsg_name,
            "--name",
            rule_name,
            "--protocol",
            "tcp",
            "--priority",
            "1000" if port == "22" else "1001",
            "--destination-port-range",
            port,
            "--access",
            "allow",
            "--output",
            "json",
        ]

        await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """获取实例状态"""
        try:
            # 从instance_id中提取资源组和VM名称
            vm_name = self._extract_vm_name_from_id(instance_id)
            resource_group = self._extract_resource_group_from_id(instance_id)

            cmd = [
                "az",
                "vm",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                vm_name,
                "--show-details",
                "--output",
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
                return {
                    "state": result.get("powerState", "unknown").replace("VM ", "").lower(),
                    "public_ip": result.get("publicIps"),
                    "private_ip": result.get("privateIps"),
                }

            return {"state": "unknown"}

        except Exception:
            return {"state": "unknown"}

    async def _terminate_instance(self, instance_id: str) -> bool:
        """终止实例"""
        try:
            vm_name = self._extract_vm_name_from_id(instance_id)
            resource_group = self._extract_resource_group_from_id(instance_id)

            cmd = [
                "az",
                "vm",
                "delete",
                "--resource-group",
                resource_group,
                "--name",
                vm_name,
                "--yes",
                "--output",
                "json",
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
            vm_name = self._extract_vm_name_from_id(instance_id)
            resource_group = self._extract_resource_group_from_id(instance_id)

            cmd = [
                "az",
                "vm",
                "boot-diagnostics",
                "get-boot-log",
                "--resource-group",
                resource_group,
                "--name",
                vm_name,
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
            vm_name = self._extract_vm_name_from_id(instance_id)
            resource_group = self._extract_resource_group_from_id(instance_id)

            # 使用Azure VM扩展执行脚本
            cmd = [
                "az",
                "vm",
                "extension",
                "set",
                "--resource-group",
                resource_group,
                "--vm-name",
                vm_name,
                "--name",
                "customScript",
                "--publisher",
                "Microsoft.Azure.Extensions",
                "--settings",
                f'{{"script": "{base64.b64encode(script.encode()).decode()}"}}',
                "--output",
                "json",
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
                "az",
                "vm",
                "list",
                "--query",
                "[?tags.Project=='AIForge']",
                "--output",
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

                for vm in result:
                    instance_info = {
                        "instance_id": vm["id"],
                        "vm_name": vm["name"],
                        "state": vm.get("powerState", "unknown").replace("VM ", "").lower(),
                        "instance_type": vm["hardwareProfile"]["vmSize"],
                        "region": vm["location"],
                        "resource_group": vm["resourceGroup"],
                    }

                    # 获取详细信息包括IP地址
                    details = await self._get_instance_status(vm["id"])
                    instance_info.update(
                        {
                            "public_ip": details.get("public_ip"),
                            "private_ip": details.get("private_ip"),
                        }
                    )

                    instances.append(instance_info)

                return instances

            else:
                print(f"❌ {self._i18n_manager.t('cloud.azure_list_instances_failed')}")
                return []

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.azure_list_instances_error', error=str(e))}")
            return []

    async def _get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """获取实例详细信息"""
        try:
            vm_name = self._extract_vm_name_from_id(instance_id)
            resource_group = self._extract_resource_group_from_id(instance_id)

            cmd = [
                "az",
                "vm",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                vm_name,
                "--show-details",
                "--output",
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
                return {
                    "instance_id": result["id"],
                    "vm_name": result["name"],
                    "state": result.get("powerState", "unknown").replace("VM ", "").lower(),
                    "instance_type": result["hardwareProfile"]["vmSize"],
                    "region": result["location"],
                    "resource_group": result["resourceGroup"],
                    "public_ip": result.get("publicIps"),
                    "private_ip": result.get("privateIps"),
                    "os_type": result.get("storageProfile", {}).get("osDisk", {}).get("osType"),
                    "creation_time": result.get("timeCreated", ""),
                }

            return {}

        except Exception as e:
            return {"error": str(e)}

    def _extract_vm_name_from_id(self, instance_id: str) -> str:
        """从Azure资源ID中提取VM名称"""
        # Azure资源ID格式: /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Compute/virtualMachines/{vm-name} # noqa 501
        parts = instance_id.split("/")
        if len(parts) >= 9 and "virtualMachines" in parts:
            vm_name_index = parts.index("virtualMachines") + 1
            if vm_name_index < len(parts):
                return parts[vm_name_index]
        return "aiforge-vm"  # 默认名称

    def _extract_resource_group_from_id(self, instance_id: str) -> str:
        """从Azure资源ID中提取资源组名称"""
        # Azure资源ID格式: /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Compute/virtualMachines/{vm-name}  # noqa 501
        parts = instance_id.split("/")
        if len(parts) >= 5 and "resourceGroups" in parts:
            rg_index = parts.index("resourceGroups") + 1
            if rg_index < len(parts):
                return parts[rg_index]
        return "aiforge-rg"  # 默认资源组

    async def _cleanup_resources(self) -> bool:
        """清理Azure资源"""
        try:
            print(f"{self._i18n_manager.t('cloud.azure_cleaning_resources')}")

            # 1. 获取所有相关实例
            instances = await self._list_instances()

            # 2. 删除所有虚拟机
            for instance in instances:
                instance_id = instance.get("instance_id")
                if instance_id:
                    await self._terminate_instance(instance_id)

            # 3. 等待虚拟机删除完成
            await asyncio.sleep(30)

            # 4. 清理资源组（可选，因为可能包含其他资源）
            # 这里可以添加清理资源组的逻辑，但需要谨慎处理

            print(f"✅ {self._i18n_manager.t('cloud.azure_cleanup_complete')}")
            return True

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.azure_cleanup_failed', error=str(e))}")
            return False
