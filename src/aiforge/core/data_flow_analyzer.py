import ast
from typing import List


class DataFlowAnalyzer(ast.NodeVisitor):
    """数据流分析器，用于追踪参数的使用链"""

    def __init__(self, function_params: List[str]):
        self.function_params = set(function_params)
        self.assignments = {}  # 变量赋值关系 {target: source_vars}
        self.usages = {}  # 变量使用情况 {var: [usage_contexts]}
        self.meaningful_uses = set()  # 有意义使用的变量
        self.current_context = "unknown"

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
        """处理函数调用"""
        self.current_context = "function_call"

        # 检查函数调用中的参数使用
        all_args = []
        if hasattr(node, "args"):
            all_args.extend(node.args)
        if hasattr(node, "keywords"):
            all_args.extend([kw.value for kw in node.keywords])

        for arg in all_args:
            used_vars = self._extract_variables_from_node(arg)
            for var in used_vars:
                if var in self.function_params:
                    self._mark_meaningful_use(var, "function_call_argument")
                elif var in self.assignments:
                    # 追踪间接使用
                    self._trace_variable_usage(var, "function_call_argument")

        self.generic_visit(node)

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
        self.usages[var].append(context)

    def _trace_variable_usage(self, var: str, context: str):
        """追踪变量的间接使用"""
        if var in self.assignments:
            source_vars = self.assignments[var]
            for source_var in source_vars:
                if source_var in self.function_params:
                    self._mark_meaningful_use(source_var, f"indirect_via_{var}_in_{context}")
                elif source_var in self.assignments:
                    # 递归追踪
                    self._trace_variable_usage(source_var, f"indirect_via_{var}_in_{context}")
