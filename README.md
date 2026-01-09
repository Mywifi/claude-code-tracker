# Claude Tracker

Claude Tracker 是一个为 [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) 设计的透明转发代理。它能够捕获、记录并可视化 Claude Code 与 AI 模型之间的所有交互，帮助开发者更好地调试、审计和分析 AI 的行为。

## 特性

| 功能 | 描述 |
|------|------|
| 透明代理 | 无缝转发请求到目标 AI 平台（支持 Claude, OpenAI 等兼容 API） |
| 实时记录 | 自动捕获所有请求体和响应内容，包括流式输出 |
| 可视化报告 | 内置精美的 HTML 报告界面，支持 Markdown 渲染、思考过程展示、工具调用分析 |
| 主题切换 | 支持深色/浅色模式，一键切换 |
| 自动刷新 | 报告界面实时更新，无需手动刷新页面 |
| 智能去重 | 相同请求自动去重，避免重复记录 |
| SSL 适配 | 检测到私有 IP 时自动处理 SSL 验证 |

## 截图预览

```
┌─────────────────────┬─────────────────────────────────────────────┐
│  Claude Tracker     │  MODEL: CLAUDE-3-5-SONNET-20241022         │
│                     │  2024-01-09 14:30:22 / USER_ID              │
├─────────────────────┼─────────────────────────────────────────────┤
│  5 RECORDS          │  [Visual Render]  [Raw Analysis]           │
│                     │                                             │
│  ▸ Today            │  System Directives                         │
│    hello world      │  ────────────────────────────              │
│    fix bug in...    │  You are Claude Code...                    │
│    explain regex    │                                             │
│                     │  Interaction Log                           │
│                     │  ────────────────────────────              │
│                     │  USER                                       │
│                     │  How do I parse JSON?                      │
│                     │                                             │
│                     │  ASSISTANT                                 │
│                     │  Here's how to parse JSON...               │
└─────────────────────┴─────────────────────────────────────────────┘
```

## 快速开始

### 安装

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

### 配置

在项目根目录创建 `.env` 文件：

```env
# 必填：目标 API 地址
TARGET_SERVER=https://api.anthropic.com

# 可选：代理服务器监听端口（默认 8082）
PORT=8082

# 可选：数据存储目录（默认 data）
DATA_DIR=data

# 可选：数据文件名（默认 ai_prompts.json）
PROMPTS_FILE=ai_prompts.json

# 可选：是否验证 SSL（默认 true）
VERIFY_SSL=true
```

### 运行

#### 方式一：使用命令行工具（推荐）

```bash
claude-tracker
```

#### 方式二：开发模式（支持热重载）

```bash
uv run uvicorn claude_code_tracker.proxy:app --host 0.0.0.0 --port 8082 --reload
```

#### 方式三：使用 Docker

```bash
docker-compose up -d
```

### 在 Claude Code 中使用

设置环境变量让 Claude Code 指向本地代理：

```bash
export ANTHROPIC_BASE_URL=http://localhost:8082
claude
```

### 查看报告

访问 http://localhost:8082/report 即可查看捕获到的对话详情。

## 使用说明

### 侧边栏导航

- 侧边栏显示所有捕获的对话记录
- 点击任意记录在主内容区查看详情
- 支持深色/浅色主题切换（点击侧边栏右上角图标）

### 报告界面

| 区域 | 说明 |
|------|------|
| System Directives | 查看当前对话的系统提示词 |
| Interaction Log | 完整的对话历史，包括用户输入和 AI 回复 |
| Final Response | AI 的最终回复内容 |
| Tool Definitions | 可用的工具定义（如果有） |
| Contents | 目录导航，点击可快速跳转 |
| Raw Analysis | 原始 JSON 数据查看 |

### 键盘快捷键

| 按键 | 功能 |
|------|------|
| `Esc` | 返回记录列表 |

## 项目结构

```
claude-code-tracker/
├── src/claude_code_tracker/
│   ├── proxy.py       # 代理服务器核心逻辑（请求转发、数据记录）
│   ├── static/        # 前端静态资源
│   │   ├── index.html # 报告页面
│   │   ├── app.js     # 前端逻辑
│   │   └── styles.css # 样式文件
│   └── utils.py       # 实用工具函数
├── data/              # 数据存储目录
│   └── ai_prompts.json # 捕获的对话数据
├── .env               # 配置文件（需创建）
└── README.md          # 本文档
```

## 开发

```bash
# 运行测试
pytest

# 手动运行代理
claude-tracker
```

## 常见问题

**Q: 记录重复怎么办？**
A: 系统会自动去重。5 秒内相同的请求只会记录一次。如需调整，可修改 `DEDUP_WINDOW_SECONDS` 配置。

**Q: 如何导出数据？**
A: 直接复制 `data/ai_prompts.json` 文件，或使用任意 JSON 格式化工具导出。

**Q: 支持哪些 API？**
A: 支持所有兼容 OpenAI API 格式的接口，包括 Anthropic、OpenAI、MiniMax 等。

**Q: 私密数据安全吗？**
A: 所有数据仅保存在本地，不会上传到任何服务器。

## 许可证

MIT License
