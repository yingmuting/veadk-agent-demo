# VeADK Agent Demo - 聊天机器人

使用火山引擎 VeADK 和 AgentKit 开发的智能聊天机器人。

## 功能特点

- 🤖 智能对话 - 基于 LLM 的自然语言交互
- 💬 友好聊天 - 温暖友善的交流风格
- 🎯 多功能 - 回答问题、提供建议、日常闲聊

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行聊天机器人

```bash
python main.py
```

### 代码示例

```python
import asyncio
from veadk import Runner
from chat_agent.agent import root_agent

async def chat():
    runner = Runner(agent=root_agent)
    response = await runner.run("你好！")
    print(response)

asyncio.run(chat())
```

## 项目结构

```
veadk-agent-demo/
├── chat_agent/
│   ├── __init__.py
│   └── agent.py          # 聊天机器人 Agent 定义
├── main.py               # 运行示例
├── requirements.txt      # 依赖包
└── README.md            # 项目说明
```

## 配置

在使用前，请确保配置好火山引擎的相关凭证。

## 开发

基于 VeADK 框架，你可以：
- 扩展 Agent 的能力
- 添加自定义工具
- 创建更复杂的 Agent 架构

## License

MIT
