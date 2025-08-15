import asyncio
from pathlib import Path
from typing import Dict, Any
from ..core.deployment_manager import BaseDeploymentProvider
from .compose_generator import ComposeGenerator
from aiforge import AIForgeI18nManager


class DockerDeploymentProvider(BaseDeploymentProvider):
    """Docker部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "docker"
        self.compose_generator = ComposeGenerator(config_manager)

        # 获取i18n管理器
        self._i18n_manager = AIForgeI18nManager.get_instance()

        # 获取Docker配置
        self.docker_config = config_manager.get_docker_config()

        # 设置compose文件路径
        if self._is_source_environment():
            self.compose_file = "docker-compose.yml"
            self.dev_compose_file = "docker-compose.dev.yml"
        else:
            self.compose_file = self._get_template_path("docker-compose.yml")
            self.dev_compose_file = self._get_template_path("docker-compose.dev.yml")

    def _is_source_environment(self) -> bool:
        """检查是否在源码环境"""
        current_dir = Path.cwd()
        return (
            (current_dir / "src" / "aiforge").exists()
            and (current_dir / "docker-compose.yml").exists()
            and (current_dir / "pyproject.toml").exists()
        )

    def _get_template_path(self, filename: str) -> str:
        """获取模板文件路径"""
        try:
            from importlib import resources

            with resources.path("aiforge_deploy.docker.templates", filename) as path:
                return str(path)
        except Exception:
            return filename

    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署Docker服务"""
        dev_mode = kwargs.get("dev_mode", False)
        enable_searxng = kwargs.get("enable_searxng", False)
        mode = kwargs.get("mode", "web")

        print(self._i18n_manager.t("docker.starting_services"))
        print("=" * 50)

        # 显示部署模式
        if mode == "core":
            print("📦 部署模式: 核心CLI（无Web依赖）")
        elif mode == "web":
            print("🌐 部署模式: Web界面")

        # 1. 环境检查
        env_check = await self._check_environment()
        if not env_check["success"]:
            return {"success": False, "message": "Environment check failed", "details": env_check}

        # 检查必要条件
        checks = env_check["checks"]
        if not checks["docker_available"]:
            print(f"\n{self._i18n_manager.t('docker.docker_not_installed')}")
            print(self._i18n_manager.t("docker.docker_not_installed_help"))
            return {"success": False, "message": "Docker not available"}

        if not checks["docker_running"]:
            print(f"\n{self._i18n_manager.t('docker.docker_not_running')}")
            print(self._i18n_manager.t("docker.docker_not_running_help"))
            return {"success": False, "message": "Docker not running"}

        if not checks["compose_available"]:
            print(f"\n{self._i18n_manager.t('docker.docker_compose_not_available_msg')}")
            return {"success": False, "message": "Docker Compose not available"}

        if not checks["compose_file_exists"]:
            print(f"\n{self._i18n_manager.t('docker.compose_file_not_exists_msg')}")
            return {"success": False, "message": "Compose file not exists"}

        if dev_mode and not checks["dev_compose_file_exists"]:
            print(f"\n{self._i18n_manager.t('docker.dev_compose_file_not_exists')}")
            print(self._i18n_manager.t("docker.dev_mode_fallback"))
            dev_mode = False

        print("\n" + "=" * 50)

        # 2. 构建镜像（如果需要）
        build_result = await self._build_images_if_needed(dev_mode)
        if not build_result["success"]:
            return build_result

        print("\n" + "=" * 50)

        # 3. 启动服务
        start_result = await self._start_services(dev_mode, enable_searxng, mode)

        return start_result

    async def _check_environment(self) -> Dict[str, Any]:
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
            result = await asyncio.create_subprocess_exec(
                "docker",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
            if result.returncode == 0:
                checks["docker_available"] = True
                print(self._i18n_manager.t("docker.docker_installed"))
            else:
                print(self._i18n_manager.t("docker.docker_not_installed"))
                return {"success": False, "checks": checks}
        except FileNotFoundError:
            print(self._i18n_manager.t("docker.docker_not_in_path"))
            return {"success": False, "checks": checks}

        # 检查Docker是否运行
        try:
            result = await asyncio.create_subprocess_exec(
                "docker", "info", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            if result.returncode == 0:
                checks["docker_running"] = True
                print(self._i18n_manager.t("docker.docker_running"))
            else:
                print(self._i18n_manager.t("docker.docker_not_running"))
                return {"success": False, "checks": checks}
        except Exception:
            print(self._i18n_manager.t("docker.cannot_connect_docker"))
            return {"success": False, "checks": checks}

        # 检查Docker Compose
        try:
            result = await asyncio.create_subprocess_exec(
                "docker-compose",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()
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
            result = await asyncio.create_subprocess_exec(
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "--filter",
                "reference=*aiforge*",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            if stdout.decode().strip():
                checks["aiforge_image_exists"] = True
                print(self._i18n_manager.t("docker.aiforge_image_exists"))
            else:
                print(self._i18n_manager.t("docker.aiforge_image_not_exists"))
        except Exception:
            print(self._i18n_manager.t("docker.cannot_check_image_status"))

        success = all(
            [
                checks["docker_available"],
                checks["docker_running"],
                checks["docker_compose_available"],
                checks["compose_file_exists"],
            ]
        )

        return {"success": success, "checks": checks}

    async def _build_images_if_needed(self, dev_mode: bool = False) -> Dict[str, Any]:
        """智能构建镜像"""
        print(f"\n{self._i18n_manager.t('docker.building_images')}")

        try:
            # 检查是否需要构建
            result = await asyncio.create_subprocess_exec(
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}",
                "--filter",
                "reference=*aiforge*",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if stdout.decode().strip():
                print(self._i18n_manager.t("docker.image_exists_skip_build"))
                return {"success": True, "message": "Images already exist"}

            print(self._i18n_manager.t("docker.start_building"))
            print(self._i18n_manager.t("docker.build_time_notice"))

            # 构建命令
            cmd = ["docker-compose"]
            if dev_mode and Path(self.dev_compose_file).exists():
                cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
            else:
                cmd.extend(["-f", self.compose_file])
            cmd.extend(["build", "--no-cache"])

            # 异步实时显示构建进度
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )

            print(self._i18n_manager.t("docker.build_progress"))
            output_lines = []

            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                if line_str:
                    output_lines.append(line_str)
                    if "Step" in line_str:
                        print(f"🔧 {line_str}")
                    elif "Successfully built" in line_str or "Successfully tagged" in line_str:
                        print(f"✅ {line_str}")
                    elif "ERROR" in line_str or "FAILED" in line_str:
                        print(f"❌ {line_str}")
                    elif any(
                        keyword in line_str
                        for keyword in ["Downloading", "Extracting", "Pull complete"]
                    ):
                        print(f"⬇️ {line_str}")

            await process.wait()

            if process.returncode == 0:
                print(self._i18n_manager.t("docker.build_success"))
                return {
                    "success": True,
                    "message": "Build successful",
                    "output": "\n".join(output_lines),
                }
            else:
                print(self._i18n_manager.t("docker.build_failed"))
                return {
                    "success": False,
                    "message": "Build failed",
                    "output": "\n".join(output_lines),
                }

        except Exception as e:
            print(self._i18n_manager.t("docker.build_exception", error=str(e)))
            return {"success": False, "message": f"Build exception: {str(e)}"}

    async def _start_services(
        self, dev_mode: bool = False, enable_searxng: bool = False, mode: str = "web"
    ) -> Dict[str, Any]:
        """启动Docker服务"""
        print(self._i18n_manager.t("docker.starting_services"))

        try:
            # 先清理可能存在的旧容器
            print(self._i18n_manager.t("docker.cleaning_old_containers"))
            await asyncio.create_subprocess_exec(
                "docker-compose",
                "down",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 构建启动命令
            cmd = ["docker-compose"]
            if dev_mode:
                cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
                print(self._i18n_manager.t("docker.dev_mode_start"))
            else:
                cmd.extend(["-f", self.compose_file])
                print(self._i18n_manager.t("docker.production_mode_start"))

            # 根据mode参数选择profile - 这是关键修改
            if mode == "core":
                cmd.extend(["--profile", "core"])
                print("📦 启动核心CLI模式（无Web界面）")
            elif mode == "web":
                cmd.extend(["--profile", "web"])
                print("🌐 启动Web界面模式")
            # 如果mode不是core或web，则使用默认行为（不指定profile）

            # 添加搜索引擎支持
            if enable_searxng:
                cmd.extend(["--profile", "search"])  # 注意：这里应该是"search"而不是"searxng"
                print(self._i18n_manager.t("docker.searxng_enabled"))
            else:
                print(self._i18n_manager.t("docker.searxng_not_enabled"))

            cmd.extend(["up", "-d"])

            # 异步执行启动命令
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print(self._i18n_manager.t("docker.service_start_success"))

                # 显示服务信息 - 需要传递mode参数
                await self._show_service_urls(enable_searxng, mode)

                # 等待服务稳定
                print(f"\\n{self._i18n_manager.t('docker.waiting_services')}")
                await asyncio.sleep(10)

                # 检查服务健康状态 - 需要传递mode参数
                health_status = await self._check_services_health(enable_searxng, mode)

                # 更新SearXNG配置（仅当启用时）
                if enable_searxng:
                    await self._check_and_update_searxng_formats()

                print(f"\\n{self._i18n_manager.t('docker.startup_complete')}")
                print(self._i18n_manager.t("docker.ready_to_use"))

                return {
                    "success": True,
                    "message": "Services started successfully",
                    "mode": mode,  # 返回使用的模式
                    "health_status": health_status,
                    "output": stdout.decode() if stdout else "",
                }
            else:
                print(self._i18n_manager.t("docker.service_start_failed", error=stderr.decode()))
                return {
                    "success": False,
                    "message": "Service start failed",
                    "error": stderr.decode() if stderr else "",
                }

        except Exception as e:
            print(self._i18n_manager.t("docker.startup_exception", error=str(e)))
            return {"success": False, "message": f"Start exception: {str(e)}"}

    async def _show_service_urls(self, enable_searxng: bool = False, mode: str = "web") -> None:
        """显示服务访问地址"""
        print(f"\\n{self._i18n_manager.t('docker.service_urls')}")

        if mode == "web":
            print(self._i18n_manager.t("docker.aiforge_web_url"))
            print(self._i18n_manager.t("docker.admin_panel_url"))
        elif mode == "core":
            print("📦 CLI模式: docker exec -it aiforge-core aiforge --help")

        if enable_searxng:
            print(self._i18n_manager.t("docker.searxng_url"))

    async def _check_services_health(
        self, enable_searxng: bool = False, mode: str = "web"
    ) -> Dict[str, str]:
        """检查服务健康状态"""
        print(f"\\n{self._i18n_manager.t('docker.health_check')}")

        # 根据mode选择要检查的服务
        services = []
        if mode == "web":
            services = ["aiforge-web"]  # 或者根据实际的服务名称
        elif mode == "core":
            services = ["aiforge-core"]

        if enable_searxng:
            services.extend(["aiforge-searxng", "aiforge-nginx"])

        health_status = {}

        for service in services:
            try:
                cmd = ["docker", "ps", "--filter", f"name={service}", "--format", "{{.Status}}"]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()

                status = stdout.decode().strip()
                if "Up" in status:
                    health_status[service] = "running"
                    print(self._i18n_manager.t("docker.service_running", service=service))
                else:
                    health_status[service] = "stopped"
                    print(
                        self._i18n_manager.t(
                            "docker.service_not_running", service=service, status=status
                        )
                    )

            except Exception:
                health_status[service] = "unknown"
                print(self._i18n_manager.t("docker.service_status_unknown", service=service))

        return health_status

    async def _check_and_update_searxng_formats(self) -> bool:
        """更新SearXNG配置以支持多种输出格式"""
        try:
            import yaml
        except ImportError:
            print(self._i18n_manager.t("docker.pyyaml_not_installed"))
            return False

        # 保持原始路径：根目录下的searxng/settings.yml
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

    # 其他必要的方法实现...
    async def stop(self) -> bool:
        """停止服务"""
        if not Path(self.compose_file).exists():
            print(self._i18n_manager.t("docker.compose_file_not_exists_msg"))
            return False

        print(self._i18n_manager.t("docker.stopping_services"))

        try:
            cmd = ["docker-compose", "-f", self.compose_file, "down"]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.wait()

            if process.returncode == 0:
                print(self._i18n_manager.t("docker.stop_success"))
                return True
            else:
                print(self._i18n_manager.t("docker.stop_failed", error="Process failed"))
                return False
        except Exception as e:
            print(self._i18n_manager.t("docker.stop_failed", error=str(e)))
            return False

    async def cleanup(self) -> bool:
        """清理Docker资源"""
        print(self._i18n_manager.t("docker.cleaning_resources"))

        try:
            # 停止并移除容器
            cmd1 = ["docker-compose", "down", "-v"]
            process1 = await asyncio.create_subprocess_exec(
                *cmd1, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process1.wait()

            cmd2 = ["docker-compose", "--profile", "searxng", "down", "-v", "--remove-orphans"]
            process2 = await asyncio.create_subprocess_exec(
                *cmd2, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process2.wait()

            # 清理相关镜像
            cmd3 = [
                "docker",
                "image",
                "prune",
                "-f",
                "--filter",
                "label=com.docker.compose.project=aiforge",
            ]
            process3 = await asyncio.create_subprocess_exec(
                *cmd3, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process3.wait()

            print(self._i18n_manager.t("docker.cleanup_success"))
            return True
        except Exception as e:
            print(self._i18n_manager.t("docker.cleanup_failed", error=str(e)))
            return False

    async def deep_cleanup(self) -> bool:
        """彻底清理AIForge相关资源，但保留基础镜像"""
        print(self._i18n_manager.t("docker.deep_cleanup_start"))
        print(self._i18n_manager.t("docker.deep_cleanup_warning"))

        try:
            # 1. 停止所有服务
            print(self._i18n_manager.t("docker.stopping_all_services"))
            await asyncio.create_subprocess_exec(
                "docker-compose",
                "down",
                "-v",
                "--remove-orphans",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.create_subprocess_exec(
                "docker-compose",
                "--profile",
                "searxng",
                "down",
                "-v",
                "--remove-orphans",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 2. 只清理AIForge构建的镜像，保留基础镜像
            print(self._i18n_manager.t("docker.cleaning_built_images"))
            await self._remove_aiforge_built_images_only()

            # 3. 清理构建缓存
            print(self._i18n_manager.t("docker.cleaning_build_cache"))
            await asyncio.create_subprocess_exec(
                "docker",
                "builder",
                "prune",
                "-f",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 4. 清理悬空资源
            print(self._i18n_manager.t("docker.cleaning_dangling_resources"))
            await asyncio.create_subprocess_exec(
                "docker",
                "image",
                "prune",
                "-f",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.create_subprocess_exec(
                "docker",
                "volume",
                "prune",
                "-f",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            print(self._i18n_manager.t("docker.deep_cleanup_success"))
            return True

        except Exception as e:
            print(self._i18n_manager.t("docker.deep_cleanup_failed", error=str(e)))
            return False

    async def _remove_aiforge_built_images_only(self):
        """只移除AIForge构建的镜像，保留基础镜像"""
        try:
            result = await asyncio.create_subprocess_exec(
                "docker",
                "images",
                "--format",
                "{{.Repository}}:{{.Tag}}\t{{.ID}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if not stdout or not stdout.decode().strip():
                return

            preserve_images = {"python", "searxng/searxng", "nginx"}
            images_to_remove = []

            for line in stdout.decode().strip().split("\n"):
                if "\t" in line:
                    repo_tag, image_id = line.split("\t", 1)
                    repo = repo_tag.split(":")[0]

                    if any(keyword in repo.lower() for keyword in ["aiforge"]):
                        if not any(base in repo.lower() for base in preserve_images):
                            images_to_remove.append(image_id)

            # 删除镜像
            for image_id in images_to_remove:
                await asyncio.create_subprocess_exec(
                    "docker",
                    "rmi",
                    "-f",
                    image_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            if images_to_remove:
                print(self._i18n_manager.t("docker.removed_images", count=len(images_to_remove)))
            else:
                print(self._i18n_manager.t("docker.no_images_to_remove"))

        except Exception as e:
            print(self._i18n_manager.t("docker.cleanup_images_error", error=str(e)))
