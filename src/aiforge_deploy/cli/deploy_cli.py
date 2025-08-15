#!/usr/bin/env python3
"""AIForge 统一部署CLI"""

import asyncio
import argparse
from ..core.deployment_manager import DeploymentManager, DeploymentType
from ..core.config_manager import DeploymentConfigManager


def main():
    """统一部署CLI入口"""
    parser = argparse.ArgumentParser(
        description="AIForge 统一部署管理工具", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 全局选项
    parser.add_argument("--config", help="部署配置文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    subparsers = parser.add_subparsers(dest="command", help="部署命令", required=True)

    # Docker部署
    docker_parser = subparsers.add_parser("docker", help="Docker部署")
    docker_parser.add_argument("action", choices=["start", "stop", "status", "cleanup"])
    docker_parser.add_argument("--dev", action="store_true", help="开发模式")
    docker_parser.add_argument("--searxng", action="store_true", help="启用SearXNG")
    docker_parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    docker_parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    docker_parser.add_argument("--deep", action="store_true", help="深度清理（仅用于cleanup）")
    docker_parser.add_argument(
        "--mode",
        choices=["core", "web"],
        default="web",
        help="部署模式：core(仅CLI) 或 web(Web界面)",
    )
    docker_parser.add_argument("--web-optional", action="store_true", help="使web组件可选")
    # Kubernetes部署
    k8s_parser = subparsers.add_parser("k8s", help="Kubernetes部署")
    k8s_parser.add_argument("action", choices=["deploy", "delete", "status", "upgrade"])
    k8s_parser.add_argument("--namespace", default="aiforge", help="命名空间")
    k8s_parser.add_argument("--replicas", type=int, default=1, help="副本数量")

    # 云部署
    cloud_parser = subparsers.add_parser("cloud", help="云部署")
    cloud_parser.add_argument("provider", choices=["aws", "azure", "gcp", "aliyun"])
    cloud_parser.add_argument("action", choices=["deploy", "destroy", "status"])
    cloud_parser.add_argument("--region", help="部署区域")
    cloud_parser.add_argument("--instance-type", help="实例类型")

    args = parser.parse_args()

    try:
        # 初始化配置和部署管理器
        config_manager = DeploymentConfigManager()
        config_manager.initialize_deployment_config(deployment_config_file=args.config)
        deployment_manager = DeploymentManager(config_manager)

        # 执行相应的部署命令
        if args.command == "docker":
            asyncio.run(handle_docker_command(deployment_manager, args))
        elif args.command == "k8s":
            asyncio.run(handle_k8s_command(deployment_manager, args))
        elif args.command == "cloud":
            asyncio.run(handle_cloud_command(deployment_manager, args))

    except KeyboardInterrupt:
        print("\\n用户中断操作")
    except Exception as e:
        print(f"执行异常: {str(e)}")
        if args.verbose:
            import traceback

            traceback.print_exc()


async def handle_docker_command(deployment_manager, args):
    """处理Docker命令"""
    if args.action == "start":
        # 添加mode参数支持
        deploy_kwargs = {
            "dev_mode": args.dev,
            "enable_searxng": args.searxng,
            "host": args.host,
            "port": args.port,
        }

        # 如果指定了mode，添加到参数中
        if hasattr(args, "mode"):
            deploy_kwargs["mode"] = args.mode

        result = await deployment_manager.deploy(DeploymentType.DOCKER, **deploy_kwargs)
        print(f"Docker部署结果: {'成功' if result.get('success') else '失败'}")

        # 显示部署模式信息
        if result.get("success") and "mode" in deploy_kwargs:
            mode = deploy_kwargs["mode"]
            if mode == "core":
                print("📦 已启动核心CLI模式（无Web界面）")
            elif mode == "web":
                print("🌐 已启动Web界面模式")

    elif args.action == "stop":
        result = await deployment_manager.stop(DeploymentType.DOCKER)
        print(f"Docker停止结果: {'成功' if result else '失败'}")

    elif args.action == "status":
        result = await deployment_manager.status(DeploymentType.DOCKER)
        print(f"Docker状态: {result}")

    elif args.action == "cleanup":
        if getattr(args, "deep", False):
            # 深度清理
            result = await deployment_manager.providers[DeploymentType.DOCKER].deep_cleanup()
        else:
            # 普通清理
            result = await deployment_manager.cleanup(DeploymentType.DOCKER)
        print(f"Docker清理结果: {'成功' if result else '失败'}")


async def handle_k8s_command(deployment_manager, args):
    """处理Kubernetes命令"""
    if args.action == "deploy":
        result = await deployment_manager.deploy(
            DeploymentType.KUBERNETES, namespace=args.namespace, replicas=args.replicas
        )
        print(f"K8s部署结果: {'成功' if result.get('success') else '失败'}")
        if result.get("success"):
            print(f"部署到命名空间: {result.get('namespace', args.namespace)}")
            print(f"副本数量: {result.get('replicas', args.replicas)}")
        else:
            print(f"错误信息: {result.get('message', '未知错误')}")

    elif args.action == "status":
        result = await deployment_manager.status(DeploymentType.KUBERNETES)
        if result.get("success"):
            pods = result.get("pods", [])
            print(f"K8s状态: 找到 {len(pods)} 个Pod")
            for pod in pods:
                name = pod.get("metadata", {}).get("name", "Unknown")
                status = pod.get("status", {}).get("phase", "Unknown")
                print(f"  Pod {name}: {status}")
        else:
            print(f"获取K8s状态失败: {result.get('error', '未知错误')}")

    elif args.action == "delete":
        result = await deployment_manager.stop(DeploymentType.KUBERNETES)
        print(f"K8s删除结果: {'成功' if result else '失败'}")

    elif args.action == "upgrade":
        # 先停止，再重新部署
        stop_result = await deployment_manager.stop(DeploymentType.KUBERNETES)
        if stop_result:
            result = await deployment_manager.deploy(
                DeploymentType.KUBERNETES, namespace=args.namespace, replicas=args.replicas
            )
            print(f"K8s升级结果: {'成功' if result.get('success') else '失败'}")
        else:
            print("K8s升级失败: 无法停止现有部署")


async def handle_cloud_command(deployment_manager, args):
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
        print(f"不支持的云提供商: {args.provider}")
        return

    if args.action == "deploy":
        deploy_kwargs = {}
        if args.region:
            deploy_kwargs["region"] = args.region
        if args.instance_type:
            deploy_kwargs["instance_type"] = args.instance_type

        result = await deployment_manager.deploy(deployment_type, **deploy_kwargs)

        if result.get("success"):
            print(f"{args.provider}部署成功!")
            if "instance_id" in result:
                print(f"实例ID: {result['instance_id']}")
            if "deploy_result" in result:
                deploy_info = result["deploy_result"]
                if deploy_info.get("success"):
                    print("应用部署完成")
                else:
                    print(f"应用部署失败: {deploy_info.get('error', '未知错误')}")
        else:
            print(f"{args.provider}部署失败: {result.get('message', '未知错误')}")

    elif args.action == "status":
        result = await deployment_manager.status(deployment_type)
        if result.get("success"):
            instances = result.get("instances", [])
            print(f"{args.provider}状态: 找到 {len(instances)} 个实例")
            for instance in instances:
                instance_id = instance.get("instance_id", "Unknown")
                status = instance.get("status", {})
                state = status.get("state", "Unknown")
                public_ip = status.get("public_ip", "N/A")
                print(f"  实例 {instance_id}: {state} (IP: {public_ip})")
        else:
            print(f"获取{args.provider}状态失败: {result.get('error', '未知错误')}")

    elif args.action == "destroy":
        result = await deployment_manager.cleanup(deployment_type)
        print(f"{args.provider}销毁结果: {'成功' if result else '失败'}")
        if result:
            print("所有云资源已清理完成")
        else:
            print("销毁过程中遇到错误，请检查云控制台")


if __name__ == "__main__":
    main()
