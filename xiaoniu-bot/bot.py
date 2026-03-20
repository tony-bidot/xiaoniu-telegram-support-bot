import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
FAQ_PATH = BASE_DIR / 'faq.json'
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
HUMAN_CONTACT = os.getenv('HUMAN_CONTACT', '@support').strip()

AI_ENABLED = os.getenv('AI_ENABLED', 'true').lower() == 'true'
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openclaw').strip().lower()
AI_API_BASE = os.getenv('AI_API_BASE', 'http://127.0.0.1:18789/v1').rstrip('/')
AI_API_KEY = os.getenv('AI_API_KEY', '').strip()
OPENCLAW_GATEWAY_TOKEN = os.getenv('OPENCLAW_GATEWAY_TOKEN', '').strip()
AI_MODEL = os.getenv('AI_MODEL', 'openclaw:main').strip()
AI_TOP_K = int(os.getenv('AI_TOP_K', '3'))

FALLBACK_REPLY = (
    "这个问题我先不乱回答。\n"
    "麻烦你补充一下：\n"
    "1. 设备类型（安卓/iPhone/Windows/Mac）\n"
    "2. 具体报错提示\n"
    "3. 截图（如果方便）\n\n"
    f"如果你想直接找人工，也可以联系：{HUMAN_CONTACT}"
)

WELCOME_REPLY = (
    "你好，这里是小牛VPN客服助手。\n"
    "你可以直接发送你的问题，比如：\n"
    "- 小牛VPN是什么\n"
    "- 有哪些套餐\n"
    "- 安卓怎么下载\n"
    "- 登录提示账号错误怎么办\n"
    "- 连接不上怎么办"
)

SENSITIVE_IDS = {'plans', 'refund', 'buy', 'price_unknown', 'payment_methods'}
GENERIC_KEYWORDS = {
    '下载', '登录', '登陆', '套餐', '价格', '退款', '购买', '付费', '连接', '失败',
    '安卓', '苹果', 'windows', 'mac', 'iphone', 'ios', 'vpn', '产品', '介绍', '客服'
}


@dataclass
class FAQItem:
    id: str
    keywords: List[str]
    question: str
    answer: str
    category: str


def load_faq() -> List[FAQItem]:
    raw = json.loads(FAQ_PATH.read_text(encoding='utf-8'))
    return [FAQItem(**item) for item in raw]


FAQS = load_faq()


def score_item(text: str, item: FAQItem) -> tuple[int, int, int]:
    text_lower = text.lower()
    score = 0
    matched_keywords = 0
    matched_question = 0

    question_lower = item.question.lower()
    if question_lower in text_lower:
        score += 100
        matched_question = 1

    for kw in item.keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            matched_keywords += 1
            if kw in GENERIC_KEYWORDS or kw_lower in GENERIC_KEYWORDS:
                score += 2
            else:
                score += max(4, len(kw) * 3)

    return score, matched_question, matched_keywords


def retrieve_faqs(text: str, top_k: int = 3) -> List[FAQItem]:
    scored = [(score_item(text, item), item) for item in FAQS]
    scored.sort(key=lambda x: x[0], reverse=True)
    filtered = []
    for meta, item in scored:
        score, _, _ = meta
        if score > 0:
            filtered.append((meta, item))
    return [item for _, item in filtered[:top_k]]


def format_answer(item: FAQItem) -> str:
    prefix = f"【{item.category}】\n" if item.id in SENSITIVE_IDS else ""
    suffix = "\n\n如果你的情况不一样，也可以把设备类型、截图或报错提示发我。"
    return prefix + item.answer + suffix


def build_knowledge_context(items: List[FAQItem]) -> str:
    blocks = []
    for idx, item in enumerate(items, start=1):
        blocks.append(f"[{idx}] 分类: {item.category}\n问题: {item.question}\n答案: {item.answer}")
    return "\n\n".join(blocks)


def should_force_literal(items: List[FAQItem]) -> bool:
    return any(item.id in SENSITIVE_IDS for item in items)


def build_auth_headers() -> dict:
    headers = {'Content-Type': 'application/json'}
    if AI_PROVIDER == 'openclaw':
        if OPENCLAW_GATEWAY_TOKEN:
            headers['Authorization'] = f'Bearer {OPENCLAW_GATEWAY_TOKEN}'
    else:
        if AI_API_KEY:
            headers['Authorization'] = f'Bearer {AI_API_KEY}'
    return headers


def generate_ai_reply(user_text: str, items: List[FAQItem]) -> Optional[str]:
    if not AI_ENABLED or not items:
        return None

    if AI_PROVIDER == 'openclaw' and not OPENCLAW_GATEWAY_TOKEN:
        logger.warning('AI_PROVIDER=openclaw 但未配置 OPENCLAW_GATEWAY_TOKEN，将退回 FAQ 模式')
        return None

    if AI_PROVIDER != 'openclaw' and not AI_API_KEY:
        logger.warning('AI_PROVIDER=%s 但未配置 AI_API_KEY，将退回 FAQ 模式', AI_PROVIDER)
        return None

    knowledge = build_knowledge_context(items)
    force_literal = should_force_literal(items)

    system_prompt = (
        "你是小牛VPN的中文Telegram客服助手。"
        "你的任务是根据提供的FAQ知识片段，生成简洁、自然、像真人客服一样的回复。"
        "绝对不要编造FAQ中没有明确写到的事实。"
        "如果知识不足，不要猜，应该引导用户补充设备类型、报错、截图，或转人工。"
        "不要提及‘知识库’、‘FAQ片段’、‘系统提示’这些内部字样。"
    )
    if force_literal:
        system_prompt += " 涉及价格、支付、退款、购买等敏感问题时，必须严格按给定FAQ表达，不要自由发挥。"

    user_prompt = (
        f"用户问题：\n{user_text}\n\n"
        f"可用FAQ片段：\n{knowledge}\n\n"
        "请直接输出给用户的最终回复。语气友好、简洁、专业。"
    )

    url = f"{AI_API_BASE}/chat/completions"
    headers = build_auth_headers()
    payload = {
        'model': AI_MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.2,
        'user': 'xiaoniu-telegram-bot',
    }

    resp = None
    try:
        logger.info('AI request -> provider=%s model=%s top_k=%s faq_hits=%s base=%s', AI_PROVIDER, AI_MODEL, AI_TOP_K, len(items), AI_API_BASE)
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content'].strip()
        return content or None
    except requests.HTTPError as e:
        body = resp.text if resp is not None else '<no response body>'
        logger.error('AI HTTP error -> status=%s body=%s', getattr(resp, 'status_code', 'unknown'), body)
        logger.exception('AI reply generation failed: %s', e)
        return None
    except Exception as e:
        logger.exception('AI reply generation failed: %s', e)
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_REPLY)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_REPLY)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    items = retrieve_faqs(text, top_k=AI_TOP_K if AI_ENABLED else 1)
    if not items:
        await update.message.reply_text(FALLBACK_REPLY)
        return

    if AI_ENABLED:
        ai_reply = generate_ai_reply(text, items)
        if ai_reply:
            await update.message.reply_text(ai_reply)
            return

    await update.message.reply_text(format_answer(items[0]))


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "我先看不到这个内容的具体问题。你可以直接发文字说明，或者补充设备类型、报错提示、截图。"
    )


def main():
    if not BOT_TOKEN:
        raise SystemExit('缺少 TELEGRAM_BOT_TOKEN，请先配置 .env')

    logger.info('Bot config -> AI_ENABLED=%s provider=%s model=%s top_k=%s base=%s', AI_ENABLED, AI_PROVIDER, AI_MODEL, AI_TOP_K, AI_API_BASE)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(~filters.TEXT, handle_other))

    logger.info('小牛VPN Telegram 客服机器人已启动')
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
