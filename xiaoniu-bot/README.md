# 小牛VPN Telegram 客服机器人（智能版骨架）

支持两种 AI 路线：
- `openclaw`：推荐，复用本机 OpenClaw Gateway + 已配置的模型/provider（例如 Codex OAuth）
- `openai`：直接走外部 OpenAI 兼容接口

## 1. 安装依赖

```bash
cd xiaoniu-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 配置环境变量

```bash
cp .env.example .env
```

### 推荐：走 OpenClaw

```env
TELEGRAM_BOT_TOKEN=你的机器人Token
HUMAN_CONTACT=@你的人工客服用户名
AI_ENABLED=true
AI_PROVIDER=openclaw
AI_API_BASE=http://127.0.0.1:18789/v1
OPENCLAW_GATEWAY_TOKEN=你的gateway token
AI_MODEL=openclaw:main
AI_TOP_K=3
```

说明：
- `AI_PROVIDER=openclaw` 时，bot 会调用本机 Gateway 的 `/v1/chat/completions`
- 这样能复用你在 OpenClaw 里已经配置好的模型/provider（例如 OpenAI Codex ChatGPT OAuth）
- `OPENCLAW_GATEWAY_TOKEN` 需要填网关 token

### 备用：走外部 OpenAI 兼容接口

```env
AI_ENABLED=true
AI_PROVIDER=openai
AI_API_BASE=https://api.openai.com/v1
AI_API_KEY=你的 key
AI_MODEL=gpt-4o-mini
AI_TOP_K=3
```

## 3. 运行

```bash
python bot.py
```

## 4. 当前逻辑

- FAQ 检索 top K
- AI 根据 FAQ 组织自然回复
- 敏感问题受 FAQ 约束
- AI 失败时自动退回 FAQ 回复
