#!/usr/bin/env python3
"""
AIForge Docker服务管理
"""

import time
import subprocess
import sys
import argparse
from pathlib import Path
from ..i18n.manager import AIForgeI18nManager


class DockerServiceManager:
    """一体化Docker服务管理器"""

    def __init__(self):
        # 初始化 i18n 管理器
        self._i18n_manager = AIForgeI18nManager.get_instance()
        # 动态判断是源码环境还是打包环境
        if self._is_source_environment():
            self.compose_file = "docker-compose.yml"
            self.dev_compose_file = "docker-compose.dev.yml"
        else:
            self.compose_file = self._get_package_resource("docker-compose.yml")
            self.dev_compose_file = self._get_package_resource("docker-compose.dev.yml")

    def _is_source_environment(self) -> bool:
        """判断是否为源码环境"""
        current_dir = Path.cwd()
        return (
            (current_dir / "src" / "aiforge").exists()
            and (current_dir / "docker-compose.yml").exists()
            and (current_dir / "pyproject.toml").exists()
        )

    def _get_package_resource(self, filename: str) -> str:
        """获取包内资源路径"""
        try:
            from importlib import resources

            with resources.path("aiforge", "..") as package_root:
                return str(package_root / filename)
        except ImportError:
            import pkg_resources

            package_root = Path(pkg_resources.resource_filename("aiforge", ".."))
            return str(package_root / filename)

    def check_docker_environment(self) -> dict:
        """全面检查Docker环境"""
        print(self._i18n_manager.t("docker.checking_environment"))

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
                print(self._i18n_manager.t("docker.docker_installed"))
            else:
                print(self._i18n_manager.t("docker.docker_not_installed"))
                return checks
        except FileNotFoundError:
            print(self._i18n_manager.t("docker.docker_not_in_path"))
            return checks

        # 检查Docker是否运行
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, text=True)
            if result.returncode == 0:
                checks["docker_running"] = True
                print(self._i18n_manager.t("docker.docker_running"))
            else:
                print(self._i18n_manager.t("docker.docker_not_running"))
                return checks
        except Exception:
            print(self._i18n_manager.t("docker.cannot_connect_docker"))
            return checks

        # 检查Docker Compose
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                checks["docker_compose_available"] = True
                print(self._i18n_manager.t("docker.docker_compose_available"))
            else:
                print(self._i18n_manager.t("docker.docker_compose_not_available"))
        except FileNotFoundError:
            print(self._i18n_manager.t("docker.docker_compose_not_installed"))

        # 检查配置文件
        if Path(self.compose_file).exists():
            checks["compose_file_exists"] = True
            print(self._i18n_manager.t("docker.compose_file_exists"))
        else:
            print(self._i18n_manager.t("docker.compose_file_not_exists"))

        if Path(self.dev_compose_file).exists():
            checks["dev_compose_file_exists"] = True
            print(self._i18n_manager.t("docker.dev_compose_file_exists"))
        else:
            print(self._i18n_manager.t("docker.dev_compose_file_not_exists"))

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
                print(self._i18n_manager.t("docker.aiforge_image_exists"))
            else:
                print(self._i18n_manager.t("docker.aiforge_image_not_exists"))
        except Exception:
            print(self._i18n_manager.t("docker.cannot_check_image_status"))

        return checks

    def build_images_if_needed(self, dev_mode: bool = False) -> bool:
        """智能构建镜像"""
        print(f"\n{self._i18n_manager.t('docker.building_images')}")

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
                print(self._i18n_manager.t("docker.image_exists_skip_build"))
                return True

            print(self._i18n_manager.t("docker.start_building"))
            print(self._i18n_manager.t("docker.build_time_notice"))

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

            print(self._i18n_manager.t("docker.build_progress"))
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
                print(self._i18n_manager.t("docker.build_success"))
                return True
            else:
                print(self._i18n_manager.t("docker.build_failed"))
                return False

        except Exception as e:
            print(self._i18n_manager.t("docker.build_exception", error=str(e)))
            return False

    def start_services(self, dev_mode: bool = False, enable_searxng: bool = False) -> bool:
        """一体化启动服务"""
        print(self._i18n_manager.t("docker.starting_services"))
        print("=" * 50)

        # 1. 环境检查
        checks = self.check_docker_environment()

        # 检查必要条件
        if not checks["docker_available"]:
            print(f"\n{self._i18n_manager.t('docker.docker_not_installed')}")
            print(self._i18n_manager.t("docker.docker_not_installed_help"))
            return False

        if not checks["docker_running"]:
            print(f"\n{self._i18n_manager.t('docker.docker_not_running')}")
            print(self._i18n_manager.t("docker.docker_not_running_help"))
            return False

        if not checks["docker_compose_available"]:
            print(f"\n{self._i18n_manager.t('docker.docker_compose_not_available_msg')}")
            return False

        if not checks["compose_file_exists"]:
            print(f"\n{self._i18n_manager.t('docker.compose_file_not_exists_msg')}")
            return False

        if dev_mode and not checks["dev_compose_file_exists"]:
            print(f"\n{self._i18n_manager.t('docker.dev_compose_file_not_exists')}")
            print(self._i18n_manager.t("docker.dev_mode_fallback"))
            dev_mode = False

        print("\n" + "=" * 50)

        # 2. 构建镜像（如果需要）
        if not self.build_images_if_needed(dev_mode):
            return False

        print("\n" + "=" * 50)

        # 3. 启动服务
        print(self._i18n_manager.t("docker.starting_services"))

        try:
            # 先清理可能存在的旧容器
            print(self._i18n_manager.t("docker.cleaning_old_containers"))
            subprocess.run(["docker-compose", "down"], capture_output=True)

            # 构建启动命令
            cmd = ["docker-compose"]
            if dev_mode:
                cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
                print(self._i18n_manager.t("docker.dev_mode_start"))
            else:
                cmd.extend(["-f", self.compose_file])
                print(self._i18n_manager.t("docker.production_mode_start"))

            # 添加 profile 支持
            if enable_searxng:
                cmd.extend(["--profile", "searxng"])
                print(self._i18n_manager.t("docker.searxng_enabled"))
            else:
                print(self._i18n_manager.t("docker.searxng_not_enabled"))

            cmd.extend(["up", "-d"])

            # 启动服务
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(self._i18n_manager.t("docker.service_start_success"))

                # 显示服务信息
                self._show_service_urls(enable_searxng)

                # 等待服务稳定
                print(f"\n{self._i18n_manager.t('docker.waiting_services')}")
                time.sleep(10)

                # 检查服务健康状态
                self._check_service_health(enable_searxng)

                # 更新SearXNG配置（仅当启用时）
                if enable_searxng:
                    self._check_and_update_searxng_formats()

                print(f"\n{self._i18n_manager.t('docker.startup_complete')}")
                print(self._i18n_manager.t("docker.ready_to_use"))

                return True
            else:
                print(self._i18n_manager.t("docker.service_start_failed", error=result.stderr))
                return False

        except Exception as e:
            print(self._i18n_manager.t("docker.startup_exception", error=str(e)))
            return False

    def stop_services(self) -> bool:
        """停止Docker服务栈"""
        if not Path(self.compose_file).exists():
            print(self._i18n_manager.t("docker.compose_file_not_exists_msg"))
            return False

        print(self._i18n_manager.t("docker.stopping_services"))

        try:
            subprocess.run(["docker-compose", "-f", self.compose_file, "down"], check=True)
            print(self._i18n_manager.t("docker.stop_success"))
            return True
        except subprocess.CalledProcessError as e:
            print(self._i18n_manager.t("docker.stop_failed", error=str(e)))
            return False

    def show_status(self) -> None:
        """显示Docker服务状态"""
        print(self._i18n_manager.t("docker.service_status"))
        print("=" * 40)

        try:
            result = subprocess.run(
                ["docker-compose", "ps"], capture_output=True, text=True, check=True
            )
            print(result.stdout)
            self._check_service_health()
        except subprocess.CalledProcessError:
            print(self._i18n_manager.t("docker.cannot_get_status"))

    def cleanup(self) -> bool:
        """清理Docker资源"""
        print(self._i18n_manager.t("docker.cleaning_resources"))

        try:
            # 停止并移除容器
            subprocess.run(["docker-compose", "down", "-v"], capture_output=True)
            subprocess.run(
                ["docker-compose", "--profile", "searxng", "down", "-v", "--remove-orphans"],
                capture_output=True,
            )

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

            print(self._i18n_manager.t("docker.cleanup_success"))
            return True
        except Exception as e:
            print(self._i18n_manager.t("docker.cleanup_failed", error=str(e)))
            return False

    def deep_cleanup(self) -> bool:
        """彻底清理AIForge相关资源，但保留基础镜像"""
        print(self._i18n_manager.t("docker.deep_cleanup_start"))
        print(self._i18n_manager.t("docker.deep_cleanup_warning"))

        try:
            # 1. 停止所有服务
            print(self._i18n_manager.t("docker.stopping_all_services"))
            subprocess.run(
                ["docker-compose", "down", "-v", "--remove-orphans"], capture_output=True
            )
            subprocess.run(
                ["docker-compose", "--profile", "searxng", "down", "-v", "--remove-orphans"],
                capture_output=True,
            )

            # 2. 只清理AIForge构建的镜像，保留基础镜像
            print(self._i18n_manager.t("docker.cleaning_built_images"))
            self._remove_aiforge_built_images_only()

            # 3. 清理构建缓存（但不影响基础镜像）
            print(self._i18n_manager.t("docker.cleaning_build_cache"))
            subprocess.run(["docker", "builder", "prune", "-f"], capture_output=True)

            # 4. 清理悬空资源（不影响基础镜像）
            print(self._i18n_manager.t("docker.cleaning_dangling_resources"))
            subprocess.run(["docker", "image", "prune", "-f"], capture_output=True)
            subprocess.run(["docker", "volume", "prune", "-f"], capture_output=True)

            print(self._i18n_manager.t("docker.deep_cleanup_success"))
            return True

        except Exception as e:
            print(self._i18n_manager.t("docker.deep_cleanup_failed", error=str(e)))
            return False

    def _remove_aiforge_built_images_only(self):
        """只移除AIForge构建的镜像，保留基础镜像"""
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}"],
                capture_output=True,
                text=True,
            )

            if not result.stdout.strip():
                return

            preserve_images = {"python", "searxng/searxng", "nginx"}
            images_to_remove = []

            for line in result.stdout.strip().split("\n"):
                if "\t" in line:
                    repo_tag, image_id = line.split("\t", 1)
                    repo = repo_tag.split(":")[0]

                    if any(keyword in repo.lower() for keyword in ["aiforge"]):
                        if not any(base in repo.lower() for base in preserve_images):
                            images_to_remove.append(image_id)

            # 删除镜像
            for image_id in images_to_remove:
                subprocess.run(["docker", "rmi", "-f", image_id], capture_output=True)

            if images_to_remove:
                print(self._i18n_manager.t("docker.removed_images", count=len(images_to_remove)))
            else:
                print(self._i18n_manager.t("docker.no_images_to_remove"))

        except Exception as e:
            print(self._i18n_manager.t("docker.cleanup_images_error", error=str(e)))

    def _check_service_health(self, enable_searxng: bool = False) -> None:
        """检查服务健康状态"""
        print(f"\n{self._i18n_manager.t('docker.health_check')}")
        services = {"aiforge-engine": "8000"}

        if enable_searxng:
            services.update({"aiforge-searxng": "8080", "aiforge-nginx": "55510"})

        for service, port in services.items():
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={service}", "--format", "{{.Status}}"],
                    capture_output=True,
                    text=True,
                )
                status = result.stdout.strip()
                if "Up" in status:
                    print(self._i18n_manager.t("docker.service_running", service=service))
                else:
                    print(
                        self._i18n_manager.t(
                            "docker.service_not_running", service=service, status=status
                        )
                    )
            except Exception:
                print(self._i18n_manager.t("docker.service_status_unknown", service=service))

    def _show_service_urls(self, enable_searxng: bool = False) -> None:
        """显示服务访问地址"""
        print(f"\n{self._i18n_manager.t('docker.service_urls')}")
        print(self._i18n_manager.t("docker.aiforge_web_url"))
        if enable_searxng:
            print(self._i18n_manager.t("docker.searxng_url"))
        print(self._i18n_manager.t("docker.admin_panel_url"))

    def _check_and_update_searxng_formats(self):
        """更新SearXNG配置以支持多种输出格式"""
        try:
            import yaml
        except ImportError:
            print(self._i18n_manager.t("docker.pyyaml_not_installed"))
            return False

        settings_file = Path("searxng/settings.yml")

        if not settings_file.exists():
            print(self._i18n_manager.t("docker.searxng_config_not_exists"))
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

                print(self._i18n_manager.t("docker.searxng_config_updated"))
                return True
            else:
                print(self._i18n_manager.t("docker.searxng_config_latest"))
                return False

        except Exception as e:
            print(self._i18n_manager.t("docker.searxng_config_update_failed", error=str(e)))
            return False


def main():
    """主函数"""
    manager = DockerServiceManager()

    parser = argparse.ArgumentParser(
        description=manager._i18n_manager.t("docker.cli.description"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=manager._i18n_manager.t("docker.cli.epilog"),
    )

    parser.add_argument(
        "action",
        choices=["start", "stop", "status", "cleanup", "deep-cleanup"],
        help=manager._i18n_manager.t("docker.cli.action_help"),
    )
    parser.add_argument(
        "--dev", action="store_true", help=manager._i18n_manager.t("docker.cli.dev_help")
    )
    parser.add_argument(
        "--searxng", action="store_true", help=manager._i18n_manager.t("docker.cli.searxng_help")
    )

    args = parser.parse_args()

    try:
        if args.action == "start":
            success = manager.start_services(dev_mode=args.dev, enable_searxng=args.searxng)
        elif args.action == "stop":
            success = manager.stop_services()
        elif args.action == "status":
            manager.show_status()
            success = True
        elif args.action == "cleanup":
            success = manager.cleanup()
        elif args.action == "deep-cleanup":
            success = manager.deep_cleanup()
        else:
            success = False

    except KeyboardInterrupt:
        print(f"\n{manager._i18n_manager.t('docker.user_interrupted')}")
        success = False
    except Exception as e:
        print(manager._i18n_manager.t("docker.execution_exception", error=str(e)))
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
