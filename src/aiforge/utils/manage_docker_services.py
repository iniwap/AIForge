#!/usr/bin/env python3
"""
AIForge Docker服务管理 - 一体化版本
用户只需执行一行命令即可完成所有初始化工作
"""

import time
import subprocess
import sys
import argparse
from pathlib import Path


class DockerServiceManager:
    """一体化Docker服务管理器"""

    def __init__(self):
        self.compose_file = "docker-compose.yml"
        self.dev_compose_file = "docker-compose.dev.yml"

    def check_docker_environment(self) -> dict:
        """全面检查Docker环境"""
        print("🔍 检查Docker环境...")

        checks = {
            "docker_available": False,
            "docker_compose_available": False,
            "docker_running": False,
            "compose_file_exists": False,
            "dev_compose_file_exists": False,
            "aiforge_image_exists": False,
        }

        # 检查Docker是否安装
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                checks["docker_available"] = True
                print("✅ Docker已安装")
            else:
                print("❌ Docker未安装")
                return checks
        except FileNotFoundError:
            print("❌ Docker未安装或不在PATH中")
            return checks

        # 检查Docker是否运行
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, text=True)
            if result.returncode == 0:
                checks["docker_running"] = True
                print("✅ Docker服务正在运行")
            else:
                print("❌ Docker服务未运行，请启动Docker Desktop")
                return checks
        except Exception:
            print("❌ 无法连接到Docker服务")
            return checks

        # 检查Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                checks["docker_compose_available"] = True
                print("✅ Docker Compose可用")
            else:
                print("❌ Docker Compose不可用")
        except FileNotFoundError:
            print("❌ Docker Compose未安装")

        # 检查配置文件
        if Path(self.compose_file).exists():
            checks["compose_file_exists"] = True
            print("✅ docker-compose.yml存在")
        else:
            print("❌ docker-compose.yml不存在")

        if Path(self.dev_compose_file).exists():
            checks["dev_compose_file_exists"] = True
            print("✅ docker-compose.dev.yml存在")
        else:
            print("ℹ️ docker-compose.dev.yml不存在（开发模式不可用）")

        # 检查AIForge镜像
        try:
            result = subprocess.run(
                [
                    "docker",
                    "images",
                    "--format",
                    "{{.Repository}}:{{.Tag}}",
                    "--filter",
                    "reference=*aiforge*",
                ],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                checks["aiforge_image_exists"] = True
                print("✅ AIForge镜像已存在")
            else:
                print("ℹ️ AIForge镜像不存在，需要构建")
        except Exception:
            print("⚠️ 无法检查AIForge镜像状态")

        return checks

    def build_images_if_needed(self, dev_mode: bool = False) -> bool:
        """智能构建镜像"""
        print("\n🔨 检查并构建必要的镜像...")

        try:
            # 检查是否需要构建
            result = subprocess.run(
                [
                    "docker",
                    "images",
                    "--format",
                    "{{.Repository}}:{{.Tag}}",
                    "--filter",
                    "reference=*aiforge*",
                ],
                capture_output=True,
                text=True,
            )

            if result.stdout.strip():
                print("✅ AIForge镜像已存在，跳过构建")
                return True

            print("📦 开始构建AIForge镜像...")
            print("ℹ️ 首次构建可能需要5-10分钟，请耐心等待...")

            # 构建命令
            cmd = ["docker-compose"]
            if dev_mode and Path(self.dev_compose_file).exists():
                cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
            else:
                cmd.extend(["-f", self.compose_file])
            cmd.extend(["build", "--no-cache"])

            # 实时显示构建进度
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            print("📦 构建进度:")
            for line in process.stdout:
                line = line.strip()
                if line:
                    if "Step" in line:
                        print(f"🔧 {line}")
                    elif "Successfully built" in line or "Successfully tagged" in line:
                        print(f"✅ {line}")
                    elif "ERROR" in line or "FAILED" in line:
                        print(f"❌ {line}")
                    elif any(
                        keyword in line
                        for keyword in ["Downloading", "Extracting", "Pull complete"]
                    ):
                        print(f"⬇️ {line}")

            process.wait()

            if process.returncode == 0:
                print("✅ 镜像构建成功")
                return True
            else:
                print("❌ 镜像构建失败")
                return False

        except Exception as e:
            print(f"❌ 构建过程异常: {e}")
            return False

    def start_services(self, dev_mode: bool = False) -> bool:
        """一体化启动服务"""
        print("🚀 AIForge Docker一体化启动...")
        print("=" * 50)

        # 1. 环境检查
        checks = self.check_docker_environment()

        # 检查必要条件
        if not checks["docker_available"]:
            print("\n❌ Docker未安装，请先安装Docker Desktop")
            print("💡 下载地址: https://www.docker.com/products/docker-desktop")
            return False

        if not checks["docker_running"]:
            print("\n❌ Docker服务未运行")
            print("💡 请启动Docker Desktop并等待其完全启动")
            return False

        if not checks["docker_compose_available"]:
            print("\n❌ Docker Compose不可用")
            return False

        if not checks["compose_file_exists"]:
            print("\n❌ docker-compose.yml文件不存在")
            return False

        if dev_mode and not checks["dev_compose_file_exists"]:
            print("\n⚠️ 开发模式需要docker-compose.dev.yml文件")
            print("💡 将使用生产模式启动")
            dev_mode = False

        print("\n" + "=" * 50)

        # 2. 构建镜像（如果需要）
        if not self.build_images_if_needed(dev_mode):
            return False

        print("\n" + "=" * 50)

        # 3. 启动服务
        print("🚀 启动Docker服务栈...")

        try:
            # 先清理可能存在的旧容器
            print("🧹 清理旧容器...")
            subprocess.run(["docker-compose", "down"], capture_output=True)

            # 构建启动命令
            cmd = ["docker-compose"]
            if dev_mode:
                cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
                print("🔧 开发模式启动（代码热重载）")
            else:
                cmd.extend(["-f", self.compose_file])
                print("🔨 生产模式启动")

            cmd.extend(["up", "-d"])

            # 启动服务
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Docker服务启动成功")

                # 显示服务信息
                self._show_service_urls()

                # 等待服务稳定
                print("\n⏳ 等待服务完全启动...")
                time.sleep(10)

                # 检查服务健康状态
                self._check_service_health()

                # 更新SearXNG配置
                self._check_and_update_searxng_formats()

                print("\n🎉 AIForge Docker服务一体化启动完成！")
                print("💡 现在可以开始使用AIForge了")

                return True
            else:
                print(f"❌ Docker服务启动失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 启动过程异常: {e}")
            return False

    def stop_services(self) -> bool:
        """停止Docker服务栈"""
        if not Path(self.compose_file).exists():
            print("❌ docker-compose.yml文件不存在")
            return False

        print("🛑 停止AIForge Docker服务...")

        try:
            subprocess.run(["docker-compose", "-f", self.compose_file, "down"], check=True)
            print("✅ Docker服务停止成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker服务停止失败: {e}")
            return False

    def show_status(self) -> None:
        """显示Docker服务状态"""
        print("📊 AIForge Docker服务状态:")
        print("=" * 40)

        try:
            result = subprocess.run(
                ["docker-compose", "ps"], capture_output=True, text=True, check=True
            )
            print(result.stdout)
            self._check_service_health()
        except subprocess.CalledProcessError:
            print("❌ 无法获取服务状态")

    def cleanup(self) -> bool:
        """清理Docker资源"""
        print("🧹 清理AIForge Docker资源...")

        try:
            # 停止并移除容器
            subprocess.run(["docker-compose", "down", "-v"], capture_output=True)

            # 清理相关镜像
            subprocess.run(
                [
                    "docker",
                    "image",
                    "prune",
                    "-f",
                    "--filter",
                    "label=com.docker.compose.project=aiforge",
                ],
                capture_output=True,
            )

            print("✅ Docker资源清理完成")
            return True
        except Exception as e:
            print(f"❌ 清理失败: {e}")
            return False

    def _check_service_health(self) -> None:
        """检查服务健康状态"""
        print("\n🏥 服务健康检查:")
        services = {"aiforge-engine": "8000", "aiforge-searxng": "8080", "aiforge-nginx": "55510"}

        for service, port in services.items():
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={service}", "--format", "{{.Status}}"],
                    capture_output=True,
                    text=True,
                )
                status = result.stdout.strip()
                if "Up" in status:
                    print(f"✅ {service}: 运行正常")
                else:
                    print(f"❌ {service}: {status}")
            except Exception:
                print(f"⚠️ {service}: 状态未知")

    def _show_service_urls(self) -> None:
        """显示服务访问地址"""
        print("\n🌐 服务访问地址:")
        print("- AIForge Web: http://localhost:8000")
        print("- SearXNG: http://localhost:55510")
        print("- 管理面板: http://localhost:8000/admin")

    def _check_and_update_searxng_formats(self):
        """更新SearXNG配置以支持多种输出格式"""
        try:
            import yaml
        except ImportError:
            print("⚠️ PyYAML未安装，跳过SearXNG配置更新")
            return False

        settings_file = Path("searxng/settings.yml")

        if not settings_file.exists():
            print("ℹ️ SearXNG配置文件不存在，跳过格式更新")
            return False

        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if "search" not in config:
                config["search"] = {}

            required_formats = ["html", "json", "csv", "rss"]
            current_formats = config["search"].get("formats", [])

            if set(current_formats) != set(required_formats):
                config["search"]["formats"] = required_formats

                with open(settings_file, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

                print("✅ SearXNG配置已更新，支持多种输出格式")
                return True
            else:
                print("✅ SearXNG配置已是最新")
                return False

        except Exception as e:
            print(f"⚠️ 更新SearXNG配置失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AIForge Docker一体化服务管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
一体化使用示例:
    # 一键启动生产模式
    aiforge-docker start

    # 一键启动开发模式（代码热重载）
    aiforge-docker start --dev

    # 停止所有服务
    aiforge-docker stop

    # 查看服务状态
    aiforge-docker status

    # 清理Docker资源
    aiforge-docker cleanup

开发版本使用示例:
    # 直接运行模块
    python -m src.aiforge.utils.manage_docker_services start --dev

    # 或直接运行脚本
    python src/aiforge/utils/manage_docker_services.py start --dev

特性说明:
    ✅ 自动检测Docker环境
    ✅ 智能构建镜像（避免重复构建）
    ✅ 实时显示构建进度
    ✅ 自动配置SearXNG输出格式
    ✅ 服务健康检查
    ✅ 一键清理资源
        """,
    )

    parser.add_argument("action", choices=["start", "stop", "status", "cleanup"], help="操作类型")
    parser.add_argument("--dev", action="store_true", help="开发模式启动（代码热重载）")

    args = parser.parse_args()
    manager = DockerServiceManager()

    try:
        if args.action == "start":
            success = manager.start_services(dev_mode=args.dev)
        elif args.action == "stop":
            success = manager.stop_services()
        elif args.action == "status":
            manager.show_status()
            success = True
        elif args.action == "cleanup":
            success = manager.cleanup()
        else:
            success = False

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        success = False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
