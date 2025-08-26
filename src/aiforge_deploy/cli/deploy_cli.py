#!/usr/bin/env python3
"""AIForge 统一部署CLI"""

import sys
import asyncio
import argparse
from ..core.deployment_manager import DeploymentManager, DeploymentType
from ..core.config_manager import DeploymentConfigManager
from aiforge import GlobalI18nManager


def main():
    """统一部署CLI入口"""
    # 获取i18n管理器
    i18n_manager = GlobalI18nManager.get_instance()

    parser = argparse.ArgumentParser(
        description=i18n_manager.t("deploy_cli.description"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 全局选项
    parser.add_argument("--config", help=i18n_manager.t("deploy_cli.global_options.config"))
    parser.add_argument(
        "--docker-compose", help=i18n_manager.t("deploy_cli.global_options.docker_compose")
    )
    parser.add_argument("--k8s-config", help=i18n_manager.t("deploy_cli.global_options.k8s_config"))
    parser.add_argument(
        "--terraform-config", help=i18n_manager.t("deploy_cli.global_options.terraform_config")
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help=i18n_manager.t("deploy_cli.global_options.verbose"),
    )

    subparsers = parser.add_subparsers(dest="command", help="", required=True)

    # Docker部署
    docker_parser = subparsers.add_parser(
        "docker", help=i18n_manager.t("deploy_cli.commands.docker")
    )
    docker_parser.add_argument("action", choices=["start", "stop", "status", "cleanup"])
    docker_parser.add_argument(
        "--dev", action="store_true", help=i18n_manager.t("deploy_cli.docker_options.dev")
    )
    docker_parser.add_argument(
        "--searxng", action="store_true", help=i18n_manager.t("deploy_cli.docker_options.searxng")
    )
    docker_parser.add_argument(
        "--host", default="127.0.0.1", help=i18n_manager.t("deploy_cli.docker_options.host")
    )
    docker_parser.add_argument(
        "--port", type=int, default=8000, help=i18n_manager.t("deploy_cli.docker_options.port")
    )
    docker_parser.add_argument(
        "--deep", action="store_true", help=i18n_manager.t("deploy_cli.docker_options.deep")
    )
    docker_parser.add_argument(
        "--core-only",
        action="store_true",
        help=i18n_manager.t("deploy_cli.docker_options.core_only"),
    )
    docker_parser.add_argument(
        "--web-optional",
        action="store_true",
        help=i18n_manager.t("deploy_cli.docker_options.web_optional"),
    )

    # Kubernetes部署
    k8s_parser = subparsers.add_parser("k8s", help=i18n_manager.t("deploy_cli.commands.k8s"))
    k8s_parser.add_argument("action", choices=["deploy", "delete", "status", "upgrade"])
    k8s_parser.add_argument(
        "--namespace", default="aiforge", help=i18n_manager.t("deploy_cli.k8s_options.namespace")
    )
    k8s_parser.add_argument(
        "--replicas", type=int, default=1, help=i18n_manager.t("deploy_cli.k8s_options.replicas")
    )

    # 云部署
    cloud_parser = subparsers.add_parser("cloud", help=i18n_manager.t("deploy_cli.commands.cloud"))
    cloud_parser.add_argument("provider", choices=["aws", "azure", "gcp", "aliyun"])
    cloud_parser.add_argument("action", choices=["deploy", "destroy", "status"])
    cloud_parser.add_argument("--region", help=i18n_manager.t("deploy_cli.cloud_options.region"))
    cloud_parser.add_argument(
        "--instance-type", help=i18n_manager.t("deploy_cli.cloud_options.instance_type")
    )

    args = parser.parse_args()

    try:
        # 初始化配置和部署管理器
        config_manager = DeploymentConfigManager()
        config_manager.initialize_deployment_config(
            deployment_config_file=args.config,
            docker_compose_file=args.docker_compose,
            kubernetes_config_file=args.k8s_config,
            terraform_config_file=args.terraform_config,
        )
        deployment_manager = DeploymentManager(config_manager)

        # 执行相应的部署命令
        if args.command == "docker":
            asyncio.run(handle_docker_command(deployment_manager, args, i18n_manager))
        elif args.command == "k8s":
            asyncio.run(handle_k8s_command(deployment_manager, args, i18n_manager))
        elif args.command == "cloud":
            asyncio.run(handle_cloud_command(deployment_manager, args, i18n_manager))
    except Exception as e:
        print(i18n_manager.t("deploy_cli.messages.execution_error", error=str(e)))
        if args.verbose:
            import traceback

            traceback.print_exc()


async def handle_docker_command(deployment_manager, args, i18n_manager):
    """处理Docker命令"""
    if args.action == "start":
        # 添加mode参数支持
        deploy_kwargs = {
            "dev_mode": args.dev,
            "enable_searxng": args.searxng,
            "host": args.host,
            "port": args.port,
            "enable_web": not args.core_only,
        }

        # 如果指定了mode，添加到参数中
        if hasattr(args, "mode"):
            deploy_kwargs["mode"] = args.mode

        result = await deployment_manager.deploy(DeploymentType.DOCKER, **deploy_kwargs)
        success_text = (
            i18n_manager.t("deploy_cli.messages.success")
            if result.get("success")
            else i18n_manager.t("deploy_cli.messages.failed")
        )
        print(i18n_manager.t("deploy_cli.messages.docker_deploy_result", result=success_text))

        # 显示部署模式信息
        if result.get("success"):
            if args.core_only:
                print(i18n_manager.t("deploy_cli.messages.core_mode_started"))
            else:
                print(i18n_manager.t("deploy_cli.messages.web_mode_started"))

    elif args.action == "stop":
        result = await deployment_manager.stop(DeploymentType.DOCKER)
        success_text = (
            i18n_manager.t("deploy_cli.messages.success")
            if result
            else i18n_manager.t("deploy_cli.messages.failed")
        )
        print(i18n_manager.t("deploy_cli.messages.docker_stop_result", result=success_text))

    elif args.action == "status":
        result = await deployment_manager.status(DeploymentType.DOCKER)
        print(i18n_manager.t("deploy_cli.messages.docker_status", status=result))

    elif args.action == "cleanup":
        if getattr(args, "deep", False):
            # 深度清理
            result = await deployment_manager.deep_cleanup(DeploymentType.DOCKER)
        else:
            # 普通清理
            result = await deployment_manager.cleanup(DeploymentType.DOCKER)

        success_text = (
            i18n_manager.t("deploy_cli.messages.success")
            if result
            else i18n_manager.t("deploy_cli.messages.failed")
        )


async def handle_k8s_command(deployment_manager, args, i18n_manager):
    """处理Kubernetes命令"""
    if args.action == "deploy":
        result = await deployment_manager.deploy(
            DeploymentType.KUBERNETES, namespace=args.namespace, replicas=args.replicas
        )
        success_text = (
            i18n_manager.t("deploy_cli.messages.success")
            if result.get("success")
            else i18n_manager.t("deploy_cli.messages.failed")
        )
        print(i18n_manager.t("deploy_cli.messages.k8s_deploy_result", result=success_text))

        if result.get("success"):
            print(
                i18n_manager.t(
                    "deploy_cli.messages.deployed_to_namespace",
                    namespace=result.get("namespace", args.namespace),
                )
            )
            print(
                i18n_manager.t(
                    "deploy_cli.messages.replica_count",
                    replicas=result.get("replicas", args.replicas),
                )
            )
        else:
            print(
                i18n_manager.t(
                    "deploy_cli.messages.error_message",
                    message=result.get(
                        "message", i18n_manager.t("deploy_cli.messages.unknown_error")
                    ),
                )
            )

    elif args.action == "status":
        result = await deployment_manager.status(DeploymentType.KUBERNETES)
        if result.get("success"):
            pods = result.get("pods", [])
            print(i18n_manager.t("deploy_cli.messages.k8s_status", count=len(pods)))
            for pod in pods:
                name = pod.get("metadata", {}).get("name", "Unknown")
                status = pod.get("status", {}).get("phase", "Unknown")
                print(i18n_manager.t("deploy_cli.messages.pod_status", name=name, status=status))
        else:
            print(
                i18n_manager.t(
                    "deploy_cli.messages.cloud_status_failed",
                    provider="K8s",
                    error=result.get("error", i18n_manager.t("deploy_cli.messages.unknown_error")),
                )
            )

    elif args.action == "delete":
        result = await deployment_manager.stop(DeploymentType.KUBERNETES)
        success_text = (
            i18n_manager.t("deploy_cli.messages.success")
            if result
            else i18n_manager.t("deploy_cli.messages.failed")
        )
        print(i18n_manager.t("deploy_cli.messages.k8s_delete_result", result=success_text))

    elif args.action == "upgrade":
        # 先停止，再重新部署
        stop_result = await deployment_manager.stop(DeploymentType.KUBERNETES)
        if stop_result:
            result = await deployment_manager.deploy(
                DeploymentType.KUBERNETES, namespace=args.namespace, replicas=args.replicas
            )
            success_text = (
                i18n_manager.t("deploy_cli.messages.success")
                if result.get("success")
                else i18n_manager.t("deploy_cli.messages.failed")
            )
            print(i18n_manager.t("deploy_cli.messages.k8s_upgrade_result", result=success_text))
        else:
            print(i18n_manager.t("deploy_cli.messages.k8s_upgrade_failed"))


async def handle_cloud_command(deployment_manager, args, i18n_manager):
    """处理云部署命令"""
    # 根据提供商选择部署类型
    provider_map = {
        "aws": DeploymentType.CLOUD_AWS,
        "azure": DeploymentType.CLOUD_AZURE,
        "gcp": DeploymentType.CLOUD_GCP,
        "aliyun": DeploymentType.CLOUD_ALIYUN,
    }

    deployment_type = provider_map.get(args.provider)
    if not deployment_type:
        print(i18n_manager.t("deploy_cli.messages.unsupported_provider", provider=args.provider))
        return

    if args.action == "deploy":
        deploy_kwargs = {}
        if args.region:
            deploy_kwargs["region"] = args.region
        if args.instance_type:
            deploy_kwargs["instance_type"] = args.instance_type

        result = await deployment_manager.deploy(deployment_type, **deploy_kwargs)

        if result.get("success"):
            print(
                i18n_manager.t("deploy_cli.messages.cloud_deploy_success", provider=args.provider)
            )
            if "instance_id" in result:
                print(
                    i18n_manager.t(
                        "deploy_cli.messages.instance_id", instance_id=result["instance_id"]
                    )
                )
            if "deploy_result" in result:
                deploy_info = result["deploy_result"]
                if deploy_info.get("success"):
                    print(i18n_manager.t("deploy_cli.messages.app_deploy_complete"))
                else:
                    print(
                        i18n_manager.t(
                            "deploy_cli.messages.app_deploy_failed",
                            error=deploy_info.get(
                                "error", i18n_manager.t("deploy_cli.messages.unknown_error")
                            ),
                        )
                    )
        else:
            print(
                i18n_manager.t(
                    "deploy_cli.messages.cloud_deploy_failed",
                    provider=args.provider,
                    message=result.get(
                        "message", i18n_manager.t("deploy_cli.messages.unknown_error")
                    ),
                )
            )

    elif args.action == "status":
        result = await deployment_manager.status(deployment_type)
        if result.get("success"):
            instances = result.get("instances", [])
            print(
                i18n_manager.t(
                    "deploy_cli.messages.cloud_status", provider=args.provider, count=len(instances)
                )
            )
            for instance in instances:
                instance_id = instance.get("instance_id", "Unknown")
                status = instance.get("status", {})
                state = status.get("state", "Unknown")
                public_ip = status.get("public_ip", "N/A")
                print(
                    i18n_manager.t(
                        "deploy_cli.messages.instance_status",
                        instance_id=instance_id,
                        state=state,
                        public_ip=public_ip,
                    )
                )
        else:
            print(
                i18n_manager.t(
                    "deploy_cli.messages.cloud_status_failed",
                    provider=args.provider,
                    error=result.get("error", i18n_manager.t("deploy_cli.messages.unknown_error")),
                )
            )

    elif args.action == "destroy":
        result = await deployment_manager.cleanup(deployment_type)
        success_text = (
            i18n_manager.t("deploy_cli.messages.success")
            if result
            else i18n_manager.t("deploy_cli.messages.failed")
        )
        print(
            i18n_manager.t(
                "deploy_cli.messages.cloud_destroy_result",
                provider=args.provider,
                result=success_text,
            )
        )
        if result:
            print(i18n_manager.t("deploy_cli.messages.cloud_destroy_success"))
        else:
            print(i18n_manager.t("deploy_cli.messages.cloud_destroy_error"))


if __name__ == "__main__":
    sys.exit(main())
