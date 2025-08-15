import asyncio
import yaml
from typing import Dict, Any, Optional
from ..core.deployment_manager import BaseDeploymentProvider


class KubernetesDeploymentProvider(BaseDeploymentProvider):
    """Kubernetes部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "kubernetes"
        self.k8s_config = config_manager.get_kubernetes_config()
        self.namespace = self.k8s_config.get("namespace", "aiforge")

    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署到Kubernetes"""
        namespace = kwargs.get("namespace", self.namespace)
        replicas = kwargs.get("replicas", 1)

        try:
            # 1. 创建命名空间
            await self._create_namespace(namespace)

            # 2. 生成并应用部署清单
            manifests = self._generate_manifests(namespace, replicas)

            # 3. 应用清单
            for manifest_name, manifest_content in manifests.items():
                result = await self._apply_manifest(manifest_content)
                if not result["success"]:
                    return result

            return {
                "success": True,
                "message": f"Successfully deployed to namespace {namespace}",
                "namespace": namespace,
                "replicas": replicas,
            }

        except Exception as e:
            return {"success": False, "message": f"Deployment failed: {str(e)}"}

    async def _create_namespace(self, namespace: str):
        """创建命名空间"""
        cmd = ["kubectl", "create", "namespace", namespace, "--dry-run=client", "-o", "yaml"]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            # 应用命名空间
            apply_cmd = ["kubectl", "apply", "-f", "-"]
            apply_process = await asyncio.create_subprocess_exec(
                *apply_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await apply_process.communicate(input=stdout)

    def _generate_manifests(self, namespace: str, replicas: int) -> Dict[str, str]:
        """生成Kubernetes清单"""
        manifests = {}

        # Deployment清单
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "aiforge-engine", "namespace": namespace},
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": "aiforge-engine"}},
                "template": {
                    "metadata": {"labels": {"app": "aiforge-engine"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "aiforge-engine",
                                "image": "aiforge/aiforge-engine:latest",
                                "ports": [{"containerPort": 8000}],
                                "env": self._generate_env_vars(),
                                "resources": self.k8s_config.get("resources", {}),
                            }
                        ]
                    },
                },
            },
        }
        manifests["deployment"] = yaml.dump(deployment)

        # Service清单
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "aiforge-service", "namespace": namespace},
            "spec": {
                "selector": {"app": "aiforge-engine"},
                "ports": [{"port": 8000, "targetPort": 8000}],
                "type": "ClusterIP",
            },
        }
        manifests["service"] = yaml.dump(service)

        # Ingress清单（如果启用）
        if self.k8s_config.get("ingress", {}).get("enabled", False):
            ingress = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "Ingress",
                "metadata": {"name": "aiforge-ingress", "namespace": namespace},
                "spec": {
                    "rules": [
                        {
                            "host": self.k8s_config["ingress"]["host"],
                            "http": {
                                "paths": [
                                    {
                                        "path": "/",
                                        "pathType": "Prefix",
                                        "backend": {
                                            "service": {
                                                "name": "aiforge-service",
                                                "port": {"number": 8000},
                                            }
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
            manifests["ingress"] = yaml.dump(ingress)

        return manifests

    def _generate_env_vars(self) -> list:
        """生成环境变量"""
        aiforge_config = self.config_manager.get_aiforge_config_for_deployment()
        env_vars = [{"name": "AIFORGE_K8S_MODE", "value": "true"}]

        if aiforge_config:
            llm_config = aiforge_config.get_llm_config()
            if llm_config:
                for provider, config in llm_config.items():
                    if "api_key" in config:
                        env_vars.append(
                            {"name": f"{provider.upper()}_API_KEY", "value": config["api_key"]}
                        )

        return env_vars

    async def _apply_manifest(self, manifest_content: str) -> Dict[str, Any]:
        """应用Kubernetes清单"""
        try:
            cmd = ["kubectl", "apply", "-f", "-"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(input=manifest_content.encode())

            if process.returncode == 0:
                return {"success": True, "output": stdout.decode()}
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def status(self) -> Dict[str, Any]:
        """获取Kubernetes部署状态"""
        try:
            cmd = [
                "kubectl",
                "get",
                "pods",
                "-n",
                self.namespace,
                "-l",
                "app=aiforge-engine",
                "-o",
                "json",
            ]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                import json

                pods_info = json.loads(stdout.decode())
                return {
                    "success": True,
                    "pods": pods_info["items"],
                    "deployment_type": self.deployment_type,
                }
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop(self) -> bool:
        """停止Kubernetes部署"""
        try:
            cmd = ["kubectl", "delete", "deployment", "aiforge-engine", "-n", self.namespace]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except Exception:
            return False

    async def cleanup(self) -> bool:
        """清理Kubernetes资源"""
        try:
            # 删除所有相关资源
            resources = ["deployment", "service", "ingress"]
            for resource in resources:
                cmd = [
                    "kubectl",
                    "delete",
                    resource,
                    "-n",
                    self.namespace,
                    "-l",
                    "app=aiforge-engine",
                ]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process.wait()

            return True
        except Exception:
            return False

    async def logs(self, service: Optional[str] = None) -> str:
        """获取Kubernetes日志"""
        try:
            cmd = ["kubectl", "logs", "-n", self.namespace, "-l", "app=aiforge-engine"]
            if service:
                cmd.extend(["--container", service])

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            return stdout.decode() if stdout else ""
        except Exception as e:
            return f"Failed to get logs: {str(e)}"
