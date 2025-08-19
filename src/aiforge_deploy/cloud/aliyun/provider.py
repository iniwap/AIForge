import asyncio
import json
from typing import Dict, Any, List
from ..base_provider import CloudDeploymentProvider


class AliyunDeploymentProvider(CloudDeploymentProvider):
    """阿里云部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "cloud_aliyun"

    async def _check_cloud_cli(self) -> bool:
        """检查阿里云CLI是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                "aliyun",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                print(self._i18n_manager.t("cloud.aliyun_cli_installed"))
                return True
            else:
                print(self._i18n_manager.t("cloud.aliyun_cli_not_installed"))
                return False
        except FileNotFoundError:
            print(self._i18n_manager.t("cloud.aliyun_cli_not_in_path"))
            return False

    async def _check_credentials(self) -> bool:
        """检查阿里云凭据是否配置"""
        try:
            result = await asyncio.create_subprocess_exec(
                "aliyun",
                "configure",
                "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0 and "access-key-id" in stdout.decode():
                print(self._i18n_manager.t("cloud.aliyun_credentials_configured"))
                return True
            else:
                print(self._i18n_manager.t("cloud.aliyun_credentials_not_configured"))
                return False
        except Exception:
            print(self._i18n_manager.t("cloud.aliyun_credentials_check_failed"))
            return False

    async def _create_instance(self, **kwargs) -> Dict[str, Any]:
        """创建阿里云ECS实例"""
        region = kwargs.get("region", "cn-hangzhou")
        instance_type = kwargs.get("instance_type", "ecs.t5-lc1m1.small")
        image_id = kwargs.get("image_id", "ubuntu_20_04_x64_20G_alibase_20231221.vhd")
        security_group_id = kwargs.get("security_group_id", "")
        vswitch_id = kwargs.get("vswitch_id", "")

        try:
            # 如果没有提供安全组，创建一个默认的
            if not security_group_id:
                sg_result = await self._create_security_group(region)
                if not sg_result["success"]:
                    return sg_result
                security_group_id = sg_result["security_group_id"]

            # 如果没有提供交换机，使用默认VPC的交换机
            if not vswitch_id:
                vswitch_result = await self._get_default_vswitch(region)
                if not vswitch_result["success"]:
                    return vswitch_result
                vswitch_id = vswitch_result["vswitch_id"]

            # 创建ECS实例
            cmd = [
                "aliyun",
                "ecs",
                "RunInstances",
                "--region",
                region,
                "--ImageId",
                image_id,
                "--InstanceType",
                instance_type,
                "--SecurityGroupId",
                security_group_id,
                "--VSwitchId",
                vswitch_id,
                "--InstanceName",
                "aiforge-instance",
                "--Description",
                "AIForge deployment instance",
                "--InternetMaxBandwidthOut",
                "5",
                "--InstanceChargeType",
                "PostPaid",
                "--SystemDisk.Category",
                "cloud_efficiency",
                "--SystemDisk.Size",
                "40",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                instance_id = result["InstanceIdSets"]["InstanceIdSet"][0]

                print(
                    f"✅ {self._i18n_manager.t('cloud.aliyun_instance_created', instance_id=instance_id)}"  # noqa 501
                )

                return {
                    "success": True,
                    "instance_id": instance_id,
                    "region": region,
                    "instance_type": instance_type,
                }
            else:
                error_msg = stderr.decode()
                print(
                    f"❌ {self._i18n_manager.t('cloud.aliyun_instance_create_failed', error=error_msg)}"  # noqa 501
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_security_group(self, region: str) -> Dict[str, Any]:
        """创建默认安全组"""
        try:
            # 创建安全组
            cmd = [
                "aliyun",
                "ecs",
                "CreateSecurityGroup",
                "--region",
                region,
                "--SecurityGroupName",
                "aiforge-sg",
                "--Description",
                "AIForge security group",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                security_group_id = result["SecurityGroupId"]

                # 添加入站规则：允许SSH (22) 和 HTTP (8000)
                await self._add_security_group_rule(region, security_group_id, "22", "SSH")
                await self._add_security_group_rule(
                    region, security_group_id, "8000", "AIForge Web"
                )

                return {"success": True, "security_group_id": security_group_id}
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _add_security_group_rule(self, region: str, sg_id: str, port: str, description: str):
        """添加安全组规则"""
        cmd = [
            "aliyun",
            "ecs",
            "AuthorizeSecurityGroup",
            "--region",
            region,
            "--SecurityGroupId",
            sg_id,
            "--IpProtocol",
            "tcp",
            "--PortRange",
            f"{port}/{port}",
            "--SourceCidrIp",
            "0.0.0.0/0",
            "--Description",
            description,
        ]

        await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _get_default_vswitch(self, region: str) -> Dict[str, Any]:
        """获取默认VPC的交换机"""
        try:
            # 获取默认VPC
            cmd = [
                "aliyun",
                "vpc",
                "DescribeVpcs",
                "--region",
                region,
                "--IsDefault",
                "true",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                if result["Vpcs"]["Vpc"]:
                    vpc_id = result["Vpcs"]["Vpc"][0]["VpcId"]

                    # 获取VPC下的交换机
                    vswitch_cmd = [
                        "aliyun",
                        "vpc",
                        "DescribeVSwitches",
                        "--region",
                        region,
                        "--VpcId",
                        vpc_id,
                    ]

                    vswitch_process = await asyncio.create_subprocess_exec(
                        *vswitch_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    vswitch_stdout, _ = await vswitch_process.communicate()

                    if vswitch_process.returncode == 0:
                        vswitch_result = json.loads(vswitch_stdout.decode())
                        if vswitch_result["VSwitches"]["VSwitch"]:
                            vswitch_id = vswitch_result["VSwitches"]["VSwitch"][0]["VSwitchId"]
                            return {"success": True, "vswitch_id": vswitch_id}

            return {"success": False, "error": "No default VSwitch found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """获取实例状态"""
        try:
            cmd = [
                "aliyun",
                "ecs",
                "DescribeInstances",
                "--InstanceIds",
                f'["{instance_id}"]',
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                if result["Instances"]["Instance"]:
                    instance = result["Instances"]["Instance"][0]
                    return {
                        "state": instance["Status"].lower(),
                        "public_ip": instance.get("PublicIpAddress", {}).get("IpAddress", [None])[
                            0
                        ],
                        "private_ip": instance.get("InnerIpAddress", {}).get("IpAddress", [None])[
                            0
                        ],
                    }

            return {"state": "unknown"}

        except Exception:
            return {"state": "unknown"}

    async def _terminate_instance(self, instance_id: str) -> bool:
        """终止实例"""
        try:
            cmd = [
                "aliyun",
                "ecs",
                "DeleteInstance",
                "--InstanceId",
                instance_id,
                "--Force",
                "true",
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
            cmd = [
                "aliyun",
                "ecs",
                "GetInstanceConsoleOutput",
                "--InstanceId",
                instance_id,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                return result.get("ConsoleOutput", "No logs available")

            return "Failed to get logs"

        except Exception as e:
            return f"Failed to get logs: {str(e)}"

    async def _execute_remote_script(self, instance_id: str, script: str) -> Dict[str, Any]:
        """在远程实例上执行脚本"""
        try:
            # 使用阿里云云助手执行脚本
            cmd = [
                "aliyun",
                "ecs",
                "RunCommand",
                "--InstanceId.1",
                instance_id,
                "--Type",
                "RunShellScript",
                "--CommandContent",
                script,
                "--Name",
                "aiforge-deployment",
                "--Description",
                "AIForge deployment script",
                "--Timeout",
                "3600",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                command_id = result["CommandId"]

                # 等待命令执行完成
                await self._wait_for_command_completion(instance_id, command_id)

                return {"success": True, "command_id": command_id}
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _wait_for_command_completion(
        self, instance_id: str, command_id: str, timeout: int = 1800
    ):
        """等待命令执行完成"""
        for _ in range(timeout // 10):
            try:
                cmd = [
                    "aliyun",
                    "ecs",
                    "DescribeInvocations",
                    "--CommandId",
                    command_id,
                    "--InstanceId",
                    instance_id,
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()

                if process.returncode == 0:
                    result = json.loads(stdout.decode())
                    if result["Invocations"]["Invocation"]:
                        invocation = result["Invocations"]["Invocation"][0]
                        if invocation["InvokeStatus"] in ["Finished", "Failed", "Stopped"]:
                            return invocation["InvokeStatus"] == "Finished"

                await asyncio.sleep(10)

            except Exception:
                await asyncio.sleep(10)

        return False

    async def _list_instances(self) -> List[Dict[str, Any]]:
        """列出所有AIForge相关实例"""
        try:
            cmd = [
                "aliyun",
                "ecs",
                "DescribeInstances",
                "--InstanceName",
                "aiforge-instance",
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

                if result.get("Instances", {}).get("Instance"):
                    for instance in result["Instances"]["Instance"]:
                        instance_info = {
                            "instance_id": instance["InstanceId"],
                            "state": instance["Status"].lower(),
                            "instance_type": instance["InstanceType"],
                            "region": instance["RegionId"],
                            "public_ip": instance.get("PublicIpAddress", {}).get(
                                "IpAddress", [None]
                            )[0],
                            "private_ip": instance.get("InnerIpAddress", {}).get(
                                "IpAddress", [None]
                            )[0],
                            "creation_time": instance.get("CreationTime", ""),
                            "instance_name": instance.get("InstanceName", ""),
                        }
                        instances.append(instance_info)

                return instances

            else:
                print(f"❌ {self._i18n_manager.t('cloud.aliyun_list_instances_failed')}")
                return []

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.aliyun_list_instances_error', error=str(e))}")
            return []

    async def _get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """获取实例详细信息"""
        try:
            cmd = [
                "aliyun",
                "ecs",
                "DescribeInstances",
                "--InstanceIds",
                f'["{instance_id}"]',
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                if result.get("Instances", {}).get("Instance"):
                    instance = result["Instances"]["Instance"][0]
                    return {
                        "instance_id": instance["InstanceId"],
                        "state": instance["Status"].lower(),
                        "instance_type": instance["InstanceType"],
                        "region": instance["RegionId"],
                        "public_ip": instance.get("PublicIpAddress", {}).get("IpAddress", [None])[
                            0
                        ],
                        "private_ip": instance.get("InnerIpAddress", {}).get("IpAddress", [None])[
                            0
                        ],
                        "creation_time": instance.get("CreationTime", ""),
                        "instance_name": instance.get("InstanceName", ""),
                    }

            return {}

        except Exception as e:
            return {"error": str(e)}

    async def _cleanup_resources(self) -> bool:
        """清理阿里云资源"""
        try:
            print(f"{self._i18n_manager.t('cloud.aliyun_cleaning_resources')}")

            # 1. 获取所有相关实例
            instances = await self._list_instances()

            # 2. 删除所有实例
            for instance in instances:
                instance_id = instance.get("instance_id")
                if instance_id:
                    await self._terminate_instance(instance_id)

            # 3. 清理安全组（可选，因为可能被其他资源使用）
            # 这里可以添加清理安全组的逻辑，但需要谨慎处理

            print(f"✅ {self._i18n_manager.t('cloud.aliyun_cleanup_complete')}")
            return True

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.aliyun_cleanup_failed', error=str(e))}")
            return False
