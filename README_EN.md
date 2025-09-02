# 🚀 AIForge - Intelligent Intent Adaptive Execution Engine  
  
<div align="center">  
  
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/) [![PyWebView](https://img.shields.io/badge/PyWebView-4.0.0+%20-purple)](https://pywebview.flowrl.com/)
 [![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1+%20-red)](https://fastapi.tiangolo.com/) [![SentenceTransformers](https://img.shields.io/badge/SentenceTransformers-5.0.0+%20-pink)](https://www.SBERT.net/)  
[![PyPI version](https://badge.fury.io/py/aiforge-engine.svg?v=15)](https://badge.fury.io/py/aiforge-engine) [![Downloads](https://pepy.tech/badge/aiforge-engine?v=15)](https://pepy.tech/project/aiforge-engine) [![AI Powered](https://img.shields.io/badge/AI-Powered-ff69b4.svg)](#) [![License](https://img.shields.io/badge/license-Apache%202.0-yellow)](./LICENSE) [![Stars](https://img.shields.io/github/stars/iniwap/AIForge?style=social)](https://github.com/iniwap/AIForge)  
[![Development Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/iniwap/AIForge) [![Development Status](https://img.shields.io/badge/development-active-brightgreen.svg)](https://github.com/iniwap/AIForge)  
  
**Transform natural language instructions into executable code with AI-powered automation**  
  
[🚀 Quick Start](#basic-usage) • [🧠 Core Features](#-core-features) • [⚡ Installation](#installation) • [🌐 Ecosystem](#-connect--support)  
  
</div>  
  
---  
  
## 🎯 What is AIForge?  
> 🚧 **Project Status**: We are currently in full development, with quite frequent version updates. Please stay tuned!  

AIForge is an **intelligent execution engine** that bridges the gap between natural language instructions and code execution. Through advanced instruction analysis and adaptive execution architecture, AIForge provides:  
  
- 🧠 **Deep Understanding** - Multi-dimensional instruction parsing with precise intent capture  
- ⚡ **Instant Execution** - Rapid code generation with real-time environment interaction    
- 🔮 **Smart Caching** - Semantic similarity-based intelligent code reuse  
- 🌊 **Self-Evolution** - Continuous learning optimization with error self-healing  
- 🎭 **Multi-Provider** - OpenAI、DeepSeek、OpenRouter、Ollama   

 ![LOGO](https://raw.githubusercontent.com/iniwap/AIForge/main/logo.jpg)  
   
## ✨ Core Features  
  
### 🏗️ Multi-Interface Architecture  
- **CLI Interface** - Command-line tool for direct execution  
- **Python API** - Programmatic integration for applications  
- **Web API** - FastAPI-based REST interface  
- **Desktop GUI** - Desktop app gui  
  
### 🤖 LLM Provider Support  
- **OpenAI** - GPT models integration  
- **DeepSeek** - Cost-effective AI provider  
- **OpenRouter** - Multi-model access platform  
- **Ollama** - Local model execution  
  
### 🔧 Advanced Execution Management  
- **Docker Deployment** - Supports both deployment methods
- **Template System** - Domain-specific execution templates  
- **Search Integration** - Multi-engine search capabilities (Baidu, Bing, 360, Sogou)  
- **Content Generation** - Specialized content creation workflows  

### 🌍 Multi-Language Support  
- **Global Instruction Processing** - Natural language instruction recognition in 12 major languages  
- **Localized Keywords** - Chinese, English, Arabic, German, Spanish, French, Hindi, Japanese, Korean, Portuguese, Russian, Vietnamese  
- **Smart Language Detection** - Automatic language detection with corresponding keyword library matching  
- **Cross-Language Compatibility** - Maintains English keyword universality while providing localized experience

### 🛡️ Enterprise-Ready Features  
- **Progress Tracking** - Real-time execution status indicators  
- **Error Handling** - Comprehensive exception management and retry logic  
- **Configuration Management** - Flexible TOML-based configuration system  

## 🔐 Enterprise Security Features  
AIForge provides multi-layer security for safe AI code execution:  
  
- **Sandbox Isolation**: Process-level isolation with resource limits  
- **Network Security**: Four-tier policy control with smart domain filtering  
- **Code Analysis**: Dangerous pattern detection and safe module imports    
- **Unified Middleware**: Extensible security validation framework

## 🚀 Quick Start
    
### Installation & Deployment

- Product(Package)
```bash  
pip install aiforge-engine    
  
# With optional dependencies    
pip install "aiforge-engine[all]"  # All features    
pip install "aiforge-engine[gui]"  # Terminal GUI support    
pip install "aiforge-engine[web]"  # Web API support  
pip install "aiforge-engine[deploy]"  # Deploy support    
pip install "aiforge-engine[web,deploy]" # Web + deploy
```  
- Develop（Source Code） 
```bash 
git clone https://github.com/iniwap/AIForge.git  
cd AIForge

uv venv --python 3.10  
source .venv/bin/activate  # macOS/Linux  
# .venv\Scripts\activate  # Windows

uv sync --all-extras
```

### Basic Usage

- Product(Package)
```python
# Direct
from aiforge import AIForgeEngine    
print(AIForgeEngine(api_key="your-openrouter-apikey").("Search for the latest global stock market trends and write an investment analysis"))

# CLI 
aiforge "Search for the latest global stock market trends and write an investment analysis" --api-key sk-or-v1-xxx
  
# Web 
aiforge web --api-key sk-or-v1-xxx  # open http://localhost:8000  

# Web Docker
export OPENROUTER_API_KEY="your-key-here"
aiforge-deploy docker start --searxng

# Desktop GUI
aiforge gui --api-key sk-or-v1-xxx

```  
- Develop（Source Code）
```python
# Direct
from aiforge import AIForgeEngine    
print(AIForgeEngine(api_key="your-openrouter-apikey").("Search for the latest global stock market trends and write an investment analysis"))

# CLI
./aiforge-dev.sh "Search for the latest global stock market trends and write an investment analysis" --api-key sk-or-v1-xxx # win:./aiforge-dev.bat
  
# Web 
./aiforge-dev.sh web --api-key sk-or-v1-xxx  # open http://localhost:8000  

# Web Docker
export OPENROUTER_API_KEY="your-key-here"
./aiforge-dev.sh docker start --searxng --dev

# Desktop GUI
./aiforge-dev.sh gui # --api-key sk-or-v1-xxx --debug

```  
### Command List  
- **AIForge Command Usage Comparison Table**  
  
| Feature | Development Mode | Package Mode | Core Parameters |  
|---------|------------------|--------------|-----------------|  
| **Web Service** | `./aiforge-dev.sh web` | `aiforge web` | `--host 0.0.0.0 --port 8000 --reload --debug --api-key --provider` |  
| **GUI Application** | `./aiforge-dev.sh gui` | `aiforge gui` | `--theme dark --remote-url --width 1200 --height 800 --debug --api-key --provider` |  
| **GUI Remote** | `./aiforge-dev.sh gui --remote URL` | `aiforge gui --remote-url URL` | `--remote-url http://server:port` |  
| **GUI Auto Remote** | `./aiforge-dev.sh gui --auto-remote` | - | `--auto-remote --api-key` (Development mode only) |  
| **Docker Deployment** | `./aiforge-dev.sh deploy docker start` | `aiforge-deploy docker start` | `--dev --searxng --mode web --host --port --deep` |  
| **K8S Deployment** | `./aiforge-dev.sh deploy k8s deploy` | `aiforge-deploy k8s deploy` | `--namespace aiforge --replicas 1` |  
| **AWS Cloud Deploy** | `./aiforge-dev.sh deploy cloud aws deploy` | `aiforge-deploy cloud aws deploy` | `--region us-west-2 --instance-type t3.medium` |  
| **Azure Cloud Deploy** | `./aiforge-dev.sh deploy cloud azure deploy` | `aiforge-deploy cloud azure deploy` | `--region eastus --instance-type` |  
| **GCP Cloud Deploy** | `./aiforge-dev.sh deploy cloud gcp deploy` | `aiforge-deploy cloud gcp deploy` | `--region us-central1-a --instance-type` |  
| **Aliyun Cloud Deploy** | `./aiforge-dev.sh deploy cloud aliyun deploy` | `aiforge-deploy cloud aliyun deploy` | `--region cn-hangzhou --instance-type` |  
| **Direct Execution** | `python -m aiforge.cli.main "instruction"` | `aiforge "instruction"` | `--provider openrouter --config --api-key` |  
| **CLI Mode** | `python -m aiforge.cli.main cli "instruction"` | `aiforge cli "instruction"` | `--provider --config --api-key` |  
  
- **Common Parameters**  
  
| Parameter Category | Parameter | Description | Default Value |  
|-------------------|-----------|-------------|---------------|  
| **Authentication** | `--api-key` | LLM provider API key | Environment variable |  
| **Configuration** | `--provider` | LLM provider (openrouter/deepseek/ollama) | openrouter |  
| **Configuration** | `--config` | Configuration file path | - |  
| **Debug** | `--debug` | Enable debug mode | false |  
| **Debug** | `--verbose, -v` | Verbose output | false |  
  
- **Environment Variable Support**  
  
| Environment Variable | Description | Example |  
|---------------------|-------------|---------|  
| `OPENROUTER_API_KEY` | OpenRouter API key | sk-or-v1-xxx |  
| `DEEPSEEK_API_KEY` | DeepSeek API key | sk-xxx |  
| `AIFORGE_API_KEY` | AIForge universal API key | - |  
| `AIFORGE_LOCALE` | Interface language | zh/en |  
| `AIFORGE_DOCKER_MODE` | Docker mode identifier | true |

### Advanced Configuration  
  
    # Provider-specific configuration  
    forge = AIForgeEngine(  
        api_key="your-deepseek-key",  
        provider="deepseek",  
        locale="en", # ar|de|en|es|fr|hi|ja|ko|pt|ru|vi|zh
        max_rounds=5,
    )  
  
    # Complex task execution  
    result = forge.run(  
        "Build a real-time data monitoring system",  
        system_prompt="You are a senior software architect"  
    )  
  
### Configuration File Setup  
  
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
  
    # Load from configuration file  
    forge = AIForgeEngine(config_file="aiforge.toml")  
  
## 🎭 Use Cases  
  
### 💼 Business Intelligence  
- **Market Analysis** - Real-time data mining and trend prediction  
- **Risk Assessment** - Multi-dimensional risk model construction  
- **Decision Support** - Data-driven intelligent decision engines  
  
### 🔬 Research & Development  
- **Data Science** - Automated experiment design and analysis  
- **Model Training** - Intelligent hyperparameter optimization  
- **Research Assistance** - Data visualization and presentation  
  
### 🛠️ Development Acceleration  
- **Prototype Validation** - Rapid MVP construction  
- **API Integration** - Intelligent interface adaptation  
- **DevOps Automation** - System monitoring and maintenance  
  
### 🎨 Creative Implementation  
- **Content Generation** - Multimedia content intelligent creation  
- **Data Art** - Transform data into visual art  
- **Interactive Design** - Smart UI/UX prototype generation  
  
## 🤝 Development & Contributing  
  
    # Developer setup  
    git clone https://github.com/iniwap/AIForge.git  
    cd AIForge  
    pip install -e ".[dev]"  
  
    # Run tests  
    pytest tests/  
  
## 📞 Connect & Support  
  
- 🌐 **Website**: [aiforge.dev](https://iniwap.github.io/AIForge)  
- 💬 **Community**: [Discord](https://discord.gg/Vp35uSBsrw)  
- 📧 **Contact**: iniwaper@gmail.com  
- 🐦 **Updates**: [@AIForge](https://twitter.com/iafun_tipixel)  
- 📦 **PyPI**: [aiforge-engine](https://pypi.org/project/aiforge-engine/)  
  
---  
  
<div align="center">  
  
**🌟 Redefining the Boundaries of Possibility 🌟**  
  
*AIForge - Where Intelligence Meets Execution*  
  
[Get Started](https://pypi.org/project/aiforge-engine/) | [View Documentation](https://iniwap.github.io/AIForge) | [Join Community](https://discord.gg/Vp35uSBsrw)  
  
</div>