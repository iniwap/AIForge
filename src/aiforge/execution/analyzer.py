import ast
from typing import List, Set, Dict, Any


class DataFlowAnalyzer(ast.NodeVisitor):
    """数据流分析器，用于追踪参数的使用链"""

    def __init__(self, function_params: List[str], components: Dict[str, Any] = None):
        self.function_params: Set[str] = set(function_params)
        self.assignments: Dict[str, List[str]] = {}  # 变量赋值关系 {target: source_vars}
        self.usages: Dict[str, List[str]] = {}  # 变量使用情况 {var: [usage_contexts]}
        self.meaningful_uses: Set[str] = set()  # 有意义使用的变量
        self.current_context: str = "unknown"
        self.hardcoded_values = {}
        self.api_calls = []
        self.parameter_conflicts = []
        self._i18n_manager = components.get("i18n_manager")

    def visit_Assign(self, node):
        """处理赋值语句"""
        # 获取赋值目标
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_name = target.id
                # 分析赋值源中使用的变量
                source_vars = self._extract_variables_from_node(node.value)
                self.assignments[target_name] = source_vars

                # 如果赋值源包含参数，标记为有意义使用
                if any(var in self.function_params for var in source_vars):
                    for var in source_vars:
                        if var in self.function_params:
                            self._mark_meaningful_use(var, f"assignment_to_{target_name}")

        self.generic_visit(node)

    def visit_Call(self, node):
        """检测API调用中的硬编码问题和API密钥使用"""
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "requests"
                and node.func.attr in ["get", "post", "put", "delete", "patch", "head", "options"]
            ):
                # 分析URL参数中的硬编码值
                if node.args:
                    url_arg = node.args[0]
                    self._analyze_url_for_hardcoded_values(url_arg)
                    self._analyze_url_for_api_keys(url_arg)

                # 检查headers参数中的认证信息
                self._check_headers_for_auth(node)

                # 检查其他关键字参数中的API密钥
                self._check_params_for_api_keys(node)

        # 检查其他可能的HTTP库调用
        self._check_other_http_libraries(node)

        self.generic_visit(node)

    def _analyze_url_for_api_keys(self, url_node):
        """分析URL中的API密钥参数"""
        if isinstance(url_node, ast.JoinedStr):
            # f-string URL中可能包含API密钥
            for value in url_node.values:
                if isinstance(value, ast.Constant):
                    url_part = str(value.value).lower()
                    if any(
                        pattern in url_part for pattern in ["api_key=", "apikey=", "token=", "key="]
                    ):
                        self.parameter_conflicts.append(
                            {
                                "type": "api_key_in_url",
                                "context": "url_parameter",
                                "message": self._i18n_manager.t(
                                    "analyzer.api_key_in_url_parameter"
                                ),
                            }
                        )
        elif isinstance(url_node, ast.Constant):
            # 常量URL
            url_str = str(url_node.value).lower()
            if any(pattern in url_str for pattern in ["api_key=", "apikey=", "token=", "key="]):
                self.parameter_conflicts.append(
                    {
                        "type": "api_key_in_url",
                        "context": "constant_url",
                        "message": self._i18n_manager.t("analyzer.api_key_in_url_constant"),
                    }
                )

    def _check_headers_for_auth(self, node):
        """检查headers参数中的认证信息"""
        for keyword in node.keywords:
            if keyword.arg == "headers":
                self._analyze_headers_dict(keyword.value)

    def _analyze_headers_dict(self, headers_node):
        """分析headers字典中的认证信息"""
        if isinstance(headers_node, ast.Dict):
            for key, value in zip(headers_node.keys, headers_node.values):
                if isinstance(key, ast.Constant):
                    key_str = str(key.value).lower()
                    if key_str in ["authorization", "x-api-key", "api-key", "auth-token"]:
                        self.parameter_conflicts.append(
                            {
                                "type": "api_key_in_headers",
                                "parameter": key_str,
                                "context": "headers_dict",
                                "message": self._i18n_manager.t(
                                    "analyzer.api_key_in_headers", key=key_str
                                ),
                            }
                        )

    def _check_params_for_api_keys(self, node):
        """检查其他参数中的API密钥"""
        api_key_params = ["api_key", "apikey", "token", "secret", "auth", "key"]

        for keyword in node.keywords:
            if keyword.arg and keyword.arg.lower() in api_key_params:
                self.parameter_conflicts.append(
                    {
                        "type": "api_key_parameter",
                        "parameter": keyword.arg,
                        "context": "function_parameter",
                        "message": self._i18n_manager.t(
                            "analyzer.possible_api_key_parameter", param=keyword.arg
                        ),
                    }
                )

    def _check_other_http_libraries(self, node):
        """检查其他HTTP库的使用"""
        if isinstance(node.func, ast.Attribute):
            # 检查urllib
            if isinstance(node.func.value, ast.Name) and node.func.value.id in [
                "urllib",
                "httpx",
                "aiohttp",
            ]:
                # 对这些库也进行类似的检查
                self._check_params_for_api_keys(node)

            # 检查urllib.request
            elif (
                isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.value.id == "urllib"
                and node.func.value.attr == "request"
            ):
                self._check_params_for_api_keys(node)

    def _analyze_url_for_hardcoded_values(self, url_node):
        """分析URL中的硬编码值"""
        if isinstance(url_node, ast.JoinedStr):
            # f-string URL
            hardcoded_coords = []
            for value in url_node.values:
                if isinstance(value, ast.Constant):
                    # 检测经纬度模式
                    coord_pattern = r"latitude=([0-9.-]+)|longitude=([0-9.-]+)"
                    import re

                    matches = re.findall(coord_pattern, str(value.value))
                    if matches:
                        hardcoded_coords.extend([m for m in matches if m])

            if hardcoded_coords and "location" in self.function_params:
                self.parameter_conflicts.append(
                    {
                        "type": "hardcoded_coordinates",
                        "parameter": "location",
                        "hardcoded_values": hardcoded_coords,
                        "context": "api_url",
                    }
                )

    def has_parameter_conflicts(self) -> bool:
        """检查是否存在参数冲突"""
        return len(self.parameter_conflicts) > 0

    def get_conflict_details(self) -> List[Dict]:
        """获取冲突详情"""
        return self.parameter_conflicts

    def visit_JoinedStr(self, node):
        """处理f-string"""
        self.current_context = "f_string"

        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                used_vars = self._extract_variables_from_node(value.value)
                for var in used_vars:
                    if var in self.function_params:
                        self._mark_meaningful_use(var, "f_string_formatting")
                    elif var in self.assignments:
                        self._trace_variable_usage(var, "f_string_formatting")

        self.generic_visit(node)

    def visit_Compare(self, node):
        """处理比较操作"""
        self.current_context = "comparison"

        # 检查比较操作中的变量使用
        all_nodes = [node.left] + node.comparators
        for comp_node in all_nodes:
            used_vars = self._extract_variables_from_node(comp_node)
            for var in used_vars:
                if var in self.function_params:
                    self._mark_meaningful_use(var, "comparison_operation")
                elif var in self.assignments:
                    self._trace_variable_usage(var, "comparison_operation")

        self.generic_visit(node)

    def visit_Subscript(self, node):
        """处理索引访问"""
        self.current_context = "subscript"

        # 检查被索引的变量和索引值
        used_vars = self._extract_variables_from_node(node.value)
        index_vars = self._extract_variables_from_node(node.slice)

        for var in used_vars + index_vars:
            if var in self.function_params:
                self._mark_meaningful_use(var, "subscript_access")
            elif var in self.assignments:
                self._trace_variable_usage(var, "subscript_access")

        self.generic_visit(node)

    def _extract_variables_from_node(self, node) -> List[str]:
        """从AST节点中提取所有变量名"""
        variables = []

        if isinstance(node, ast.Name):
            variables.append(node.id)
        elif isinstance(node, ast.Attribute):
            variables.extend(self._extract_variables_from_node(node.value))
        elif isinstance(node, ast.Call):
            if hasattr(node, "args"):
                for arg in node.args:
                    variables.extend(self._extract_variables_from_node(arg))
            if hasattr(node, "keywords"):
                for kw in node.keywords:
                    variables.extend(self._extract_variables_from_node(kw.value))
        elif isinstance(node, ast.BinOp):
            variables.extend(self._extract_variables_from_node(node.left))
            variables.extend(self._extract_variables_from_node(node.right))
        elif isinstance(node, ast.Compare):
            variables.extend(self._extract_variables_from_node(node.left))
            for comp in node.comparators:
                variables.extend(self._extract_variables_from_node(comp))
        elif isinstance(node, ast.IfExp):
            variables.extend(self._extract_variables_from_node(node.test))
            variables.extend(self._extract_variables_from_node(node.body))
            variables.extend(self._extract_variables_from_node(node.orelse))
        elif isinstance(node, ast.JoinedStr):
            for value in node.values:
                if isinstance(value, ast.FormattedValue):
                    variables.extend(self._extract_variables_from_node(value.value))
        elif hasattr(node, "__dict__"):
            # 递归处理其他节点类型
            for child in ast.iter_child_nodes(node):
                variables.extend(self._extract_variables_from_node(child))

        return variables

    def _mark_meaningful_use(self, var: str, context: str):
        """标记变量的有意义使用"""
        self.meaningful_uses.add(var)
        if var not in self.usages:
            self.usages[var] = []
        full_context = (
            f"{self.current_context}:{context}" if self.current_context != "unknown" else context
        )
        self.usages[var].append(full_context)

    def _trace_variable_usage(
        self, var: str, context: str, visited: Set[str] = None, depth: int = 0
    ):
        """追踪变量的间接使用"""
        if visited is None:
            visited = set()

        # 防止循环引用和过深递归
        if var in visited or depth > 10:  # 限制递归深度
            return

        visited.add(var)

        if var in self.assignments:
            source_vars = self.assignments[var]
            for source_var in source_vars:
                if source_var in self.function_params:
                    self._mark_meaningful_use(source_var, f"indirect_via_{var}_in_{context}")
                elif source_var in self.assignments and source_var not in visited:
                    # 递归追踪，传递visited集合和深度
                    self._trace_variable_usage(
                        source_var, f"indirect_via_{var}_in_{context}", visited, depth + 1
                    )
