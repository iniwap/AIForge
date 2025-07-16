# src/aiforge/cli.py

import argparse
from aiforge.runner import run_task


def main():
    parser = argparse.ArgumentParser(description="AIForge CLI - 用一句话驱动本地 AI 执行")
    parser.add_argument("instruction", type=str, help="任务描述，例如：读取某CSV并统计均值")
    args = parser.parse_args()

    result = run_task(args.instruction)
    print("✅ 执行结果：\n", result)