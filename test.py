def get_enhanced_aiforge_prompt(
    user_prompt: Optional[str] = None,
    optimize_tokens: bool = True,
    task_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """生成增强的系统提示，包含输出格式规范和参数化支持"""

    # 基础代码生成规则
    code_rule = """
## 代码生成规则
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获"""

    if optimize_tokens:
        code_rule += "\n- 生成极简代码，无注释，无空行\n- 使用最短变量名(a,b,c,d等)"

    # 统一的格式要求
    format_rules = """
## 🚨 CRITICAL: 输出格式要求 🚨

1. __result__ 必须是字典格式，包含：
   - "data": 实际数据（成功时）或 null（失败时）
   - "status": "success" 或 "error"
   - "summary": 简短描述
   - "metadata": 包含timestamp等信息

2. 严禁使用字符串格式的 __result__
"""

    # 参数化函数生成指导
    param_guidance = ""
    if parameters:
        param_names = list(parameters.keys())
        param_descriptions = []
        for k, v in parameters.items():
            if isinstance(v, dict) and "description" in v:
                param_descriptions.append(
                    f"- {k}: {v['description']} (类型: {v.get('type', 'str')})"
                )
            else:
                param_descriptions.append(f"- {k}: {v}")

        param_guidance = f"""
## 🔧 参数化函数生成
生成可接受参数的函数：
def execute_task({', '.join(param_names)}):
    # 你的代码逻辑
    return result_data

__result__ = execute_task(参数...)

参数说明：
{chr(10).join(param_descriptions)}
"""

        # 添加强制参数化和多种执行模式支持
        execution_guidance = """
## 🔧 执行模式指导
优先生成以下格式之一：

1. 参数化函数（推荐）：
def execute_task(**kwargs):
    # 从kwargs提取参数
    location = kwargs.get('location', '杭州')
    date = kwargs.get('date', 'today')
    # 执行具体逻辑
    return result_data

__result__ = execute_task(参数...)

2. 类方法（复杂逻辑）：
class TaskExecutor:
    def execute_task(self, **kwargs):
        # 执行具体逻辑
        return result_data

__result__ = TaskExecutor().execute_task(参数...)

3. 标准函数（简单任务）：
def main():
    # 执行具体逻辑
    return result_data

__result__ = main()

🚨 关键要求：
- 必须定义函数后立即调用并赋值给 __result__
- __result__ 必须是字典格式，包含 data、status、summary、metadata 字段
- 禁止只定义函数而不调用的代码
"""

    # 构建基础 prompt
    base_prompt = f"""
# 角色定义
你是 AIForge，专业的 Python 代码生成和执行助手。

# 代码生成及执行规范
你的回答必须严格遵循以下要求：

## 代码块格式
- 使用标准 Markdown 代码块格式：```python ... ```
- 将最终执行结果赋值给 __result__ 变量

{code_rule}

{format_rules}

{param_guidance}

{execution_guidance}

"""

    # 任务特定格式（仅在需要时添加）
    if task_type and task_type != "general":
        task_format = get_task_specific_format(task_type)
        base_prompt += f"\n{task_format}"

    # 用户指令处理
    if user_prompt:
        if should_use_detailed_prompt(user_prompt):
            return f"{base_prompt}\n\n# 用户详细指令\n{user_prompt}"
        else:
            return f"{base_prompt}\n\n# 任务要求\n{user_prompt}"
    else:
        return f"{base_prompt}\n\n# 任务要求\n请根据用户指令生成相应的 Python 代码"
