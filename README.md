# 🚀 AIForge

[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](./LICENSE) [![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/) [![Build](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/iniwap/aiforge) [![AI Powered](https://img.shields.io/badge/AI-Powered-ff69b4.svg)](#)

> 🧠 **一句话指令，驱动本地 AI 编程执行**  
> 用自然语言生成 Python 脚本，立即本地运行并返回结果。任务即代码，代码即能力。

---

## ✨ 项目简介

**AIForge** 是一个任务驱动的 AI 编程引擎，通过大语言模型（LLM）将自然语言任务描述转化为可执行的 Python 代码，并在本地执行后返回结果。无需手动编程，即可自动完成数据处理、可视化、API 调用等一系列操作。

适用于：
- 📊 数据分析师自动脚本生成
- ⚙️ AI 助手工具链底座
- 🔗 API 工作流编排
- 🧑‍💻 自动化脚本开发与执行

---

## 🧱 核心特性

- ✅ 支持本地或远程大语言模型调用（OpenAI / OpenRouter / Deepseek / Qwen 等）
- ✅ 智能代码生成 + 安全沙箱本地执行
- ✅ 支持上下文缓存、变量复用、内存对话链
- ✅ 可插拔式任务执行器框架
- ✅ 支持 JSON、CSV、Excel 等常用数据操作

---

## 💡 示例用法

```python
from aiforge import run_task

response = run_task("读取本地 data.csv，统计每一列的平均值，并输出成表格")
print(response.result)
```

或使用命令行：

```bash
aiforge "查询百度热搜前10并输出为 Markdown 表格"
```

---

## 📦 安装方式

```bash
pip install aiforge
```

> 依赖 Python 3.8 以上版本，部分功能需要配置 OpenAI 或本地模型 API Key。

---

> 🧱 AIForge — 用一句话构建你的智能工作流。