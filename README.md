# 🚀 AIForge - 智能意图自适应执行引擎  
  
<div align="center">  
  
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/) [![PyWebView](https://img.shields.io/badge/PyWebView-4.0.0+%20-purple)](https://pywebview.flowrl.com/)
 [![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1+%20-red)](https://fastapi.tiangolo.com/) [![SentenceTransformers](https://img.shields.io/badge/SentenceTransformers-5.0.0+%20-pink)](https://www.SBERT.net/)  
[![PyPI version](https://badge.fury.io/py/aiforge-engine.svg?v=15)](https://badge.fury.io/py/aiforge-engine) [![Downloads](https://pepy.tech/badge/aiforge-engine?v=15)](https://pepy.tech/project/aiforge-engine) [![AI Powered](https://img.shields.io/badge/AI-Powered-ff69b4.svg)](#) [![License](https://img.shields.io/badge/license-Apache%202.0-yellow)](./LICENSE) [![Stars](https://img.shields.io/github/stars/iniwap/AIForge?style=social)](https://github.com/iniwap/AIForge)  
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/iniwap/AIForge) [![Development Status](https://img.shields.io/badge/development-active-brightgreen.svg)](https://github.com/iniwap/AIForge)  
  
**将自然语言指令转化为可执行代码的AI驱动自动化引擎**  
  
[🚀 快速开始](#-快速开始) • [🧠 核心功能](#-核心功能) • [⚡ 联系支持](#-联系与支持) • [🌐 应用场景](#-应用场景)  
  
</div>  
  
---  
  
## 🎯 什么是 AIForge？    
> 🚧 **项目状态**: 目前处于全力开发阶段，版本更新比较频繁，敬请关注。 

AIForge 是一个**智能执行引擎**，它消除了自然语言指令与代码执行之间的壁垒。通过先进的指令分析和自适应执行架构，AIForge 提供：  
  
- 🧠 **深度理解**：多维度指令解析，精准捕获意图  
- ⚡ **即时执行**：快速代码生成，实时环境交互  
- 🌊 **多模式部署**：CLI、Web API、桌面 GUI  
- 🎭 **多 LLM 支持**：OpenAI、DeepSeek、OpenRouter、Ollama 
- 🔮 **智能缓存** - 基于语义相似性的智能代码复用  
- 🌊 **自我进化** - 持续学习优化，错误自愈能力  
 
> **核心哲学**: *Thought → Code → Reality* - 让思维直接驱动现实世界  

![LOGO](https://raw.githubusercontent.com/iniwap/AIForge/main/logo.jpg)  
![PREVIEW](preview.jpg)
## ✨ 核心功能  
  
### 🏗️ 多界面架构  
- **CLI接口** - 直接执行的命令行工具  
- **Python API** - 应用程序的编程集成  
- **Web API** - 基于FastAPI的REST接口  
- **桌面GUI** - 桌面级GUI客户端支持  
  
### 🔧 高级执行管理  
- **语义缓存** - 基于指令相似性的智能代码复用  
- **模板系统** - 领域特定的执行模板  
- **搜索集成** - 多引擎搜索能力（百度、Bing、360、搜狗），支持SearXNG集成
- **内容生成** - 专业的内容创建工作流  

### 🌍 多语言支持  
- **全球化指令处理** - 支持12种主要语言的自然语言指令识别  
- **本地化关键词** - 中文、英文、阿拉伯语、德语、西班牙语、法语、印地语、日语、韩语、葡萄牙语、俄语、越南语  
- **智能语言检测** - 自动识别用户指令语言并匹配相应的关键词库  
- **跨语言兼容** - 保持英文关键词通用性的同时提供本地化体验

### 🛡️ 企业级功能  
- **Docker部署** - 同时支持两种部署方式
- **进度跟踪** - 实时执行状态指示器  
- **错误处理** - 全面的异常管理和重试逻辑  
- **配置管理** - 灵活的TOML配置系统  

## 🔐 企业级安全特性  
AIForge提供多层安全保障，确保AI代码安全执行：  

- **沙盒隔离**：进程级隔离执行，完整资源限制  
- **网络安全**：四级策略控制，智能域名过滤    
- **代码分析**：危险模式检测，安全模块导入  
- **统一中间件**：可扩展的安全验证框架

## 🚀 快速开始
    
### 安装部署

- 生产模式（安装包）    
```bash  
pip install aiforge-engine    
  
# 包含可选依赖    
pip install "aiforge-engine[all]"  # 所有功能（依赖）    
pip install "aiforge-engine[gui]"  # 终端GUI支持    
pip install "aiforge-engine[web]"  # Web API支持    
pip install "aiforge-engine[deploy]" # 部署支持
pip install "aiforge-engine[web,deploy]" # 安装WEB和部署支持
```

- 开发模式（源码模式）  
```bash 
# 下载源码
git clone https://github.com/iniwap/AIForge.git  
cd AIForge

# 创建并激活虚拟环境
uv venv --python 3.10  
source .venv/bin/activate  # macOS/Linux  
# 或 .venv\Scripts\activate  # Windows

# 安装所有开发依赖
uv sync --all-extras

```
### 基础使用 
- 生产模式（安装包）
```python
# 直接模式
from aiforge import AIForgeEngine    
print(AIForgeEngine(api_key="your-openrouter-apikey").("获取全球最新股市趋势并生成投资建议"))

# CLI 模式
aiforge "获取全球最新股市趋势并生成投资建议" --api-key sk-or-v1-xxx
  
# Web 服务
aiforge web # --api-key sk-or-v1-xxx  # 访问 http://localhost:8000  

# Web Docker
export OPENROUTER_API_KEY="your-key-here"
aiforge-deploy docker start --searxng

# 桌面应用
aiforge gui # --api-key sk-or-v1-xxx

```  
- 开发模式（源码模式）
```python
# 直接模式
from aiforge import AIForgeEngine    
print(AIForgeEngine(api_key="your-openrouter-apikey").("获取全球最新股市趋势并生成投资建议"))

# CLI 模式
./aiforge-dev.sh "获取全球最新股市趋势并生成投资建议" --api-key sk-or-v1-xxx # win : ./aiforge-dev.bat
  
# Web 服务
./aiforge-dev.sh web  # 访问 http://localhost:8000，填写API KEY

# Web Docker
export OPENROUTER_API_KEY="your-key-here" # 也可以不带，打开web页面后配置
./aiforge-dev.sh docker start --searxng --dev

# 桌面应用
./aiforge-dev.sh gui # 填写API KEY，也可以带参数启动 --api-key sk-or-v1-xxx

# 桌面应用一体化启动，GUI本地连接后端WEB服务器模式
./aiforge-dev.bat gui --auto-remote

```  

### 命令列表
- **AIForge 命令使用对比表**  
  
| 功能 | 开发模式（源码） | 生产模式（安装包） | 核心参数 |  
|------|----------|------------|--------------|  
| **Web服务** | `./aiforge-dev.sh web` | `aiforge web` | `--host 0.0.0.0 --port 8000 --reload --debug --api-key --provider` |  
| **GUI应用** | `./aiforge-dev.sh gui` | `aiforge gui` | `--theme dark --remote-url --width 1200 --height 800 --debug --api-key --provider` |  
| **GUI远程** | `./aiforge-dev.sh gui --remote URL` | `aiforge gui --remote-url URL` | `--remote-url http://server:port` |  
| **GUI自动远程** | `./aiforge-dev.sh gui --auto-remote` | - | `--auto-remote --api-key` (仅开发模式) |  
| **Docker部署** | `./aiforge-dev.sh deploy docker start` | `aiforge-deploy docker start` | `--dev --searxng --mode web --host --port --deep` |  
| **K8S部署** | `./aiforge-dev.sh deploy k8s deploy` | `aiforge-deploy k8s deploy` | `--namespace aiforge --replicas 1` |  
| **云部署AWS** | `./aiforge-dev.sh deploy cloud aws deploy` | `aiforge-deploy cloud aws deploy` | `--region us-west-2 --instance-type t3.medium` |  
| **云部署Azure** | `./aiforge-dev.sh deploy cloud azure deploy` | `aiforge-deploy cloud azure deploy` | `--region eastus --instance-type` |  
| **云部署GCP** | `./aiforge-dev.sh deploy cloud gcp deploy` | `aiforge-deploy cloud gcp deploy` | `--region us-central1-a --instance-type` |  
| **云部署阿里云** | `./aiforge-dev.sh deploy cloud aliyun deploy` | `aiforge-deploy cloud aliyun deploy` | `--region cn-hangzhou --instance-type` |  
| **直接执行** | `python -m aiforge.cli.main "指令内容"` | `aiforge "指令内容"` | `--provider openrouter --config --api-key` |  
| **CLI模式** |`python -m aiforge.cli.main cli "指令内容"` | `aiforge cli "指令内容"` | `--provider --config --api-key` |  
  
- **通用参数说明** 
  
| 参数类别 | 参数 | 说明 | 默认值 |  
|----------|------|------|--------|  
| **认证** | `--api-key` | LLM 提供商 API 密钥 | 环境变量 |  
| **配置** | `--provider` | LLM 提供商 (openrouter/deepseek/ollama) | openrouter |  
| **配置** | `--config` | 配置文件路径 | - |  
| **调试** | `--debug` | 启用调试模式 | false |  
| **调试** | `--verbose, -v` | 详细输出 | false |  
  
- **环境变量支持**  
  
| 环境变量 | 说明 | 示例 |  
|----------|------|------|  
| `OPENROUTER_API_KEY` | OpenRouter API 密钥 | sk-or-v1-xxx |  
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | sk-xxx |  
| `AIFORGE_API_KEY` | AIForge 通用 API 密钥 | - |  
| `AIFORGE_LOCALE` | 界面语言 | zh/en |  
| `AIFORGE_DOCKER_MODE` | Docker 模式标识 | true |

### 高级使用 

- 高级参数传递
```python
# 提供商特定配置  
forge = AIForgeEngine(  
    api_key="your-deepseek-key",  
    provider="deepseek",
    locale="en", # ar|de|en|es|fr|hi|ja|ko|pt|ru|vi|zh
    max_rounds=5,
)  

# 复杂任务执行  
result = forge.run(  
    "构建实时数据监控系统",  
    system_prompt="你是一位高级软件架构师"  
)  
```
  
### 配置文件设置  
  
    # aiforge.toml  
    max_tokens = 4096  
    max_rounds = 5  
    default_llm_provider = "openrouter"  
  
    [llm.openrouter]  
    type = "openai"  
    model = "deepseek/deepseek-chat-v3-0324:free"  
    api_key = "your-key"  
    base_url = "https://openrouter.ai/api/v1"  
    timeout = 30  
    max_tokens = 8192  
  
    # 从配置文件加载  
    forge = AIForgeEngine(config_file="aiforge.toml")  
  
## 🎭 应用场景  
  
### 💼 商业智能  
- **市场分析** - 实时数据挖掘与趋势预测  
- **风险评估** - 多维度风险模型构建  
- **决策支持** - 数据驱动的智能决策引擎  
  
### 🔬 研究与开发  
- **数据科学** - 自动化实验设计与分析  
- **模型训练** - 智能超参数优化  
- **研究辅助** - 数据可视化与展示  
  
### 🛠️ 开发加速  
- **原型验证** - 快速MVP构建  
- **API集成** - 智能接口适配  
- **DevOps自动化** - 系统监控与维护  
  
### 🎨 创意实现  
- **内容生成** - 多媒体内容智能创作  
- **数据艺术** - 将数据转化为视觉艺术  
- **交互设计** - 智能UI/UX原型生成  
  
## 🌟 为什么选择 AIForge？  
  
| 特性 | 传统解决方案 | AIForge |  
|------|-------------|---------|  
| 学习曲线 | 数周到数月 | 几分钟上手 |  
| 开发效率 | 线性增长 | 指数级提升 |  
| 错误处理 | 手动调试 | 自动错误恢复 |  
| 可扩展性 | 有限 | 无限可能 |  
| 智能程度 | 静态规则 | 动态学习 |  
  
## 🔮 技术前瞻  
  
AIForge 不仅是工具，更是通往**认知计算时代**的桥梁：  
  
- 🧠 **神经符号融合** - 结合符号推理与神经网络  
- 🌊 **流式思维** - 实时思维流的捕获与执行  
- 🎯 **意图预测** - 基于上下文的需求预判  
- 🔄 **自我进化** - 持续学习的智能体系统  

## 🤝 开发与贡献  
  
    # 开发者设置  
    git clone https://github.com/iniwap/AIForge.git  
    cd AIForge  
    pip install -e ".[dev]"  
  
    # 运行测试  
    pytest tests/  
  
## 📞 联系与支持  
  
- 🌐 **官网**: [aiforge.dev](https://iniwap.github.io/AIForge)  
- 💬 **社区**: [Discord](https://discord.gg/Vp35uSBsrw)  
- 📧 **联系**: iniwaper@gmail.com  
- 🐦 **动态**: [@AIForge](https://twitter.com/iafun_tipixel)  
- 📦 **PyPI**: [aiforge-engine](https://pypi.org/project/aiforge-engine/)  
  
---  
  
<div align="center">  
  
**🌟 重新定义可能性的边界 🌟**  
  
*AIForge - 智能与执行的完美结合*  
  
[立即开始](https://pypi.org/project/aiforge-engine/) | [查看文档](https://iniwap.github.io/AIForge) | [加入社区](https://discord.gg/Vp35uSBsrw)  
  [English](README_EN.md) | [中文](README.md)

</div>