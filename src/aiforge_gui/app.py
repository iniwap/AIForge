import json
from typing import Dict, Any

from textual.widgets import Input, Button
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Header, Footer

from aiforge import AIForgeEngine


class AIForgeGUI(App):
    def __init__(self):
        super().__init__()
        self.forge = AIForgeEngine()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="请输入指令", id="instruction_input")
        yield Button("提交", id="submit")
        yield Static("执行结果显示区", id="result_display")
        yield Footer()

    def display_result(self, ui_result: Dict[str, Any]):
        """在GUI中显示UI适配后的结果"""
        result_widget = self.query_one("#result_display", Static)

        display_items = ui_result.get("display_items", [])
        summary_text = ui_result.get("summary_text", "执行完成")

        # 构建显示内容
        display_content = []

        for item in display_items:
            item_type = item.get("type", "text")
            title = item.get("title", "结果")
            content = item.get("content", "")

            if item_type == "table":
                # 表格显示
                columns = content.get("columns", [])
                rows = content.get("rows", [])

                table_text = f"[bold]{title}[/bold]\n"
                table_text += " | ".join(columns) + "\n"
                table_text += "-" * (len(" | ".join(columns))) + "\n"

                for row in rows:
                    row_data = [str(row.get(col, "")) for col in columns]
                    table_text += " | ".join(row_data) + "\n"

                display_content.append(table_text)

            elif item_type == "card":
                # 卡片显示
                card_text = f"[bold]{title}[/bold]\n"
                card_text += f"主要内容: {content.get('primary', '')}\n"

                for key, value in content.get("secondary", {}).items():
                    card_text += f"{key}: {value}\n"

                display_content.append(card_text)

            else:
                # 默认文本显示
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False, indent=2)

                display_content.append(f"[bold]{title}[/bold]\n{content}")

        # 更新显示内容
        final_content = "\n\n".join(display_content)
        final_content += f"\n\n[green]{summary_text}[/green]"

        result_widget.update(final_content)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "submit":
            # 获取输入
            input_widget = self.query_one("#instruction_input", Input)
            raw_input = {
                "text": input_widget.value,
                "widget_id": "instruction_input",
                "cursor_position": input_widget.cursor_position,
                "input_method": "keyboard",
            }

            # 准备GUI上下文
            context_data = {
                "device_info": {
                    "screen_size": {"width": self.size.width, "height": self.size.height}
                },
                "preferences": {"theme": "default"},
            }

            # 使用输入适配运行
            result = self.forge.run_with_input_adaptation(raw_input, "gui", context_data)

            # 适配输出结果
            ui_result = self.forge.adapt_result_for_ui(result, "web_card", "gui")

            # 显示结果
            self.display_result(ui_result)
