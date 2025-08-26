import os
import asyncio
from pathlib import Path
from typing import Dict, Any
from ..core.deployment_manager import BaseDeploymentProvider
from aiforge import GlobalI18nManager


class DockerDeploymentProvider(BaseDeploymentProvider):
    """Docker部署提供商"""

    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.deployment_type = "docker"
        self.project_name = "aiforge"

        # 获取i18n管理器
        self._i18n_manager = GlobalI18nManager.get_instance()

        # 获取用户传递的Docker配置（可能为None）
        self.docker_config = config_manager.get_docker_config()

        # 根据用户配置或默认配置设置compose文件路径
        self._setup_compose_file_paths()

    def _get_dockerfile_mode(self) -> str:
        """检测当前使用的 Dockerfile 模式"""
        if self._is_source_environment():
            return "source"
        else:
            return "package"

    def _get_base_env_vars(self) -> tuple[Dict[str, str], Path]:
        """获取基础环境变量 - 考虑文件可写性"""
        env_vars = os.environ.copy()
        env_vars["COMPOSE_PROJECT_NAME"] = self.project_name

        current_file = Path(__file__)
        templates_dir = current_file.parent / "templates"
        work_dir = self._get_docker_working_directory()
        dockerfile_mode = self._get_dockerfile_mode()

        if dockerfile_mode == "source":
            env_vars.update(
                {
                    "AIFORGE_CONFIG_DIR": str(work_dir / "aiforge_config"),
                    "AIFORGE_WORK_DIR": str(work_dir / "aiforge_work"),
                    "AIFORGE_LOGS_DIR": str(work_dir / "logs"),
                    "AIFORGE_SEARXNG_DIR": str(work_dir / "searxng"),
                    "AIFORGE_NGINX_DIR": str(work_dir / "nginx"),
                }
            )
        else:
            env_vars.update(
                {
                    "AIFORGE_CONFIG_DIR": str(work_dir / "config"),
                    "AIFORGE_WORK_DIR": str(work_dir / "work"),
                    "AIFORGE_LOGS_DIR": str(work_dir / "logs"),
                    "AIFORGE_SEARXNG_DIR": str(work_dir / "searxng"),
                    "AIFORGE_NGINX_DIR": str(work_dir / "nginx"),
                }
            )

        # Dockerfile 路径设置
        if dockerfile_mode == "source":
            dockerfile_path = str(templates_dir / "Dockerfile")
        else:
            dockerfile_path = str(templates_dir / "Dockerfile.package")

        env_vars["AIFORGE_DOCKERFILE_PATH"] = dockerfile_path
        return env_vars, templates_dir

    def _get_docker_working_directory(self) -> Path:
        """根据 Dockerfile 模式获取正确的工作目录"""
        dockerfile_mode = self._get_dockerfile_mode()

        if dockerfile_mode == "source":
            # 源码模式：使用项目根目录，所有文件都可写
            current_dir = Path.cwd()
            while current_dir != current_dir.parent:
                if (current_dir / "pyproject.toml").exists():
                    return current_dir
                current_dir = current_dir.parent
            return Path.cwd()
        else:
            # 安装包模式：必须使用用户数据目录，确保文件可写
            data_dir = Path.home() / ".aiforge"
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir

    def _ensure_nginx_config(self, templates_dir: Path) -> str:
        """确保 nginx 配置文件在可写目录中"""
        work_dir = self._get_docker_working_directory()
        nginx_dir = work_dir / "nginx"
        nginx_config_path = nginx_dir / "nginx.conf"

        # 确保目录存在
        nginx_dir.mkdir(parents=True, exist_ok=True)

        # 如果配置文件不存在，从模板复制
        if not nginx_config_path.exists():
            if self._is_source_environment():
                template_path = templates_dir / "nginx" / "nginx.conf"
            else:
                template_path = Path(self._get_template_path("nginx.conf"))

            # 复制模板文件到可写目录
            import shutil

            shutil.copy2(template_path, nginx_config_path)

        return str(nginx_config_path)

    def _ensure_docker_runtime_directories(self) -> bool:
        """确保Docker运行时目录存在"""
        work_dir = self._get_docker_working_directory()

        try:
            # 只创建必要的运行时目录，不管理aiforge.toml
            (work_dir / "aiforge_config").mkdir(exist_ok=True)
            (work_dir / "aiforge_work").mkdir(exist_ok=True)
            (work_dir / "logs").mkdir(exist_ok=True)
            (work_dir / "searxng").mkdir(exist_ok=True)
            (work_dir / "nginx").mkdir(exist_ok=True)

            return True
        except Exception as e:
            print(f"创建Docker运行时目录失败: {e}")
            return False

    def _create_default_searxng_config(self, settings_path: Path) -> None:
        """创建默认的SearXNG配置文件"""
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        default_settings = {
            "search": {"formats": ["html", "json", "csv", "rss"]},
            "server": {
                "secret_key": "change_me_in_production",
                "bind_address": "0.0.0.0",
                "port": 8080,
            },
            "ui": {"default_locale": "en"},
        }

        import yaml

        with open(settings_path, "w", encoding="utf-8") as f:
            yaml.dump(default_settings, f, default_flow_style=False, allow_unicode=True)

    def _setup_compose_file_paths(self):
        """设置compose文件路径"""
        # 检查用户是否传递了自定义的 docker-compose.yml 文件路径
        user_compose_path = self.config_manager.get_user_docker_compose_file_path()

        if user_compose_path:
            # 用户传递了自定义的 docker-compose.yml 文件路径
            if Path(user_compose_path).exists():
                self.compose_file = user_compose_path
            else:
                self.compose_file = self._get_default_compose_file()
        else:
            # 使用默认配置
            self.compose_file = self._get_default_compose_file()

        # dev_compose_file 始终使用默认值（用户不需要自定义）
        self.dev_compose_file = self._get_default_dev_compose_file()

    def _get_default_compose_file(self) -> str:
        """获取默认的compose文件路径"""
        if self._is_source_environment():
            current_file = Path(__file__)
            templates_dir = current_file.parent / "templates"
            return str(templates_dir / "docker-compose.yml")
        else:
            return self._get_template_path("docker-compose.yml")

    def _get_default_dev_compose_file(self) -> str:
        """获取默认的dev compose文件路径"""
        if self._is_source_environment():
            current_file = Path(__file__)
            templates_dir = current_file.parent / "templates"
            return str(templates_dir / "docker-compose.dev.yml")
        else:
            return self._get_template_path("docker-compose.dev.yml")

    def _is_source_environment(self) -> bool:
        """检查是否在源码环境"""
        current_dir = Path.cwd()
        return (
            (current_dir / "src" / "aiforge").exists()
            and (
                current_dir
                / "src"
                / "aiforge_deploy"
                / "docker"
                / "templates"
                / "docker-compose.yml"
            ).exists()
            and (current_dir / "pyproject.toml").exists()
        )

    def _get_template_path(self, filename: str) -> str:
        """获取模板文件路径"""
        try:
            from importlib import resources

            with resources.path("aiforge_deploy.docker.templates", filename) as path:
                return str(path)
        except Exception:
            # 如果无法从包资源获取，回退到当前目录
            return filename

    def get_effective_docker_config(self) -> Dict[str, Any]:
        """获取有效的Docker配置（用户配置 + 默认配置）"""
        if self.docker_config and "compose_content" in self.docker_config:
            # 用户提供了 docker-compose.yml 内容
            return {
                "compose_content": self.docker_config["compose_content"],
                "compose_file": self.compose_file,
                "dev_compose_file": self.dev_compose_file,
            }
        else:
            # 返回默认Docker配置
            return {
                "compose_file": self.compose_file,
                "dev_compose_file": self.dev_compose_file,
                "build_args": {},
                "services": {},
            }

    async def deploy(self, **kwargs) -> Dict[str, Any]:
        """部署Docker服务"""
        dev_mode = kwargs.get("dev_mode", False)
        enable_searxng = kwargs.get("enable_searxng", False)
        mode = kwargs.get("mode", "web")

        print(self._i18n_manager.t("docker.starting_services"))
        print("=" * 50)

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

        if not checks["docker_compose_available"]:
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
            work_dir = self._get_docker_working_directory()
            original_cwd = Path.cwd()

            try:
                os.chdir(work_dir)

                # 设置环境变量
                env_vars, _ = self._get_base_env_vars()

                # 检查是否需要构建
                result = await asyncio.create_subprocess_exec(
                    "docker",
                    "images",
                    "--format",
                    "{{.Repository}}:{{.Tag}}",
                    "--filter",
                    f"label=com.docker.compose.project={self.project_name}",
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
                cmd = ["docker-compose", "-p", self.project_name]
                if dev_mode and Path(self.dev_compose_file).exists():
                    cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
                else:
                    cmd.extend(["-f", self.compose_file])
                cmd.extend(["build", "--no-cache"])

                # 异步实时显示构建进度
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env_vars,
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

            finally:
                # 恢复原始工作目录
                os.chdir(original_cwd)

        except Exception as e:
            print(self._i18n_manager.t("docker.build_exception", error=str(e)))
            return {"success": False, "message": f"Build exception: {str(e)}"}

    async def _start_services(
        self, dev_mode: bool = False, enable_searxng: bool = False, enable_web: bool = True
    ) -> Dict[str, Any]:
        """启动Docker服务"""
        print(self._i18n_manager.t("docker.starting_services"))

        try:
            work_dir = self._get_docker_working_directory()
            original_cwd = Path.cwd()

            try:
                os.chdir(work_dir)

                # 确保运行时目录存在
                if not self._ensure_docker_runtime_directories():
                    return {
                        "success": False,
                        "message": "Failed to prepare Docker runtime directories",
                    }

                # 设置环境变量
                env_vars, templates_dir = self._get_base_env_vars()

                # 设置nginx.conf路径（仅在启用searxng时需要）
                if enable_searxng:
                    nginx_conf_path = self._ensure_nginx_config(templates_dir)
                    env_vars["AIFORGE_NGINX_CONF_PATH"] = nginx_conf_path

                # 先清理可能存在的旧容器
                print(self._i18n_manager.t("docker.cleaning_old_containers"))
                await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "down",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )

                # 构建启动命令
                cmd = ["docker-compose", "-p", self.project_name]
                if dev_mode:
                    cmd.extend(["-f", self.compose_file, "-f", self.dev_compose_file])
                    print(self._i18n_manager.t("docker.dev_mode_start"))
                else:
                    cmd.extend(["-f", self.compose_file])
                    print(self._i18n_manager.t("docker.production_mode_start"))

                # 根据参数选择profile
                if enable_web:
                    cmd.extend(["--profile", "web"])

                if enable_searxng:
                    cmd.extend(["--profile", "search"])
                    print(self._i18n_manager.t("docker.searxng_enabled"))
                else:
                    print(self._i18n_manager.t("docker.searxng_not_enabled"))

                cmd.extend(["up", "-d"])

                # 执行启动命令
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    print(self._i18n_manager.t("docker.service_start_success"))

                    # 显示服务信息
                    await self._show_service_urls(enable_searxng, enable_web)

                    # 等待服务稳定
                    print(f"\n{self._i18n_manager.t('docker.waiting_services')}")
                    await asyncio.sleep(10)

                    # 检查服务健康状态
                    health_status = await self._check_services_health(enable_searxng, enable_web)

                    # 更新SearXNG配置（仅当启用时）
                    if enable_searxng:
                        await self._check_and_update_searxng_formats()

                    print(f"\n{self._i18n_manager.t('docker.startup_complete')}")
                    print(self._i18n_manager.t("docker.ready_to_use"))

                    return {
                        "success": True,
                        "message": "Services started successfully",
                        "mode": enable_web,
                        "health_status": health_status,
                        "output": stdout.decode() if stdout else "",
                    }
                else:
                    print(
                        self._i18n_manager.t("docker.service_start_failed", error=stderr.decode())
                    )
                    return {
                        "success": False,
                        "message": "Service start failed",
                        "error": stderr.decode() if stderr else "",
                    }

            finally:
                # 恢复原始工作目录
                os.chdir(original_cwd)

        except Exception as e:
            print(self._i18n_manager.t("docker.startup_exception", error=str(e)))
            return {"success": False, "message": f"Start exception: {str(e)}"}

    async def _show_service_urls(
        self, enable_searxng: bool = False, enable_web: bool = True
    ) -> None:
        """显示服务访问地址"""
        print(f"\n{self._i18n_manager.t('docker.service_urls')}")

        if enable_web:
            print(self._i18n_manager.t("docker.aiforge_web_url"))
            print(self._i18n_manager.t("docker.admin_panel_url"))

        if enable_searxng:
            print(self._i18n_manager.t("docker.searxng_url"))

    async def _check_services_health(
        self, enable_searxng: bool = False, enable_web: bool = True
    ) -> Dict[str, str]:
        """检查服务健康状态"""
        print(f"\n{self._i18n_manager.t('docker.health_check')}")

        services = ["aiforge-core"]
        if enable_web:
            services.append("aiforge-web")

        if enable_searxng:
            services.extend(["aiforge-searxng", "aiforge-nginx"])

        health_status = {}

        for service in services:
            try:
                # 使用更灵活的容器名称匹配
                cmd = [
                    "docker",
                    "ps",
                    "--filter",
                    f"name=^{service}$",  # 使用精确匹配
                    "--format",
                    "{{.Status}}",
                ]
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

        # 使用正确的工作目录路径
        work_dir = self._get_docker_working_directory()
        settings_file = work_dir / "searxng" / "settings.yml"

        if not settings_file.exists():
            print(self._i18n_manager.t("docker.searxng_config_not_exists"))
            # 创建默认配置
            self._create_default_searxng_config(settings_file)
            return True

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

    async def stop(self) -> bool:
        """停止服务"""
        if not Path(self.compose_file).exists():
            print(self._i18n_manager.t("docker.compose_file_not_exists_msg"))
            return False

        print(self._i18n_manager.t("docker.stopping_services"))

        try:
            work_dir = self._get_docker_working_directory()
            original_cwd = Path.cwd()

            try:
                os.chdir(work_dir)
                env_vars, _ = self._get_base_env_vars()

                cmd = ["docker-compose", "-p", self.project_name, "-f", self.compose_file, "down"]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process.wait()

                if process.returncode == 0:
                    print(self._i18n_manager.t("docker.stop_success"))
                    return True
                else:
                    print(self._i18n_manager.t("docker.stop_failed", error="Process failed"))
                    return False

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            print(self._i18n_manager.t("docker.stop_failed", error=str(e)))
            return False

    async def cleanup(self) -> bool:
        """清理Docker资源"""
        print(self._i18n_manager.t("docker.cleaning_resources"))

        try:
            work_dir = self._get_docker_working_directory()
            original_cwd = Path.cwd()

            try:
                os.chdir(work_dir)
                env_vars, _ = self._get_base_env_vars()

                # 停止并移除容器
                cmd1 = [
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "down",
                    "-v",
                ]
                process1 = await asyncio.create_subprocess_exec(
                    *cmd1,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process1.wait()

                # 清理web profile的服务 - 修正：添加进程等待
                process_web = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "--profile",
                    "web",
                    "down",
                    "-v",
                    "--remove-orphans",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process_web.wait()

                # 清理search profile的服务
                cmd2 = [
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "--profile",
                    "search",
                    "down",
                    "-v",
                    "--remove-orphans",
                ]
                process2 = await asyncio.create_subprocess_exec(
                    *cmd2,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process2.wait()

                # 清理相关镜像
                cmd3 = [
                    "docker",
                    "image",
                    "prune",
                    "-f",
                    "--filter",
                    f"label=com.docker.compose.project={self.project_name}",
                ]
                process3 = await asyncio.create_subprocess_exec(
                    *cmd3, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process3.wait()

                print(self._i18n_manager.t("docker.cleanup_success"))
                return True

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            print(self._i18n_manager.t("docker.cleanup_failed", error=str(e)))
            return False

    async def deep_cleanup(self) -> bool:
        """彻底清理AIForge相关资源，但保留基础镜像"""
        print(self._i18n_manager.t("docker.deep_cleanup_start"))
        print(self._i18n_manager.t("docker.deep_cleanup_warning"))

        try:
            work_dir = self._get_docker_working_directory()
            original_cwd = Path.cwd()

            try:
                os.chdir(work_dir)
                env_vars, _ = self._get_base_env_vars()

                # 1. 停止所有服务 - 修正：添加进程等待
                print(self._i18n_manager.t("docker.stopping_all_services"))
                process_default = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "down",
                    "-v",
                    "--remove-orphans",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process_default.wait()

                process_web = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "--profile",
                    "web",
                    "down",
                    "-v",
                    "--remove-orphans",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process_web.wait()

                process_search = await asyncio.create_subprocess_exec(
                    "docker-compose",
                    "-p",
                    self.project_name,
                    "-f",
                    self.compose_file,
                    "--profile",
                    "search",
                    "down",
                    "-v",
                    "--remove-orphans",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                )
                await process_search.wait()

                # 2. 清理AIForge构建的镜像
                print(self._i18n_manager.t("docker.cleaning_built_images"))
                await self._remove_aiforge_built_images_only()

                # 3. 清理构建缓存
                print(self._i18n_manager.t("docker.cleaning_build_cache"))
                process_builder = await asyncio.create_subprocess_exec(
                    "docker",
                    "builder",
                    "prune",
                    "-f",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process_builder.wait()

                # 4. 清理悬空资源
                print(self._i18n_manager.t("docker.cleaning_dangling_resources"))
                process_image_prune = await asyncio.create_subprocess_exec(
                    "docker",
                    "image",
                    "prune",
                    "-f",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process_image_prune.wait()

                process_volume_prune = await asyncio.create_subprocess_exec(
                    "docker",
                    "volume",
                    "prune",
                    "-f",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process_volume_prune.wait()

                print(self._i18n_manager.t("docker.deep_cleanup_success"))
                return True

            finally:
                # 恢复原始工作目录
                os.chdir(original_cwd)

        except Exception as e:
            print(self._i18n_manager.t("docker.deep_cleanup_failed", error=str(e)))
            return False

    async def _remove_aiforge_built_images_only(self):
        """只移除AIForge构建的镜像，保留基础镜像"""
        try:
            # 查找带有项目标签的镜像
            result = await asyncio.create_subprocess_exec(
                "docker",
                "images",
                "--filter",
                f"label=com.docker.compose.project={self.project_name}",
                "--format",
                "{{.Repository}}:{{.Tag}}\t{{.ID}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if not stdout or not stdout.decode().strip():
                # 如果没有找到带标签的镜像，回退到名称匹配
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
                print(self._i18n_manager.t("docker.no_images_found"))
                return

            preserve_images = {"python", "searxng/searxng", "nginx"}
            images_to_remove = []

            for line in stdout.decode().strip().split("\n"):
                if "\t" in line:
                    repo_tag, image_id = line.split("\t", 1)
                    repo = repo_tag.split(":")[0]

                    # 只删除包含aiforge关键词的镜像，但保留基础镜像
                    if any(keyword in repo.lower() for keyword in ["aiforge"]):
                        if not any(base in repo.lower() for base in preserve_images):
                            images_to_remove.append(image_id)

            # 删除镜像
            for image_id in images_to_remove:
                try:
                    await asyncio.create_subprocess_exec(
                        "docker",
                        "rmi",
                        "-f",
                        image_id,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                except Exception as e:
                    print(f"Failed to remove image {image_id}: {e}")

            if images_to_remove:
                print(self._i18n_manager.t("docker.removed_images", count=len(images_to_remove)))
            else:
                print(self._i18n_manager.t("docker.no_images_to_remove"))

        except Exception as e:
            print(self._i18n_manager.t("docker.cleanup_images_error", error=str(e)))

    async def status(self) -> Dict[str, Any]:
        """获取部署状态"""
        try:
            # 检查服务状态
            services_status = await self._check_services_health(False, True)

            return {
                "success": True,
                "status": (
                    "running"
                    if any(status == "running" for status in services_status.values())
                    else "stopped"
                ),
                "services": services_status,
                "compose_file": self.compose_file,
            }
        except Exception as e:
            return {"success": False, "status": "unknown", "error": str(e)}
