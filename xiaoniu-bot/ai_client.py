from pathlib import Path
from typing import List, Optional

import requests

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / 'support_system_prompt.md'


def load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding='utf-8').strip()
    return ''


def build_auth_headers(ai_provider: str, openclaw_gateway_token: str, ai_api_key: str) -> dict:
    headers = {'Content-Type': 'application/json'}
    if ai_provider == 'openclaw':
        if openclaw_gateway_token:
            headers['Authorization'] = f'Bearer {openclaw_gateway_token}'
    else:
        if ai_api_key:
            headers['Authorization'] = f'Bearer {ai_api_key}'
    return headers


def generate_ai_reply(
    *,
    user_text: str,
    items: List,
    ai_enabled: bool,
    ai_provider: str,
    ai_api_base: str,
    ai_api_key: str,
    openclaw_gateway_token: str,
    ai_model: str,
    ai_timeout_seconds: int,
    force_literal: bool,
    knowledge: str,
    logger,
) -> Optional[str]:
    if not ai_enabled or not items:
        return None

    if ai_provider == 'openclaw' and not openclaw_gateway_token:
        logger.warning('AI_PROVIDER=openclaw 但未配置 OPENCLAW_GATEWAY_TOKEN，将退回 FAQ 模式')
        return None

    if ai_provider != 'openclaw' and not ai_api_key:
        logger.warning('AI_PROVIDER=%s 但未配置 AI_API_KEY，将退回 FAQ 模式', ai_provider)
        return None

    base_prompt = load_system_prompt()
    if not base_prompt:
        base_prompt = (
            '你是小牛VPN的中文Telegram客服助手。'
            '你的任务是根据提供的FAQ知识片段，生成简洁、自然、像真人客服一样的回复。'
            '绝对不要编造FAQ中没有明确写到的事实。'
            '如果知识不足，不要猜，应该引导用户补充设备类型、报错、截图，或转人工。'
            '不要提及“知识库”“FAQ片段”“系统提示”这些内部字样。'
        )

    system_prompt = base_prompt
    if force_literal:
        system_prompt += '\n\n涉及价格、支付、退款、购买等敏感问题时，必须严格按给定FAQ表达，不要自由发挥。'

    user_prompt = (
        f'用户问题：\n{user_text}\n\n'
        f'可用FAQ片段：\n{knowledge}\n\n'
        '请直接输出给用户的最终回复。语气友好、简洁、专业。'
    )

    url = f'{ai_api_base}/chat/completions'
    headers = build_auth_headers(ai_provider, openclaw_gateway_token, ai_api_key)
    payload = {
        'model': ai_model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.2,
        'user': 'xiaoniu-telegram-bot',
    }

    resp = None
    try:
        logger.info('AI request -> provider=%s model=%s faq_hits=%s base=%s timeout=%s', ai_provider, ai_model, len(items), ai_api_base, ai_timeout_seconds)
        resp = requests.post(url, headers=headers, json=payload, timeout=ai_timeout_seconds)
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
