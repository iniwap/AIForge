from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static


class AIForgeGUI(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="请输入指令")
        yield Static("执行结果显示区")
        yield Footer()


def run_gui():
    AIForgeGUI().run()


if __name__ == "__main__":
    run_gui()
