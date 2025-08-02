import os
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import json
from typing import Dict, Any

from aiforge import AIForgeEngine


def display_terminal_result(ui_result: Dict[str, Any]):
    """在终端显示UI适配后的结果"""
    console = Console()

    display_items = ui_result.get("display_items", [])
    summary_text = ui_result.get("summary_text", "执行完成")

    for item in display_items:
        item_type = item.get("type", "text")
        title = item.get("title", "结果")
        content = item.get("content", "")

        if item_type == "table":
            # 显示表格
            table = Table(title=title)
            columns = content.get("columns", [])
            rows = content.get("rows", [])

            for col in columns:
                table.add_column(col)

            for row in rows:
                table.add_row(*[str(row.get(col, "")) for col in columns])

            console.print(table)

        elif item_type == "card":
            # 显示卡片
            card_content = f"主要内容: {content.get('primary', '')}\n"
            for key, value in content.get("secondary", {}).items():
                card_content += f"{key}: {value}\n"

            panel = Panel(card_content, title=title)
            console.print(panel)

        else:
            # 默认文本显示
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False, indent=2)

            panel = Panel(str(content), title=title)
            console.print(panel)

    # 显示摘要
    console.print(f"\n[green]{summary_text}[/green]")


@click.command()
@click.argument("instruction", required=False)
@click.option("--config", help="配置文件路径")
@click.option("--api-key", help="API密钥")
def main(instruction, config, api_key):
    """AIForge CLI工具"""
    # 初始化核心
    forge = AIForgeEngine(config_file=config, api_key=api_key)

    if not instruction:
        instruction = click.prompt("请输入指令")

    # 准备CLI上下文
    context_data = {
        "device_info": {
            "terminal_width": click.get_terminal_size().columns,
            "supports_color": True,
            "shell": os.environ.get("SHELL", "bash"),
        }
    }

    # 使用输入适配运行
    result = forge.run_with_input_adaptation(instruction, "cli", context_data)

    # 适配输出结果
    ui_result = forge.adapt_result_for_ui(result, "terminal_text", "cli")

    # 显示结果
    display_terminal_result(ui_result)
