import asyncio
import json
import base64
from typing import Dict, Any, List
from ..base_provider import CloudDeploymentProvider


class AWSDeploymentProvider(CloudDeploymentProvider):
    """AWS部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "cloud_aws"

    async def _check_cloud_cli(self) -> bool:
        """检查AWS CLI是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                "aws",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                print(self._i18n_manager.t("cloud.aws_cli_installed"))
                return True
            else:
                print(self._i18n_manager.t("cloud.aws_cli_not_installed"))
                return False
        except FileNotFoundError:
            print(self._i18n_manager.t("cloud.aws_cli_not_in_path"))
            return False

    async def _check_credentials(self) -> bool:
        """检查AWS凭据是否配置"""
        try:
            result = await asyncio.create_subprocess_exec(
                "aws",
                "sts",
                "get-caller-identity",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0:
                identity = json.loads(stdout.decode())
                if identity.get("Account"):
                    print(self._i18n_manager.t("cloud.aws_credentials_configured"))
                    return True

            print(self._i18n_manager.t("cloud.aws_credentials_not_configured"))
            return False
        except Exception:
            print(self._i18n_manager.t("cloud.aws_credentials_check_failed"))
            return False

    async def _create_instance(self, **kwargs) -> Dict[str, Any]:
        """创建AWS EC2实例"""
        region = kwargs.get("region", "us-west-2")
        instance_type = kwargs.get("instance_type", "t3.medium")
        ami_id = kwargs.get("ami_id", "ami-0c02fb55956c7d316")  # Ubuntu 20.04 LTS
        key_name = kwargs.get("key_name", "")
        security_group_id = kwargs.get("security_group_id", "")

        try:
            # 如果没有提供安全组，创建一个默认的
            if not security_group_id:
                sg_result = await self._create_security_group(region)
                if not sg_result["success"]:
                    return sg_result
                security_group_id = sg_result["security_group_id"]

            # 生成用户数据脚本
            user_data = await self._generate_deploy_script()
            user_data_b64 = base64.b64encode(user_data.encode()).decode()

            # 创建EC2实例
            cmd = [
                "aws",
                "ec2",
                "run-instances",
                "--region",
                region,
                "--image-id",
                ami_id,
                "--instance-type",
                instance_type,
                "--security-group-ids",
                security_group_id,
                "--user-data",
                user_data_b64,
                "--tag-specifications",
                f"ResourceType=instance,Tags=[{{Key=Name,Value=aiforge-instance}},{{Key=Project,Value=AIForge}}]",  # noqa 501
                "--associate-public-ip-address",
            ]

            # 如果提供了密钥对，添加到命令中
            if key_name:
                cmd.extend(["--key-name", key_name])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                instance_id = result["Instances"][0]["InstanceId"]

                print(
                    f"✅ {self._i18n_manager.t('cloud.aws_instance_created', instance_id=instance_id)}"  # noqa 501
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
                    f"❌ {self._i18n_manager.t('cloud.aws_instance_create_failed', error=error_msg)}"
                )
                return {"success": False, "error": error_msg}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_security_group(self, region: str) -> Dict[str, Any]:
        """创建默认安全组"""
        try:
            # 获取默认VPC
            vpc_result = await self._get_default_vpc(region)
            if not vpc_result["success"]:
                return vpc_result

            vpc_id = vpc_result["vpc_id"]

            # 创建安全组
            cmd = [
                "aws",
                "ec2",
                "create-security-group",
                "--region",
                region,
                "--group-name",
                "aiforge-sg",
                "--description",
                "AIForge security group",
                "--vpc-id",
                vpc_id,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                security_group_id = result["GroupId"]

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

    async def _get_default_vpc(self, region: str) -> Dict[str, Any]:
        """获取默认VPC"""
        try:
            cmd = [
                "aws",
                "ec2",
                "describe-vpcs",
                "--region",
                region,
                "--filters",
                "Name=is-default,Values=true",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                if result["Vpcs"]:
                    vpc_id = result["Vpcs"][0]["VpcId"]
                    return {"success": True, "vpc_id": vpc_id}

            return {"success": False, "error": "No default VPC found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _add_security_group_rule(self, region: str, sg_id: str, port: str, description: str):
        """添加安全组规则"""
        cmd = [
            "aws",
            "ec2",
            "authorize-security-group-ingress",
            "--region",
            region,
            "--group-id",
            sg_id,
            "--protocol",
            "tcp",
            "--port",
            port,
            "--cidr",
            "0.0.0.0/0",
        ]

        await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """获取实例状态"""
        try:
            cmd = [
                "aws",
                "ec2",
                "describe-instances",
                "--instance-ids",
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
                if result["Reservations"] and result["Reservations"][0]["Instances"]:
                    instance = result["Reservations"][0]["Instances"][0]
                    return {
                        "state": instance["State"]["Name"],
                        "public_ip": instance.get("PublicIpAddress"),
                        "private_ip": instance.get("PrivateIpAddress"),
                    }

            return {"state": "unknown"}

        except Exception:
            return {"state": "unknown"}

    async def _terminate_instance(self, instance_id: str) -> bool:
        """终止实例"""
        try:
            cmd = [
                "aws",
                "ec2",
                "terminate-instances",
                "--instance-ids",
                instance_id,
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
                "aws",
                "ec2",
                "get-console-output",
                "--instance-id",
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
                if result.get("Output"):
                    return base64.b64decode(result["Output"]).decode()

            return "No logs available"

        except Exception as e:
            return f"Failed to get logs: {str(e)}"

    async def _execute_remote_script(self, instance_id: str, script: str) -> Dict[str, Any]:
        """在远程实例上执行脚本"""
        try:
            # 使用AWS Systems Manager执行脚本
            cmd = [
                "aws",
                "ssm",
                "send-command",
                "--instance-ids",
                instance_id,
                "--document-name",
                "AWS-RunShellScript",
                "--parameters",
                f'commands=["{script}"]',
                "--comment",
                "AIForge deployment script",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                command_id = result["Command"]["CommandId"]

                # 等待命令执行完成
                success = await self._wait_for_command_completion(instance_id, command_id)

                return {"success": success, "command_id": command_id}
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
                    "aws",
                    "ssm",
                    "get-command-invocation",
                    "--command-id",
                    command_id,
                    "--instance-id",
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
                    status = result.get("Status", "")
                    if status in ["Success", "Failed", "Cancelled", "TimedOut"]:
                        return status == "Success"

                await asyncio.sleep(10)

            except Exception:
                await asyncio.sleep(10)

        return False

    async def _list_instances(self) -> List[Dict[str, Any]]:
        """列出所有AIForge相关实例"""
        try:
            cmd = [
                "aws",
                "ec2",
                "describe-instances",
                "--filters",
                "Name=tag:Name,Values=aiforge-instance",
                "Name=instance-state-name,Values=pending,running,stopping,stopped",
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

                for reservation in result["Reservations"]:
                    for instance in reservation["Instances"]:
                        instance_info = {
                            "instance_id": instance["InstanceId"],
                            "state": instance["State"]["Name"],
                            "instance_type": instance["InstanceType"],
                            "region": instance["Placement"]["AvailabilityZone"][:-1],
                            "public_ip": instance.get("PublicIpAddress"),
                            "private_ip": instance.get("PrivateIpAddress"),
                            "launch_time": instance.get("LaunchTime", "")
                            .replace("T", " ")
                            .replace("Z", ""),
                        }
                        instances.append(instance_info)

                return instances

            else:
                print(f"❌ {self._i18n_manager.t('cloud.aws_list_instances_failed')}")
                return []

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.aws_list_instances_error', error=str(e))}")
            return []

    async def _get_instance_info(self, instance_id: str) -> Dict[str, Any]:
        """获取实例详细信息"""
        try:
            cmd = [
                "aws",
                "ec2",
                "describe-instances",
                "--instance-ids",
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
                if result["Reservations"] and result["Reservations"][0]["Instances"]:
                    instance = result["Reservations"][0]["Instances"][0]
                    return {
                        "instance_id": instance["InstanceId"],
                        "state": instance["State"]["Name"],
                        "instance_type": instance["InstanceType"],
                        "region": instance["Placement"]["AvailabilityZone"][:-1],
                        "public_ip": instance.get("PublicIpAddress"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "launch_time": instance.get("LaunchTime", "")
                        .replace("T", " ")
                        .replace("Z", ""),
                        "vpc_id": instance.get("VpcId"),
                        "subnet_id": instance.get("SubnetId"),
                    }

            return {}

        except Exception as e:
            return {"error": str(e)}

    async def _cleanup_resources(self) -> bool:
        """清理AWS资源"""
        try:
            print(f"{self._i18n_manager.t('cloud.aws_cleaning_resources')}")

            # 1. 获取所有相关实例
            instances = await self._list_instances()

            # 2. 终止所有实例
            for instance in instances:
                instance_id = instance.get("instance_id")
                if instance_id:
                    await self._terminate_instance(instance_id)

            # 3. 等待实例终止
            await asyncio.sleep(30)

            # 4. 清理安全组（可选，因为可能被其他资源使用）
            # 这里可以添加清理安全组的逻辑，但需要谨慎处理

            print(f"✅ {self._i18n_manager.t('cloud.aws_cleanup_complete')}")
            return True

        except Exception as e:
            print(f"❌ {self._i18n_manager.t('cloud.aws_cleanup_failed', error=str(e))}")
            return False
