#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import tempfile
import json
import sys
import os
from typing import Dict, Any
from pathlib import Path
from rich.console import Console
import traceback


class SecureProcessRunner:
    """安全的进程隔离执行器"""

    def __init__(self, workdir: str = "aiforge_work"):
        self.workdir = Path(workdir)
        self.workdir.mkdir(exist_ok=True)
        self.temp_dir = self.workdir / "tmp"
        self.temp_dir.mkdir(exist_ok=True)
        self.console = Console()

    def execute_code(
        self,
        code: str,
        globals_dict: Dict | None = None,
        timeout: int = 30,
        memory_limit_mb: int = 512,
        cpu_time_limit: int = 30,
        file_descriptor_limit: int = 64,
        max_file_size_mb: int = 10,
        max_processes: int = 10,
    ) -> Dict[str, Any]:
        """在隔离进程中执行代码"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir=self.workdir, delete=False, encoding="utf-8"
        ) as f:
            execution_code = self._prepare_execution_code(
                code,
                globals_dict,
                memory_limit_mb,
                cpu_time_limit,
                file_descriptor_limit,
                max_file_size_mb,
                max_processes,
            )
            f.write(execution_code)
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                encoding="utf-8",  # 明确指定编码
                errors="replace",  # 处理编码错误
                timeout=timeout + 5,
                cwd=self.workdir,
                env=self._get_restricted_env(),
            )

            # 添加调试输出
            print(f"DEBUG: 安全执行进程stdout: {result.stdout}")
            print(f"DEBUG: 安全执行进程stderr: {result.stderr}")
            print(f"DEBUG: 安全执行进程返回码: {result.returncode}")

            parsed_result = self._parse_execution_result(result)
            print(f"DEBUG: 解析后的结果: {parsed_result}")

            return parsed_result

            # return self._parse_execution_result(result)

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"代码执行超时 ({timeout}秒)",
                "result": None,
                "locals": {},
                "globals": {},
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"进程执行错误: {str(e)}",
                "result": None,
                "locals": {},
                "globals": {},
            }
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def _get_restricted_env(self) -> Dict[str, str]:
        """获取受限的环境变量"""
        return {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "HOME": str(self.workdir),
            "TMPDIR": str(self.temp_dir),
            # "HTTP_PROXY": "127.0.0.1:9999",  # 阻止网络访问
            # "HTTPS_PROXY": "127.0.0.1:9999",
        }

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

def smart_import_fallback(name, import_info):
    fallback_mapping = {{
        'requests': 'urllib.request',
        'bs4': None,
        'selenium': None,
        'feedparser': None,
    }}

    if name in fallback_mapping:
        fallback_name = fallback_mapping[name]
        if fallback_name:
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

def smart_import_missing(name):
    try:
        common_modules = {{
            "requests": "requests",
            "json": "json",
            "os": "os",
            "re": "re",
            "sys": "sys",
            "time": "time",
            "random": "random",
            "datetime": "datetime",
            "BeautifulSoup": "bs4.BeautifulSoup",
            "pd": "pandas",
            "np": "numpy",
            "plt": "matplotlib.pyplot",
        }}

        if name in common_modules:
            module_path = common_modules[name]
            if "." in module_path:
                module_name, attr_name = module_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                return getattr(module, attr_name)
            else:
                return importlib.import_module(module_path)

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
    
    # 首先执行用户代码以定义函数  
    try:  
        # 只执行函数和类定义，避免执行其他代码  
        tree = ast.parse(code)
        function_defs = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
                function_defs.append(node)

        if function_defs:
            # 只执行定义部分
            definition_code = ast.Module(body=function_defs, type_ignores=[])
            exec(compile(definition_code, '<string>', 'exec'), exec_globals)
    except Exception:
        pass
    
    user_imports = extract_imports_from_code(code)  
      
    # 危险模块黑名单
    dangerous_modules = [
        'subprocess',
        'multiprocessing',
        'ctypes',
        'importlib.util',
        'runpy',
        'code',
        'codeop',  
    ]  
      
    # 危险函数模式检测（函数级安全控制）  
    dangerous_patterns = [  
        r'os\.system\(',  
        r'os\.exec\w*\(',  
        r'os\.spawn\w*\(',  
        r'os\.popen\(',  
        r'subprocess\.',  
        r'eval\(',  
        r'exec\(',  
        r'compile\(',  
        r'__import__\([^)]*["\\']subprocess["\\']',  
        r'getattr\([^)]*["\\']system["\\']',  
    ]
      
    # 检查代码中是否包含危险函数调用  
    has_dangerous_calls = any(re.search(pattern, code, re.IGNORECASE)   
                             for pattern in dangerous_patterns)
      
    # 动态导入处理  
    for name, import_info in user_imports.items():  
        try:  
            module_name = import_info["module"]  
              
            # 只阻止真正危险的模块  
            if any(dangerous in module_name for dangerous in dangerous_modules):  
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
            fallback_module = smart_import_fallback(name, import_info)  
            if fallback_module is not None:  
                exec_globals[name] = fallback_module
  
    # 处理缺失的名称（基于原始AIForge逻辑）  
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
        smart_module = smart_import_missing(name)  
        if smart_module is not None:  
            exec_globals[name] = smart_module  
  
    return exec_globals

def timeout_handler(signum, frame):
    raise TimeoutError("代码执行超时")

try:
    set_resource_limits()

    # 超时处理也需要平台检测
    if platform.system() != "Windows":
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm({cpu_timeout})
    
    user_code_for_analysis = {encoded_user_code} 

    # 使用智能环境构建
    globals_dict = build_smart_execution_environment(user_code_for_analysis)

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
        "globals": clean_globals
    }}
    print("__AIFORGE_RESULT__" + json.dumps(output, default=str))

except Exception as e:
    if platform.system() != "Windows":
        signal.alarm(0)

    error_output = {{
        "success": False,
        "result": None,
        "error": str(e),
        "traceback": traceback.format_exc(),
        "locals": {{}},
        "globals": {{}}
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
            return {
                "success": False,
                "result": None,
                "error": f"结果解析错误: {str(e)}",
                "locals": {},
                "globals": {},
            }


class AIForgeRunner:
    """AIForge安全任务运行器"""

    def __init__(self, workdir: str = "aiforge_work", security_config: dict = {}):
        self.workdir = Path(workdir)
        self.workdir.mkdir(exist_ok=True)
        self.console = Console()
        self.current_task = None
        self.secure_runner = SecureProcessRunner(workdir)

        self.default_timeout = security_config.get("execution_timeout", 30)
        self.default_memory_limit = security_config.get("memory_limit_mb", 512)
        self.default_cpu_time_limit = security_config.get("cpu_time_limit", 30)
        self.default_file_descriptor_limit = security_config.get("file_descriptor_limit", 64)
        self.default_max_file_size_mb = security_config.get("max_file_size_mb", 10)
        self.default_max_processes = security_config.get("max_processes", 10)

    def execute_code(
        self,
        code: str,
        globals_dict: Dict | None = None,
        timeout: int = None,
        memory_limit_mb: int = None,
        cpu_time_limit: int = None,
        file_descriptor_limit: int = None,
        max_file_size_mb: int = None,
        max_processes: int = None,
    ) -> Dict[str, Any]:
        """执行生成的代码"""

        # 使用传入参数或默认值
        timeout = timeout or self.default_timeout
        memory_limit_mb = memory_limit_mb or self.default_memory_limit
        cpu_time_limit = cpu_time_limit or self.default_cpu_time_limit
        file_descriptor_limit = file_descriptor_limit or self.default_file_descriptor_limit
        max_file_size_mb = max_file_size_mb or self.default_max_file_size_mb
        max_processes = max_processes or self.default_max_processes

        self.console.print(
            f"[blue]安全执行: 超时={timeout}s, 内存={memory_limit_mb}MB, CPU={cpu_time_limit}s, "
            f"文件描述符={file_descriptor_limit}, 文件大小={max_file_size_mb}MB, "
            f"进程数={max_processes}[/blue]"
        )
        try:
            result = self.secure_runner.execute_code(
                code,
                globals_dict,
                timeout,
                memory_limit_mb,
                cpu_time_limit,
                file_descriptor_limit,
                max_file_size_mb,
                max_processes,
            )

            if not result["success"]:
                self.console.print(f"[red]执行失败: {result.get('error', 'Unknown error')}[/red]")

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "result": None,
                "error": f"Runner错误: {str(e)}",
                "traceback": traceback.format_exc(),
                "locals": {},
                "globals": globals_dict or {},
            }
            self.console.print(f"[red]Runner错误: {e}[/red]")
            return error_result

    def set_current_task(self, task):
        self.current_task = task

    def get_current_task(self):
        return self.current_task

    def save_code(self, code: str, filename: str = "generated_code.py") -> Path:
        file_path = self.workdir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return file_path

    def cleanup(self):
        try:
            for file in self.workdir.glob("*.tmp"):
                file.unlink()
        except Exception as e:
            self.console.print(f"[yellow]清理警告: {e}[/yellow]")
