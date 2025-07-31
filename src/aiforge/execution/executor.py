import ast
import importlib
from typing import Dict, Any, List, Set
from rich.console import Console
import traceback


class AIForgeExecutor:
    """AIForge代码执行引擎"""

    MAX_EXECUTE_TIMEOUT = 30  # 代码执行超过30秒失败

    def __init__(self):
        self.history = []
        self.console = Console()

    def _extract_imports_from_code(self, code: str) -> Dict[str, Dict[str, Any]]:
        """提取代码中的所有导入语句"""
        try:
            tree = ast.parse(code)
            imports = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = {
                            "type": "from_import",
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }

            return imports
        except SyntaxError:
            return {}

    def _extract_used_names(self, code: str) -> Set[str]:
        """提取代码中使用的所有名称"""
        try:
            tree = ast.parse(code)
            used_names = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    # 只收集被使用（Load）的名称，不包括被赋值（Store）的
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    # 提取属性访问的根对象
                    current = node
                    while isinstance(current, ast.Attribute):
                        current = current.value
                    if isinstance(current, ast.Name):
                        used_names.add(current.id)

            return used_names
        except SyntaxError:
            return set()

    def _build_smart_execution_environment(self, code: str) -> Dict[str, Any]:
        """智能构建执行环境，优化补全逻辑"""
        exec_globals = {"__builtins__": __builtins__}

        # 第一步：分析用户代码的导入语句和使用的名称
        user_imports = self._extract_imports_from_code(code)
        used_names = self._extract_used_names(code)

        # 第二步：完全按照用户导入语句构建环境
        for name, import_info in user_imports.items():
            try:
                if import_info["type"] == "import":
                    module = importlib.import_module(import_info["module"])
                    exec_globals[name] = module
                elif import_info["type"] == "from_import":
                    module = importlib.import_module(import_info["module"])
                    if import_info["name"] == "*":
                        for attr_name in dir(module):
                            if not attr_name.startswith("_"):
                                exec_globals[attr_name] = getattr(module, attr_name)
                    else:
                        exec_globals[name] = getattr(module, import_info["name"])
            except (ImportError, AttributeError) as e:
                fallback_module = self._smart_import_fallback(name, import_info)
                if fallback_module is not None:
                    exec_globals[name] = fallback_module
                else:
                    print(f"[WARNING] 无法导入模块 {name}: {e}")

        # 第三步：更精确的智能补全，避免不必要的导入
        missing_names = used_names - set(user_imports.keys()) - set(exec_globals.keys())
        for name in missing_names:
            # 更严格的过滤条件
            if (
                name in ["__result__", "result", "data", "output", "response", "content"]
                or name.islower()
                and len(name) <= 3
                or name
                in [
                    "a",
                    "b",
                    "c",
                    "d",
                    "e",
                    "f",
                    "g",
                    "h",
                    "i",
                    "j",
                    "k",
                    "l",
                    "m",
                    "n",
                    "o",
                    "p",
                    "q",
                    "r",
                    "s",
                    "t",
                    "u",
                    "v",
                    "w",
                    "x",
                    "y",
                    "z",
                ]
            ):
                continue

            # 只对明确的模块名进行智能补全
            known_modules = ["requests", "json", "os", "sys", "re", "datetime", "time", "random"]
            if name in known_modules:
                smart_module = self._smart_import_missing(name)
                if smart_module is not None:
                    exec_globals[name] = smart_module
                    print(f"[INFO] 智能补全导入: {name}")

        return exec_globals

    def _smart_import_fallback(self, name: str, import_info: Dict[str, Any]) -> Any:
        """智能导入回退机制"""
        try:
            # 常见模块的智能替代
            fallback_mappings = {
                "feedparser": None,  # 第三方库，无法替代
                "requests": "requests",
                "datetime": "datetime",
                "BeautifulSoup": "bs4.BeautifulSoup",
                "json": "json",
                "os": "os",
                "re": "re",
                "sys": "sys",
                "time": "time",
                "random": "random",
            }

            if name in fallback_mappings:
                fallback_path = fallback_mappings[name]
                if fallback_path is None:
                    return None

                if "." in fallback_path:
                    # 处理嵌套导入，如 bs4.BeautifulSoup
                    module_path, attr_name = fallback_path.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    return getattr(module, attr_name)
                else:
                    return importlib.import_module(fallback_path)

            # 尝试直接导入原模块名
            if import_info["type"] == "import":
                return importlib.import_module(import_info["module"])
            elif import_info["type"] == "from_import":
                module = importlib.import_module(import_info["module"])
                return getattr(module, import_info["name"])

        except Exception:
            return None

    def _smart_import_missing(self, name: str) -> Any:
        """为缺失的名称提供智能导入"""
        try:
            # 常见的模块名映射
            common_modules = {
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
            }

            if name in common_modules:
                module_path = common_modules[name]
                if "." in module_path:
                    # 处理嵌套导入
                    module_name, attr_name = module_path.rsplit(".", 1)
                    module = importlib.import_module(module_name)
                    return getattr(module, attr_name)
                else:
                    return importlib.import_module(module_path)

            # 尝试直接导入
            return importlib.import_module(name)

        except Exception:
            return None

    def _preprocess_code(self, code: str) -> str:
        """智能代码预处理"""
        lines = code.split("\n")
        processed_lines = []

        for line in lines:
            # 标准化制表符
            line = line.expandtabs(4)
            processed_lines.append(line)

        return "\n".join(processed_lines)

    def _extract_result(self, namespace_dict: dict) -> Any:
        """强制验证数组格式的结果提取"""
        if "__result__" not in namespace_dict:
            return {
                "data": [],
                "status": "error",
                "summary": "代码未执行函数并赋值给 __result__ 变量",
                "metadata": {"error": "missing_result_variable"},
            }

        result = namespace_dict["__result__"]

        # 强制验证基本结构
        if not isinstance(result, dict):
            return {
                "data": [],
                "status": "error",
                "summary": "__result__ 必须是字典格式",
                "metadata": {"error": "invalid_result_type"},
            }

        # 强制验证 data 字段
        if "data" not in result:
            return {
                "data": [],
                "status": "error",
                "summary": "__result__ 缺少 data 字段",
                "metadata": {"error": "missing_data_field"},
            }

        # 强制验证 data 是数组
        if not isinstance(result["data"], list):
            return {
                "data": [],
                "status": "error",
                "summary": "data 字段必须是数组格式",
                "metadata": {"error": "data_not_array"},
            }

        # 强制验证数组元素是字典
        for i, item in enumerate(result["data"]):
            if not isinstance(item, dict):
                return {
                    "data": [],
                    "status": "error",
                    "summary": f"data[{i}] 必须是字典格式",
                    "metadata": {"error": "data_item_not_dict"},
                }

        return result

    def execute_python_code(self, code: str) -> Dict[str, Any]:
        """智能执行Python代码，修复多函数定义问题"""
        import platform
        import threading
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("代码执行超时")

        try:
            # 预处理代码
            code = self._preprocess_code(code)

            # 语法检查
            compile(code, "<string>", "exec")

            # 智能构建执行环境
            exec_globals = self._build_smart_execution_environment(code)

            # 不使用分离的exec_locals，直接在exec_globals中执行
            # 这样所有函数定义都在同一个全局命名空间中，可以相互访问

            # 跨平台超时控制
            if platform.system() != "Windows":
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.MAX_EXECUTE_TIMEOUT)

                try:
                    # 直接在exec_globals中执行，不使用exec_locals
                    exec(code, exec_globals, exec_globals)
                finally:
                    signal.alarm(0)
            else:
                # Windows系统的超时处理
                timeout_occurred = threading.Event()
                execution_exception = None

                def timeout_callback():
                    timeout_occurred.set()

                def execute_with_timeout():
                    nonlocal execution_exception
                    try:
                        # 直接在exec_globals中执行
                        exec(code, exec_globals, exec_globals)
                    except Exception as e:
                        execution_exception = e

                timer = threading.Timer(self.MAX_EXECUTE_TIMEOUT, timeout_callback)
                timer.start()

                exec_thread = threading.Thread(target=execute_with_timeout)
                exec_thread.start()
                exec_thread.join(self.MAX_EXECUTE_TIMEOUT + 1)

                timer.cancel()

                if timeout_occurred.is_set():
                    raise TimeoutError("代码执行超时")
                if execution_exception:
                    raise execution_exception

            # 修复：从exec_globals中提取结果
            result = self._extract_result(exec_globals)

            execution_result = {
                "success": True,
                "result": result,
                "code": code,
            }

            # 记录执行历史
            business_success = True
            if isinstance(result, dict) and result.get("status") == "error":
                business_success = False

            self.history.append(
                {
                    "code": code,
                    "result": {"__result__": result},
                    "success": business_success,
                }
            )

            return execution_result

        except TimeoutError:
            return {
                "success": False,
                "error": "代码执行超时（10秒限制）",
                "code": code,
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"语法错误: {str(e)} (行 {e.lineno})",
                "traceback": traceback.format_exc(),
                "code": code,
            }
        except Exception as e:
            error_result = {"success": False, "error": str(e), "code": code}

            self.history.append(
                {"code": code, "result": {"__result__": None, "error": str(e)}, "success": False}
            )

            return error_result

    def extract_code_blocks(self, text: str) -> List[str]:
        """从LLM响应中提取代码块"""
        import re

        # 匹配 ```python...``` 格式
        pattern = r"```python\s*\n(.*?)\n```"
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            # 尝试 ```...``` 格式
            pattern = r"```\s*\n(.*?)\n```"
            matches = re.findall(pattern, text, re.DOTALL)

        # 清理每个代码块
        cleaned_matches = []
        for match in matches:
            cleaned_code = match.strip()
            cleaned_matches.append(cleaned_code)

        return cleaned_matches
