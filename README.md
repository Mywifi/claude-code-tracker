# Claude Tracker

Claude Tracker 是一个为 [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) 设计的透明转发代理。它能够捕获、记录并可视化 Claude Code 与 AI 模型之间的所有交互，帮助开发者更好地调试、审计和分析 AI 的行为。

## ✨ 特性

- **透明代理**：无缝转发请求到目标 AI 平台（支持 Claude, OpenAI 等兼容 API）。
- **实时记录**：自动捕获所有请求体和响应内容，包括流式输出。
- **可视化报告**：内置精美的 HTML 报告界面，支持 Markdown 渲染、思考过程（Thinking Process）展示、工具调用分析。
- **自动刷新**：报告界面实时更新，无需手动刷新页面。
- **SSL 智能适配**：检测到私有 IP 时自动处理 SSL 验证。

## 🚀 快速开始

### 1. 安装

推荐使用 [uv](https://github.com/astral-sh/uv) 进行快速安装和环境管理：

```bash
git clone https://github.com/Mywifi/claude-code-tracker.git
cd claude-code-tracker

# 使用 uv 创建虚拟环境并安装（推荐）
uv venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
uv pip install -e .

# 或者使用标准 pip 安装
pip install -e .
```

### 2. 配置

在项目根目录创建 `.env` 文件：

```env
TARGET_SERVER=https://api.anthropic.com  # 目标 API 地址
PORT=8082                               # 代理服务器监听端口
DATA_DIR=data                           # 数据存储目录
```

### 3. 运行

你可以使用以下任一方式启动项目：

#### A. 使用命令行工具 (推荐)
安装后可直接在终端运行：
```bash
claude-tracker
```

#### B. 开发模式 (支持热重载)
如果你在修改代码并希望自动生效：
```bash
uv run uvicorn claude_code_tracker.proxy:app --host 0.0.0.0 --port 8082 --reload
```

#### C. 使用 Docker
```bash
docker-compose up -d
```

### 4. 在 Claude Code 中使用

设置环境变量让 Claude Code 指向本地代理：

```bash
export ANTHROPIC_BASE_URL=http://localhost:8082
claude
```

### 5. 查看报告

访问 `http://localhost:8082/report` 即可查看捕获到的对话详情，页面会自动刷新。

## 📂 项目结构

```text
src/claude_code_tracker/
├── proxy.py       # 代理服务器核心逻辑
├── reporter.py    # HTML 报告生成器
└── utils.py       # 实用工具函数
data/              # 存放 JSON 数据和 HTML 报告
```

## 🛠️ 开发

```bash
# 运行测试
pytest

# 手动生成报告
claude-reporter
```

## 📄 许可证

MIT License
