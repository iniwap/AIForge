#!/usr/bin/env python3
"""
AIForge Docker 和 SearXNG 服务管理脚本
支持启动、停止、状态检查功能，智能检测 Docker Compose 环境
"""

import requests
import subprocess
import time
import sys
import argparse
import os


class DockerServiceManager:
    def __init__(self):
        self.searxng_container_name = "test-searxng"
        self.searxng_port = "55510"
        self.searxng_url = f"http://localhost:{self.searxng_port}"

    def check_docker_available(self):
        """检查 Docker 是否可用"""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _check_docker_compose_available(self):
        """检查 Docker Compose 是否可用"""
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def check_aiforge_image(self):
        """检查 AIForge 镜像是否存在"""
        try:
            result = subprocess.run(
                ["docker", "images", "aiforge", "--format", "table"], capture_output=True, text=True
            )
            return "aiforge" in result.stdout
        except Exception:
            return False

    def is_searxng_running(self):
        """检查 SearXNG 是否正在运行"""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={self.searxng_container_name}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
            )
            return self.searxng_container_name in result.stdout
        except Exception:
            return False

    def _is_nginx_running(self):
        """检查 nginx 容器是否运行"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=aiforge-nginx", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )
            return "aiforge-nginx" in result.stdout
        except Exception:
            return False

    def _is_docker_compose_running(self):
        """检查 Docker Compose 服务是否运行"""
        try:
            result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=True)
            return len([line for line in result.stdout.split("\n") if "Up" in line]) > 0
        except Exception:
            return False

    def start_searxng(self, dev_mode=False):
        """启动 SearXNG 服务（智能检测环境）"""
        print("🚀 启动 SearXNG 服务...")

        try:
            # 检查是否存在 docker-compose.yml 和 nginx 配置
            has_compose = os.path.exists("docker-compose.yml")
            has_nginx_config = os.path.exists("nginx/nginx.conf")

            if has_compose and has_nginx_config:
                print("🔍 检测到 Docker Compose 配置，使用完整服务栈...")
                return self._start_docker_compose_services(dev_mode)
            else:
                print("⚠️ 未检测到完整配置，使用单容器模式...")
                return self._start_single_searxng_container()
        except Exception as e:
            print(f"❌ 启动异常: {e}")
            return False

    def _start_docker_compose_services(self, dev_mode=False):
        """启动 Docker Compose 服务栈"""
        try:
            # 停止现有服务
            subprocess.run(["docker-compose", "down"], capture_output=True)

            if dev_mode:
                print("🔧 启动开发模式（代码挂载）...")
                print("ℹ️ 开发模式下代码修改将立即生效，无需重新构建...")
                cmd = [
                    "docker-compose",
                    "-f",
                    "docker-compose.yml",
                    "-f",
                    "docker-compose.dev.yml",
                    "up",
                    "-d",
                ]
            else:
                print("🔨 启动生产模式...")
                print("ℹ️ 首次构建可能需要较长时间，请耐心等待...")
                cmd = ["docker-compose", "up", "-d"]

            # 使用实时输出模式显示构建进度
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # 实时显示构建输出
            for line in process.stdout:
                line = line.strip()
                if "Building" in line or "Pulling" in line:
                    print(f"📦 {line}")
                elif "FINISHED" in line or "Created" in line or "Started" in line:
                    print(f"✅ {line}")
                elif "ERROR" in line or "FAILED" in line:
                    print(f"❌ {line}")

            process.wait()

            if process.returncode == 0:
                mode = "开发模式" if dev_mode else "生产模式"
                print(f"✅ {mode} 启动成功")
                return True
            else:
                print("❌ Docker Compose 启动失败")
                print("🔄 回退到单容器模式...")
                return self._start_single_searxng_container()

        except Exception as e:
            print(f"❌ Docker Compose 启动异常: {e}")
            print("🔄 回退到单容器模式...")
            return self._start_single_searxng_container()

    def _start_single_searxng_container(self):
        """启动单独的 SearXNG 容器（回退方案）"""
        # 如果已经在运行，先停止
        if self.is_searxng_running():
            print("⚠️ SearXNG 已在运行，先停止现有容器...")
            self._stop_single_container()

        try:
            # 清理可能存在的停止容器
            subprocess.run(["docker", "rm", self.searxng_container_name], capture_output=True)

            # 启动新容器
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    self.searxng_container_name,
                    "-p",
                    f"{self.searxng_port}:8080",
                    "searxng/searxng:latest",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ SearXNG 容器启动成功")
                return True
            else:
                print(f"❌ SearXNG 启动失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ SearXNG 启动异常: {e}")
            return False

    def stop_searxng(self):
        """停止 SearXNG 服务"""
        print("🛑 停止 SearXNG 服务...")

        try:
            # 首先尝试停止 Docker Compose 服务
            if os.path.exists("docker-compose.yml"):
                result = subprocess.run(["docker-compose", "down"], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Docker Compose 服务已停止")
                    return True

            # 回退到停止单独容器
            return self._stop_single_container()
        except Exception as e:
            print(f"❌ 停止服务失败: {e}")
            return False

    def _stop_single_container(self):
        """停止单独的 SearXNG 容器"""
        try:
            result1 = subprocess.run(
                ["docker", "stop", self.searxng_container_name], capture_output=True, text=True
            )
            subprocess.run(
                ["docker", "rm", self.searxng_container_name], capture_output=True, text=True
            )

            if result1.returncode == 0 or "No such container" in result1.stderr:
                print("✅ SearXNG 服务已停止")
                return True
            else:
                print(f"⚠️ 停止 SearXNG 时出现问题: {result1.stderr}")
                return False
        except Exception as e:
            print(f"❌ 停止单独容器失败: {e}")
            return False

    def verify_searxng(self):
        """验证 SearXNG 服务功能 - 简化版本"""
        print("🔍 验证 SearXNG 服务...")
        print("⏳ 等待服务启动（5秒）...")
        time.sleep(5)

        session = requests.Session()

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # noqa 501
                "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",  # noqa 501
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": f"{self.searxng_url}/",
            }

            # 建立会话
            session.get(f"{self.searxng_url}/", headers=headers, timeout=10)

            # 搜索请求
            search_data = {
                "q": "python",
                "category_general": "1",
                "format": "json",
            }

            response = session.post(
                f"{self.searxng_url}/search", data=search_data, headers=headers, timeout=20
            )

            if response.status_code == 200:
                json_data = response.json()
                results_count = len(json_data.get("results", []))
                print(f"✅ SearXNG 搜索功能正常，返回 {results_count} 个结果")
                return True
            else:
                print(f"❌ SearXNG 搜索失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ SearXNG 验证失败: {e}")
            return False
        finally:
            session.close()

    def cleanup_all_containers(self):
        """清理所有相关容器"""
        print("🧹 清理相关容器...")

        try:
            # 停用 Docker Compose 服务
            if os.path.exists("docker-compose.yml"):
                subprocess.run(["docker-compose", "down"], capture_output=True)

            # 清理 AIForge 相关容器
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=aiforge", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )

            container_names = [name for name in result.stdout.strip().split("\n") if name]

            if container_names:
                for name in container_names:
                    subprocess.run(["docker", "stop", name], capture_output=True)
                    subprocess.run(["docker", "rm", name], capture_output=True)
                print(f"✅ 清理了 {len(container_names)} 个 AIForge 容器")

            # 清理测试容器
            subprocess.run(["docker", "stop", self.searxng_container_name], capture_output=True)
            subprocess.run(["docker", "rm", self.searxng_container_name], capture_output=True)

            return True
        except Exception as e:
            print(f"❌ 清理容器失败: {e}")
            return False

    def check_environment(self):
        """检查环境配置"""
        print("🔍 检查环境配置...")

        checks = {
            "Docker 可用": self.check_docker_available(),
            "Docker Compose 可用": self._check_docker_compose_available(),
            "AIForge 镜像": self.check_aiforge_image(),
            "Docker Compose 文件": os.path.exists("docker-compose.yml"),
            "Nginx 配置文件": os.path.exists("nginx/nginx.conf"),
        }

        for check_name, passed in checks.items():
            status = "✅ 可用" if passed else "❌ 缺失"
            print(f"{check_name}: {status}")

        if checks["Docker Compose 文件"] and checks["Nginx 配置文件"]:
            print("💡 建议使用 Docker Compose 模式以获得最佳体验")
        else:
            print("⚠️ 将使用单容器模式，可能遇到 403 错误")

        return checks

    def show_status(self):
        """显示服务状态"""
        print("📊 服务状态检查:")
        print("=" * 40)

        # Docker 状态
        docker_ok = self.check_docker_available()
        print(f"Docker 环境: {'✅ 可用' if docker_ok else '❌ 不可用'}")

        # AIForge 镜像状态
        image_ok = self.check_aiforge_image()
        print(f"AIForge 镜像: {'✅ 存在' if image_ok else '❌ 不存在'}")

        # SearXNG 状态
        searxng_running = self.is_searxng_running()
        print(f"SearXNG 服务: {'✅ 运行中' if searxng_running else '❌ 未运行'}")

        # Nginx 代理状态
        nginx_running = self._is_nginx_running()
        print(f"Nginx 代理: {'✅ 运行中' if nginx_running else '❌ 未运行'}")

        # Docker Compose 状态
        compose_running = self._is_docker_compose_running()
        print(f"Docker Compose: {'✅ 有服务运行' if compose_running else '❌ 无服务运行'}")

        # 环境配置状态
        print("\n🔧 环境配置:")
        print("-" * 40)

        has_compose_file = os.path.exists("docker-compose.yml")
        print(f"Docker Compose 文件: {'✅ 存在' if has_compose_file else '❌ 缺失'}")

        has_nginx_config = os.path.exists("nginx/nginx.conf")
        print(f"Nginx 配置文件: {'✅ 存在' if has_nginx_config else '❌ 缺失'}")

        # 推荐配置模式
        print("\n💡 推荐配置:")
        if has_compose_file and has_nginx_config:
            print("✅ 建议使用 Docker Compose 模式（完整功能）")
        else:
            print("⚠️ 当前为单容器模式（可能遇到 403 错误）")

    def start_services(self, dev_mode=False):
        """启动所有服务"""
        print("🚀 启动 Docker 和 SearXNG 服务...\n")

        # 检查环境
        if not self.check_docker_available():
            print("❌ Docker 不可用，请先安装 Docker")
            return False

        print("✅ Docker 可用")

        # 启动 SearXNG
        if not self.start_searxng(dev_mode):
            return False

        # 验证服务
        if not self.verify_searxng():
            return False

        print("\n🎉 所有服务启动成功！")
        print(f"SearXNG 访问地址: {self.searxng_url}")
        return True

    def stop_services(self):
        """停止所有服务"""
        print("🛑 停止 Docker 和 SearXNG 服务...\n")

        results = []

        # 停止 SearXNG
        results.append(self.stop_searxng())

        # 清理其他容器
        results.append(self.cleanup_all_containers())

        if all(results):
            print("\n🎉 所有服务已成功停止！")
            print("💡 现在可以正常进行开发工作了")
            return True
        else:
            print("\n⚠️ 部分服务停止失败")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AIForge Docker 服务管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
    # 生产模式启动
    python3 -m src.aiforge.utils.manage_docker_services start

    # 开发模式启动（代码挂载，热重载）
    python3 -m src.aiforge.utils.manage_docker_services start --dev

    # 停止服务
    python3 -m src.aiforge.utils.manage_docker_services stop

    # 查看状态
    python3 -m src.aiforge.utils.manage_docker_services status
        """,
    )

    parser.add_argument(
        "action",
        choices=["start", "stop", "status"],
        help="操作类型: start(启动), stop(停止), status(状态)",
    )

    parser.add_argument("--dev", action="store_true", help="开发模式启动（代码挂载，热重载）")

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
        else:
            success = False

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断操作")
        success = False
    except Exception as e:
        print(f"\n❌ 执行过程中发生异常: {e}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
