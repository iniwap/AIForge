import asyncio
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from ..core.deployment_manager import BaseDeploymentProvider
from aiforge import GlobalI18nManager


class KubernetesDeploymentProvider(BaseDeploymentProvider):
    """Kubernetes部署提供商 - 支持用户自定义配置"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "kubernetes"

        # 获取i18n管理器
        self._i18n_manager = GlobalI18nManager.get_instance()

        # 获取用户传递的K8s配置（可能为None）
        self.k8s_config = config_manager.get_kubernetes_config() or {}
        self.namespace = self.k8s_config.get("namespace", "aiforge")

        # 根据用户配置或默认配置设置manifest文件路径
        self._setup_manifest_file_paths()

    def _setup_manifest_file_paths(self):
        """设置manifest文件路径"""

        # 检查用户是否传递了自定义的 manifest 文件路径
        user_manifest_paths = self.config_manager.get_user_k8s_manifest_paths()

        if user_manifest_paths:
            # 用户传递了自定义的 manifest 文件路径
            self.manifest_files = {}
            for manifest_type, path in user_manifest_paths.items():
                if Path(path).exists():
                    self.manifest_files[manifest_type] = path
                else:
                    self.manifest_files[manifest_type] = self._get_default_manifest_file(
                        manifest_type
                    )
        else:
            # 使用默认配置
            self.manifest_files = {
                "namespace": self._get_default_manifest_file("namespace"),
                "deployment": self._get_default_manifest_file("deployment"),
                "service": self._get_default_manifest_file("service"),
                "ingress": self._get_default_manifest_file("ingress"),
                "pvc": self._get_default_manifest_file("pvc"),
                "secrets": self._get_default_manifest_file("secrets"),
            }

    def get_user_k8s_manifest_paths(self) -> Optional[Dict[str, str]]:
        """获取用户自定义的 Kubernetes manifest 文件路径"""
        if not self._deployment_config:
            return None

        k8s_config = self._deployment_config.get("kubernetes", {})
        manifest_paths = k8s_config.get("manifest_paths", {})

        # 验证路径是否存在
        validated_paths = {}
        for manifest_type, path in manifest_paths.items():
            if isinstance(path, str) and Path(path).exists():
                validated_paths[manifest_type] = path

        return validated_paths if validated_paths else None

    def _get_default_manifest_file(self, manifest_type: str) -> str:
        """获取默认的manifest文件路径"""
        if self._is_source_environment():
            current_file = Path(__file__)
            templates_dir = current_file.parent / "templates"
            return str(templates_dir / f"{manifest_type}.yaml")
        else:
            return self._get_template_path(f"{manifest_type}.yaml")

    def _is_source_environment(self) -> bool:
        """检查是否在源码环境"""
        current_dir = Path.cwd()
        return (
            (current_dir / "src" / "aiforge").exists()
            and (
                current_dir
                / "src"
                / "aiforge_deploy"
                / "kubernetes"
                / "templates"
                / "deployment.yaml"
            ).exists()
            and (current_dir / "pyproject.toml").exists()
        )

    def _get_template_path(self, filename: str) -> str:
        """获取模板文件路径"""
        try:
            from importlib import resources

            with resources.path("aiforge_deploy.kubernetes.templates", filename) as path:
                return str(path)
        except Exception:
            # 如果无法从包资源获取，回退到当前目录
            return filename

    def get_effective_k8s_config(self) -> Dict[str, Any]:
        """获取有效的K8s配置（用户配置 + 默认配置）"""
        if self.k8s_config and "manifest_content" in self.k8s_config:
            # 用户提供了 manifest 内容
            return {
                "manifest_content": self.k8s_config["manifest_content"],
                "manifest_files": self.manifest_files,
                "namespace": self.namespace,
            }
        else:
            # 返回默认K8s配置
            return {
                "manifest_files": self.manifest_files,
                "namespace": self.namespace,
                "replicas": self.k8s_config.get("replicas", 1),
                "resources": self.k8s_config.get("resources", {}),
            }

    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署到Kubernetes"""
        namespace = kwargs.get("namespace", self.namespace)
        replicas = kwargs.get("replicas", 1)
        enable_ingress = kwargs.get("enable_ingress", False)

        print(self._i18n_manager.t("k8s.starting_deployment"))
        print("=" * 50)

        # 1. 环境检查
        env_check = await self._check_environment()
        if not env_check["success"]:
            return {"success": False, "message": "Environment check failed", "details": env_check}

        # 检查必要条件
        checks = env_check["checks"]
        if not checks["kubectl_available"]:
            print(f"\n{self._i18n_manager.t('k8s.kubectl_not_installed')}")
            return {"success": False, "message": "kubectl not available"}

        if not checks["cluster_accessible"]:
            print(f"\n{self._i18n_manager.t('k8s.cluster_not_accessible')}")
            return {"success": False, "message": "Kubernetes cluster not accessible"}

        print("\n" + "=" * 50)

        try:
            # 2. 创建命名空间
            await self._create_namespace(namespace)

            # 3. 应用基础资源（PVC, Secrets）
            await self._apply_base_resources(namespace)

            # 4. 生成并应用部署清单
            manifests = await self._generate_manifests(namespace, replicas, enable_ingress)

            # 5. 应用清单
            for manifest_name, manifest_content in manifests.items():
                result = await self._apply_manifest(manifest_content)
                if not result["success"]:
                    return result

            print("\n" + "=" * 50)

            # 6. 等待部署就绪
            await self._wait_for_deployment_ready(namespace)

            # 7. 显示服务信息
            await self._show_service_urls(namespace, enable_ingress)

            return {
                "success": True,
                "message": f"Successfully deployed to namespace {namespace}",
                "namespace": namespace,
                "replicas": replicas,
            }

        except Exception as e:
            return {"success": False, "message": f"Deployment failed: {str(e)}"}

    async def _check_environment(self) -> Dict[str, Any]:
        """全面检查Kubernetes环境"""
        print(self._i18n_manager.t("k8s.checking_environment"))

        checks = {
            "kubectl_available": False,
            "cluster_accessible": False,
            "namespace_exists": False,
            "manifest_files_exist": False,
        }

        # 检查kubectl是否安装
        try:
            result = await asyncio.create_subprocess_exec(
                "kubectl",
                "version",
                "--client",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                checks["kubectl_available"] = True
                print(self._i18n_manager.t("k8s.kubectl_installed"))
            else:
                print(self._i18n_manager.t("k8s.kubectl_not_installed"))
                return {"success": False, "checks": checks}
        except FileNotFoundError:
            print(self._i18n_manager.t("k8s.kubectl_not_in_path"))
            return {"success": False, "checks": checks}

        # 检查集群连接
        try:
            result = await asyncio.create_subprocess_exec(
                "kubectl",
                "cluster-info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                checks["cluster_accessible"] = True
                print(self._i18n_manager.t("k8s.cluster_accessible"))
            else:
                print(self._i18n_manager.t("k8s.cluster_not_accessible"))
                return {"success": False, "checks": checks}
        except Exception:
            print(self._i18n_manager.t("k8s.cannot_connect_cluster"))
            return {"success": False, "checks": checks}

        # 检查manifest文件
        manifest_files_exist = True
        for manifest_type, manifest_path in self.manifest_files.items():
            if not Path(manifest_path).exists():
                print(f"{self._i18n_manager.t('k8s.manifest_file_not_exists', file=manifest_path)}")
                manifest_files_exist = False

        checks["manifest_files_exist"] = manifest_files_exist

        success = all(
            [
                checks["kubectl_available"],
                checks["cluster_accessible"],
                checks["manifest_files_exist"],
            ]
        )

        return {"success": success, "checks": checks}

    async def _create_namespace(self, namespace: str):
        """创建命名空间"""
        print(f"{self._i18n_manager.t('k8s.creating_namespace', namespace=namespace)}")

        # 使用模板文件或动态生成
        if "namespace" in self.manifest_files and Path(self.manifest_files["namespace"]).exists():
            # 使用模板文件
            with open(self.manifest_files["namespace"], "r") as f:
                namespace_yaml = f.read().replace("${NAMESPACE}", namespace)
        else:
            # 动态生成
            namespace_yaml = f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    name: {namespace}
"""

        result = await self._apply_manifest(namespace_yaml)
        if result["success"]:
            print(f"{self._i18n_manager.t('k8s.namespace_created', namespace=namespace)}")

    async def _apply_base_resources(self, namespace: str):
        """应用基础资源（PVC, Secrets等）"""
        print(f"{self._i18n_manager.t('k8s.applying_base_resources')}")

        # 应用PVC
        if "pvc" in self.manifest_files and Path(self.manifest_files["pvc"]).exists():
            with open(self.manifest_files["pvc"], "r") as f:
                pvc_yaml = f.read().replace("${NAMESPACE}", namespace)
            await self._apply_manifest(pvc_yaml)

        # 应用Secrets（如果存在）
        if "secrets" in self.manifest_files and Path(self.manifest_files["secrets"]).exists():
            with open(self.manifest_files["secrets"], "r") as f:
                secrets_yaml = f.read().replace("${NAMESPACE}", namespace)
            await self._apply_manifest(secrets_yaml)

    async def _generate_manifests(
        self, namespace: str, replicas: int, enable_ingress: bool = False
    ) -> Dict[str, str]:
        """生成或读取Kubernetes清单"""
        manifests = {}

        # 处理Deployment
        if "deployment" in self.manifest_files and Path(self.manifest_files["deployment"]).exists():
            with open(self.manifest_files["deployment"], "r") as f:
                deployment_yaml = f.read()
                deployment_yaml = deployment_yaml.replace("${NAMESPACE}", namespace)
                deployment_yaml = deployment_yaml.replace("${REPLICAS}", str(replicas))
                manifests["deployment"] = deployment_yaml
        else:
            # 动态生成（保持原有逻辑）
            manifests["deployment"] = self._generate_deployment_manifest(namespace, replicas)

        # 处理Service
        if "service" in self.manifest_files and Path(self.manifest_files["service"]).exists():
            with open(self.manifest_files["service"], "r") as f:
                service_yaml = f.read().replace("${NAMESPACE}", namespace)
                manifests["service"] = service_yaml
        else:
            manifests["service"] = self._generate_service_manifest(namespace)

        # 处理Ingress（如果启用）
        if enable_ingress:
            if "ingress" in self.manifest_files and Path(self.manifest_files["ingress"]).exists():
                with open(self.manifest_files["ingress"], "r") as f:
                    ingress_yaml = f.read().replace("${NAMESPACE}", namespace)
                    manifests["ingress"] = ingress_yaml
            else:
                manifests["ingress"] = self._generate_ingress_manifest(namespace)

        return manifests

    def _generate_deployment_manifest(self, namespace: str, replicas: int) -> str:
        """生成Deployment清单（保持原有逻辑）"""
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
        return yaml.dump(deployment)

    def _generate_service_manifest(self, namespace: str) -> str:
        """生成Service清单"""
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
        return yaml.dump(service)

    def _generate_ingress_manifest(self, namespace: str) -> str:
        """生成Ingress清单"""
        ingress = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": "aiforge-ingress",
                "namespace": namespace,
                "labels": {"app": "aiforge-engine"},
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "nginx.ingress.kubernetes.io/proxy-body-size": "50m",
                    "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                    "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                },
            },
            "spec": {
                "ingressClassName": "nginx",
                "rules": [
                    {
                        "host": self.k8s_config.get("ingress", {}).get("host", "aiforge.local"),
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
                ],
            },
        }

        # 如果配置了 TLS，添加 TLS 配置
        if self.k8s_config.get("ingress", {}).get("tls", {}).get("enabled", False):
            ingress["spec"]["tls"] = [
                {
                    "hosts": [self.k8s_config["ingress"]["host"]],
                    "secretName": self.k8s_config["ingress"]["tls"].get(
                        "secretName", "aiforge-tls"
                    ),
                }
            ]

        return yaml.dump(ingress)

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
