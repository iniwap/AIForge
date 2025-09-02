#!/usr/bin/env python
# -*- coding: utf-8 -*-

import platform
import subprocess
import tempfile
import json
import sys
import os
from typing import Dict, Any
from pathlib import Path
from rich.console import Console
import traceback
from ..security.security_constants import SecurityConstants
from .path_manager import AIForgePathManager


class SecureProcessRunner:
    """安全的进程隔离执行器"""

    def __init__(self, security_config=None, components: Dict[str, Any] = None):
        self.workdir = AIForgePathManager.get_workdir()
        self.temp_dir = AIForgePathManager.get_temp_dir()
        self.console = Console()
        self.security_config = security_config
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")

    def execute_code(self, code: str, globals_dict: Dict | None = None) -> Dict[str, Any]:
        """在隔离进程中执行代码"""
        execution_timeout = self.security_config.get("execution_timeout", 30)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=self.workdir, delete=False, encoding="utf-8"
        ) as f:
            execution_code = self._prepare_execution_code(
                code,
                globals_dict,
                self.security_config.get("memory_limit_mb", 512),
                self.security_config.get("cpu_time_limit", 30),
                self.security_config.get("file_descriptor_limit", 64),
                self.security_config.get("max_file_size_mb", 10),
                self.security_config.get("max_processes", 10),
            )
            f.write(execution_code)
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=execution_timeout + 5,
                cwd=self.workdir,
                env=self._get_restricted_env(),
            )

            return self._parse_execution_result(result)

        except subprocess.TimeoutExpired:
            timeout_error = self._i18n_manager.t(
                "runner.code_execution_timeout", timeout=execution_timeout
            )
            return {
                "success": False,
                "error": timeout_error,
                "result": None,
                "locals": {},
                "globals": {},
            }
        except Exception as e:
            process_error = self._i18n_manager.t("runner.process_execution_error", error=str(e))
            return {
                "success": False,
                "error": process_error,
                "result": None,
                "locals": {},
                "globals": {},
            }
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def _build_policy_config(self, network_config: Dict) -> Dict[str, Any]:
        """构建策略配置"""
        generated_code_config = network_config.get("generated_code", {})
        domain_filtering = network_config.get("domain_filtering", {})

        return {
            "force_block_modules": generated_code_config.get("force_block_modules", False),
            "force_block_access": generated_code_config.get("force_block_access", False),
            "domain_filtering_enabled": domain_filtering.get("enabled", True),
            "domain_whitelist": domain_filtering.get("whitelist", []),
            "domain_blacklist": domain_filtering.get("blacklist", []),
            "max_requests_per_minute": network_config.get("max_requests_per_minute", 60),
            "allowed_protocols": network_config.get("allowed_protocols", ["http", "https"]),
            "allowed_ports": network_config.get("allowed_ports", [80, 443, 8080, 8443]),
            "blocked_ports": network_config.get("blocked_ports", [22, 23, 3389, 5432, 3306]),
        }

    def _get_restricted_env(self) -> Dict[str, str]:
        """获取受限的环境变量 - 使用新的策略架构"""
        from ..security.network_policy import NetworkPolicyFactory

        # 获取网络策略配置
        network_config = self.security_config.get("network", {})
        policy_level = network_config.get("policy", "filtered")

        # 创建网络策略
        policy_config = self._build_policy_config(network_config)
        network_policy = NetworkPolicyFactory.create_policy(
            policy_level, policy_config, self._i18n_manager
        )

        # 基础环境变量
        restricted_env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "HOME": str(self.workdir),
            "TMPDIR": str(self.temp_dir),
        }

        # Windows 特定环境变量
        if platform.system() == "Windows":
            windows_vars = [
                "SYSTEMROOT",
                "WINDIR",
                "COMPUTERNAME",
                "USERNAME",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
                "TEMP",
                "TMP",
            ]
            for var in windows_vars:
                if var in os.environ:
                    restricted_env[var] = os.environ[var]

        # 应用网络策略的环境变量
        network_env = network_policy.get_environment_variables()
        restricted_env.update(network_env)

        return restricted_env

    def _prepare_execution_code(
        self,
        user_code: str,
        globals_dict: Dict | None,
        memory_limit_mb: int,
        cpu_timeout: int,
        file_descriptor_limit: int,
        max_file_size_mb: int,
        max_processes: int,
    ) -> str:
        """准备带完整资源限制的执行代码"""
        # 添加编码声明
        encoding_header = "# -*- coding: utf-8 -*-\n"

        encoded_user_code = repr(user_code)
        custom_globals_code = ""

        network_config = self.security_config.get("network", {})
        policy_level = network_config.get("policy", "filtered")
        generated_code_config = network_config.get("generated_code", {})
        force_block_modules = generated_code_config.get("force_block_modules", False)

        # 保留所有安全常量（包括 DANGEROUS_PATTERNS）
        common_modules = SecurityConstants.COMMON_MODULES
        dangerous_modules = SecurityConstants.DANGEROUS_MODULES
        dangerous_network_modules = SecurityConstants.DANGEROUS_NETWORK_MODULES
        network_modules = SecurityConstants.NETWORK_MODULES
        dangerous_patterns = SecurityConstants.DANGEROUS_PATTERNS

        reason_text = self._i18n_manager.t("runner.network_security_blocked")
        module_blocked_template = self._i18n_manager.t("runner.module_blocked_security_template")
        timeout_message = self._i18n_manager.t("runner.code_execution_timeout_handler")
        security_policy_active = self._i18n_manager.t("runner.security_policy_active")

        # 然后在模板中使用
        blocked_module_template = f"""blocked_modules.append({{
"name": name,
"module": module_name,
"reason": "{reason_text}"
}})"""

        if globals_dict:
            safe_globals = {}
            for key, value in globals_dict.items():
                if isinstance(value, (str, int, float, bool, list, dict, tuple)):
                    safe_globals[key] = value
                elif key in ["__name__", "__file__"]:
                    safe_globals[key] = str(value)

            if safe_globals:
                custom_globals_code = f"custom_globals = {json.dumps(safe_globals, default=str)}\n"

        return f"""{encoding_header}
import json
import sys
import traceback
import os
import signal
import importlib
import ast
import platform

def set_resource_limits():
    try:
        # 只在 Unix/Linux 系统上设置资源限制
        if platform.system() != "Windows":
            import resource
            memory_limit = {memory_limit_mb} * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            resource.setrlimit(resource.RLIMIT_CPU, ({cpu_timeout}, {cpu_timeout}))
            resource.setrlimit(resource.RLIMIT_NOFILE, ({file_descriptor_limit}, {file_descriptor_limit}))
            resource.setrlimit(resource.RLIMIT_NPROC, ({max_processes}, {max_processes}))

            max_file_size = {max_file_size_mb} * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (max_file_size, max_file_size))
    except Exception:
        pass

def smart_import_fallback(name, import_info, dangerous_modules=None):    
    if dangerous_modules is None:    
        dangerous_modules = []    
            
    fallback_mapping = {{    
        'requests': 'urllib.request',    
        'bs4': None,    
        'selenium': None,    
        'feedparser': None,    
    }}  
    
    if name in fallback_mapping:    
        fallback_name = fallback_mapping[name]    
        if fallback_name:    
            # 只在传入危险模块列表时才进行安全检查  
            if dangerous_modules:  
                fallback_base = fallback_name.split('.')[0]    
                if fallback_base in dangerous_modules:    
                    return None    
            try:    
                return importlib.import_module(fallback_name)    
            except ImportError:    
                pass    
    return None

def extract_imports_from_code(code):
    imports = {{}}
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name] = {{
                        "type": "import",
                        "module": alias.name,
                        "name": alias.name
                    }}
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports[alias.asname or alias.name] = {{
                        "type": "from_import",

                        "module": module,
                        "name": alias.name
                    }}
    except:
        pass
    return imports

def extract_used_names(code):
    try:
        tree = ast.parse(code)
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                current = node
                while isinstance(current, ast.Attribute):
                    current = current.value
                if isinstance(current, ast.Name):
                    used_names.add(current.id)

        return used_names
    except SyntaxError:
        return set()

def smart_import_missing(name, dangerous_modules=None):  
    if dangerous_modules is None:  
        dangerous_modules = []  
          
    try:  
        common_modules = {common_modules}  
          
        # 首先检查直接导入是否为危险模块  
        if name in dangerous_modules:  
            return None  
              
        if name in common_modules:  
            module_path = common_modules[name]  
              
            # 提取基础模块名进行检查  
            base_module = module_path.split('.')[0]  
            if base_module in dangerous_modules:  
                return None  
  
            if "." in module_path:  
                module_name, attr_name = module_path.rsplit(".", 1)  
                module = importlib.import_module(module_name)  
                return getattr(module, attr_name)  
            else:  
                return importlib.import_module(module_path)  
          
        # 对于不在常见模块列表中的模块，也要检查是否危险  
        if name in dangerous_modules:  
            return None  
  
        return importlib.import_module(name)  
  
    except Exception:  
        return None

def build_smart_execution_environment(code):  
    import importlib  
    import re  

    safe_builtins = {{  
        'print': print, 'len': len, 'range': range, 'enumerate': enumerate,  
        'str': str, 'int': int, 'float': float, 'bool': bool,  
        'list': list, 'dict': dict, 'tuple': tuple, 'set': set,  
        'abs': abs, 'max': max, 'min': min, 'sum': sum,  
        'sorted': sorted, 'reversed': reversed, 'zip': zip,  
        'map': map, 'filter': filter, 'any': any, 'all': all,  
        'round': round, 'isinstance': isinstance, 'hasattr': hasattr,  
        'getattr': getattr, 'setattr': setattr, 'type': type,  
        '__import__': __import__,  
        'ValueError': ValueError, 'TypeError': TypeError,  
        'KeyError': KeyError, 'IndexError': IndexError,  
        'AttributeError': AttributeError, 'Exception': Exception,  
    }}
  
    exec_globals = {{  
        "__name__": "__main__",  
        "__file__": "generated_code.py",  
        "__builtins__": safe_builtins,  
    }}
    
    # 危险模块黑名单
    dangerous_modules = []
    dangerous_modules.extend({dangerous_modules})
      
    if "{policy_level}" != "unrestricted":  
        dangerous_modules.extend({dangerous_network_modules})  
        
        if {force_block_modules} or "{policy_level}" == "strict":  
            dangerous_modules.extend({network_modules})

    # 首先执行用户代码以定义函数  
    try:  
        # 只执行函数和类定义，避免执行其他代码  
        tree = ast.parse(code)
        function_defs = []
        for node in tree.body:    
            if isinstance(node, (ast.Import, ast.ImportFrom)):    
                # 对 import 语句进行安全检查    
                should_skip = False  
                if isinstance(node, ast.Import):    
                    for alias in node.names:    
                        if alias.name in dangerous_modules:    
                            should_skip = True  
                            break  
                elif isinstance(node, ast.ImportFrom):  
                    if node.module and any(  
                        node.module == dangerous or node.module.startswith(dangerous + '.')  
                        for dangerous in dangerous_modules  
                    ):  
                        should_skip = True
                
                if should_skip:  
                    continue  # 跳过整个危险的 import 节点  
            
            function_defs.append(node)

        if function_defs:
            # 只执行定义部分
            definition_code = ast.Module(body=function_defs, type_ignores=[])
            exec(compile(definition_code, '<string>', 'exec'), exec_globals)
    except Exception:
        pass
    
    user_imports = extract_imports_from_code(code)  

    # 危险函数模式检测（函数级安全控制）      
    has_dangerous_calls = any(re.search(pattern, code, re.IGNORECASE)   
                             for pattern in {dangerous_patterns})
      
    # 动态导入处理
    blocked_modules = []
    for name, import_info in user_imports.items():    
        try:    
            module_name = import_info["module"]    
                
            # 只阻止真正危险的模块    
            is_dangerous = any(dangerous == module_name or module_name.startswith(dangerous + '.') for dangerous in dangerous_modules)  
            if is_dangerous:  
                {blocked_module_template}
                continue    
                
            # 动态导入（允许大部分标准库模块）    
            if import_info["type"] == "import":    
                module = importlib.import_module(module_name)    
                exec_globals[name] = module    
            elif import_info["type"] == "from_import":    
                module = importlib.import_module(module_name)    
                if import_info["name"] == "*":    
                    # 通配符导入    
                    for attr_name in dir(module):    
                        if not attr_name.startswith("_"):    
                            exec_globals[attr_name] = getattr(module, attr_name)    
                else:    
                    exec_globals[name] = getattr(module, import_info["name"])    
                            
        except (ImportError, AttributeError) as e:    
            # 导入失败时使用回退机制    
            fallback_module = smart_import_fallback(name, import_info, dangerous_modules)    
            if fallback_module is not None:    
                exec_globals[name] = fallback_module  
  
    # 处理缺失的名称
    used_names = extract_used_names(code)    
    missing_names = used_names - set(user_imports.keys()) - set(exec_globals.keys())    
        
    for name in missing_names:    
        # 跳过明显的变量名和结果变量    
        if (name in ["__result__", "result", "data", "output", "response", "content"] or    
            name.islower() and len(name) <= 3 or    
            name in ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",    
                    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]):    
            continue    
    
        # 尝试智能导入常见模块    
        smart_module = smart_import_missing(name, dangerous_modules) 

        if smart_module is not None:    
            exec_globals[name] = smart_module
        
    # 清理可能残留的危险模块
    for dangerous in dangerous_modules:  
        exec_globals.pop(dangerous, None)

    return exec_globals, blocked_modules

def timeout_handler(signum, frame):
    raise TimeoutError("{timeout_message}")

try:
    set_resource_limits()

    # 超时处理也需要平台检测
    if platform.system() != "Windows":
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm({cpu_timeout})
    
    user_code_for_analysis = {encoded_user_code} 

    # 使用智能环境构建
    globals_dict ,blocked_modules = build_smart_execution_environment(user_code_for_analysis)

    # 合并自定义globals
    {custom_globals_code}
    if 'custom_globals' in locals():
        globals_dict.update(custom_globals)

    locals_dict = {{}}

    exec(user_code_for_analysis, globals_dict, locals_dict)

    if platform.system() != "Windows":
        signal.alarm(0)

    # 结果提取逻辑
    result = None
    if "__result__" in locals_dict:
        result = locals_dict["__result__"]
    elif "result" in locals_dict:
        result = locals_dict["result"]
    else:
        for key, value in locals_dict.items():
            if not key.startswith("_"):
                result = value
                break

    clean_locals = {{k: v for k, v in locals_dict.items()
                    if not k.startswith('_') and k != '__builtins__'}}
    clean_globals = {{k: v for k, v in globals_dict.items()
                     if k in ['__name__', '__file__'] or not k.startswith('_')}}

    output = {{
        "success": True,
        "result": result,
        "error": None,
        "locals": clean_locals,
        "globals": clean_globals,
    }}
    print("__AIFORGE_RESULT__" + json.dumps(output, default=str))

except Exception as e:
    if platform.system() != "Windows":
        signal.alarm(0)

    error_message = str(e)  
    error_output = {{
        "success": False,
        "result": None,
        "error": error_message,
        "traceback": traceback.format_exc(),
        "locals": {{}},
        "globals": {{}}
    }}

    # 检查是否是因为安全策略导致的模块缺失  
    if "is not defined" in error_message:  
        missing_name = error_message.split("'")[1] if "'" in error_message else ""  
        if missing_name in [blocked['name'] for blocked in blocked_modules]:  
            blocked_info = next((b for b in blocked_modules if b['name'] == missing_name), None)  
            if blocked_info:
                error_message = "{module_blocked_template}".format(  
                    missing_name=missing_name,  
                    reason=blocked_info['reason'],  
                    original_module=blocked_info['module']  
                )  
                error_output = {{  
                    "success": False,  
                    "result": None,  
                    "error": error_message,  
                    "traceback": traceback.format_exc(),
                    "locals": {{}},
                    "globals": {{}},
                    "security_info": {{  
                        "blocked_modules": blocked_modules,  
                        "reason": "{security_policy_active}", 
                    }},
                }}
                
    print("__AIFORGE_RESULT__" + json.dumps(error_output, default=str))

"""  # noqa 501

    def _parse_execution_result(self, result: subprocess.CompletedProcess) -> Dict[str, Any]:
        """解析执行结果"""
        try:
            stdout_content = result.stdout
            if isinstance(stdout_content, bytes):
                stdout_content = stdout_content.decode("utf-8", errors="replace")

            stdout_lines = result.stdout.splitlines()
            for line in stdout_lines:
                if line.startswith("__AIFORGE_RESULT__"):
                    result_json = line.replace("__AIFORGE_RESULT__", "")
                    return json.loads(result_json)

            return {
                "success": result.returncode == 0,
                "result": result.stdout if result.stdout else None,
                "error": result.stderr if result.stderr else None,
                "locals": {},
                "globals": {},
            }

        except Exception as e:
            parse_error_message = self._i18n_manager.t("runner.result_parse_error", error=str(e))
            return {
                "success": False,
                "result": None,
                "error": parse_error_message,
                "locals": {},
                "globals": {},
            }


class AIForgeRunner:
    """AIForge安全任务运行器"""

    def __init__(
        self,
        security_config: dict = {},
        components: Dict[str, Any] = None,
    ):
        self.workdir = AIForgePathManager.get_workdir()
        self.console = Console()
        self.current_task = None
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")
        self.secure_runner = SecureProcessRunner(security_config, self.components)

        self.default_timeout = security_config.get("execution_timeout", 30)
        self.default_memory_limit = security_config.get("memory_limit_mb", 512)
        self.default_cpu_time_limit = security_config.get("cpu_time_limit", 30)
        self.default_file_descriptor_limit = security_config.get("file_descriptor_limit", 64)
        self.default_max_file_size_mb = security_config.get("max_file_size_mb", 10)
        self.default_max_processes = security_config.get("max_processes", 10)

    def execute_code(self, code: str, globals_dict: Dict | None = None) -> Dict[str, Any]:
        """执行生成的代码"""
        sandbox_info = self._i18n_manager.t(
            "runner.sandbox_info",
            timeout=self.default_timeout,
            memory=self.default_memory_limit,
            cpu=self.default_cpu_time_limit,
            fd=self.default_file_descriptor_limit,
            file_size=self.default_max_file_size_mb,
            processes=self.default_max_processes,
        )

        self.console.print(f"[blue]🔐{sandbox_info}[/blue]")

        try:
            result = self.secure_runner.execute_code(code, globals_dict)
            if not result["success"]:
                error_msg = result.get("error", self._i18n_manager.t("runner.unknown_error"))
                if "security_info" in result:
                    security_info = result["security_info"]
                    if security_info.get("blocked_modules"):
                        blocked_list = ", ".join(
                            [
                                f"{m['name']} ({m['module']})"
                                for m in security_info["blocked_modules"]
                            ]
                        )
                        security_blocked_message = self._i18n_manager.t(
                            "runner.security_blocked_modules",
                            blocked_list=blocked_list,
                            error=error_msg,
                        )
                        error_msg = security_blocked_message
                else:
                    execution_failed_message = self._i18n_manager.t(
                        "runner.execution_failed", error=error_msg
                    )
                    self.console.print(f"[red]{execution_failed_message}[/red]")
            else:
                # 检查是否有网络访问被阻止的情况（通过分析结果内容）
                result_content = result.get("result", {})
                if isinstance(result_content, dict):
                    # 检查是否包含网络错误的特征
                    if self._is_network_blocked_result(result_content):
                        network_blocked_message = self._i18n_manager.t(
                            "runner.network_blocked_info"
                        )
                        self.console.print(f"[yellow]ℹ️  {network_blocked_message}[/yellow]")

            return result

        except Exception as e:
            runner_error_message = self._i18n_manager.t("runner.runner_error", error=str(e))
            error_result = {
                "success": False,
                "result": None,
                "error": runner_error_message,
                "traceback": traceback.format_exc(),
                "locals": {},
                "globals": globals_dict or {},
            }
            self.console.print(f"[red]{runner_error_message}[/red]")
            return error_result

    def _is_network_blocked_result(self, result_content: dict) -> bool:
        """检测结果是否表明网络访问被阻止"""
        # 检查常见的网络阻止错误模式
        error_patterns = [
            "ProxyError",
            "Connection refused",
            "积极拒绝",
            "Unable to connect to proxy",
            "127.0.0.1:1",  # 我们设置的代理地址
        ]

        # 递归检查结果中的所有字符串值
        def check_dict_for_patterns(obj):
            if isinstance(obj, dict):
                return any(check_dict_for_patterns(v) for v in obj.values())
            elif isinstance(obj, list):
                return any(check_dict_for_patterns(item) for item in obj)
            elif isinstance(obj, str):
                return any(pattern in obj for pattern in error_patterns)
            return False

        return check_dict_for_patterns(result_content)

    def set_current_task(self, task):
        self.current_task = task

    def get_current_task(self):
        return self.current_task

    def save_code(self, code: str, filename: str = "generated_code.py") -> Path:
        file_path = self.workdir / filename
        AIForgePathManager.safe_write_file(Path(file_path), code, fallback_dir="appropriate_dir")

        return file_path

    def shutdown(self):
        try:
            for file in self.workdir.glob("*.tmp"):
                file.unlink()
        except Exception:
            pass
