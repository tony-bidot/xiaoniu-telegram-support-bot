import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from ai_client import generate_ai_reply
from context_store import clear_user_context, get_user_context, is_context_expired, is_duplicate_message, set_user_context
from facts_loader import format_recommended_regions
from handlers.downloads import handle_android_download, handle_ios_download, handle_mac_download, handle_windows_download
from handlers.editions import handle_editions_difference
from handlers.recommendations import (
    handle_ai_node_issue,
    handle_ai_platform_support,
    handle_recommended_nodes,
    handle_streaming_issue,
    handle_streaming_support,
)
from handlers.troubleshooting import handle_android_wifi_connecting_issue, handle_disconnect_issue, handle_speed_issue
from handlers.vip import handle_become_vip, handle_multi_device, handle_plan_query, handle_vip_benefits, handle_vip_vs_free
from intent_router import (
    detect_node_name,
    is_ai_node_issue,
    is_ai_platform_support,
    is_greeting,
    is_ios_download_query,
    is_multi_device_query,
    is_plan_query,
    is_editions_query,
    is_platform_support_query,
    is_vip_query,
    is_recommended_nodes_query,
    is_streaming_issue,
    is_streaming_support,
    is_vague_help,
    looks_like_context_followup,
)
from reply_templates import (
    GREETING_REPLY,
    WELCOME_REPLY,
    build_fallback_reply,
    build_vague_help_reply,
    make_support_style_reply,
)

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
AI_TIMEOUT_SECONDS = int(os.getenv('AI_TIMEOUT_SECONDS', '120'))

FALLBACK_REPLY = build_fallback_reply(HUMAN_CONTACT)

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
    handler: Optional[str] = None


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

    selected = [item for _, item in filtered[:top_k]]
    selected_ids = {item.id for item in selected}
    text_lower = text.lower()

    def add_by_id(item_id: str):
        for faq in FAQS:
            if faq.id == item_id and faq.id not in selected_ids:
                selected.append(faq)
                selected_ids.add(faq.id)
                return

    # Device-intent enrichment: if the user asks whether a platform is supported,
    # also include the relevant download/install FAQ so the reply can carry the link.
    if any(k in text_lower for k in ['mac', 'macbook', '苹果电脑']):
        add_by_id('supported_devices')
        add_by_id('mac_download')
        if any(k in text_lower for k in ['上不了网', '打不开网页', '没网']):
            add_by_id('mac_no_internet_after_connect')
            selected = [faq for faq in selected if faq.id != 'mac_no_internet_after_connect']
            selected.insert(0, next(faq for faq in FAQS if faq.id == 'mac_no_internet_after_connect'))
            selected_ids = {item.id for item in selected}
        elif any(k in text_lower for k in ['支持mac吗', 'mac能用吗', 'mac可以用吗', '支持 mac', 'mac 下载', 'mac怎么下载']):
            selected = [faq for faq in selected if faq.id != 'mac_download']
            selected.insert(0, next(faq for faq in FAQS if faq.id == 'mac_download'))
            selected_ids = {item.id for item in selected}
    if any(k in text_lower for k in ['windows', 'win', 'pc', '电脑']):
        add_by_id('supported_devices')
        add_by_id('windows_download')
        if any(k in text_lower for k in ['上不了网', '打不开网页', '没网']):
            add_by_id('windows_no_internet_after_connect')
            selected = [faq for faq in selected if faq.id != 'windows_no_internet_after_connect']
            selected.insert(0, next(faq for faq in FAQS if faq.id == 'windows_no_internet_after_connect'))
            selected_ids = {item.id for item in selected}
        elif any(k in text_lower for k in ['windows可以用吗', 'windows能用吗', '支持windows', '支持 windows', 'windows 下载', 'windows怎么下载']):
            selected = [faq for faq in selected if faq.id != 'windows_download']
            selected.insert(0, next(faq for faq in FAQS if faq.id == 'windows_download'))
            selected_ids = {item.id for item in selected}
    if any(k in text_lower for k in ['安卓', 'android']):
        add_by_id('supported_devices')
        add_by_id('android_download')
        add_by_id('stuck_connecting_android_wifi')
    if any(k in text_lower for k in ['iphone', 'ios', 'ipad', '苹果手机']):
        add_by_id('supported_devices')
        add_by_id('ios_download')

    if any(k in text_lower for k in ['掉线', '断开', '老断线', '自动断开', '用着用着会断开', '过一段时间就断开', '会自己断开', '不太稳定']):
        add_by_id('disconnect_issue')
        add_by_id('speed_issue')
        # boost disconnect_issue to the front
        selected = [faq for faq in selected if faq.id != 'disconnect_issue']
        selected.insert(0, next(faq for faq in FAQS if faq.id == 'disconnect_issue'))
        selected_ids = {item.id for item in selected}
    if any(k in text_lower for k in ['连上节点上不了网', '连上后上不了网', '连上后没网', '节点连上了但打不开网页', '打不开网页', '上不了网']):
        add_by_id('windows_no_internet_after_connect')
        add_by_id('mac_no_internet_after_connect')
    if any(k in text_lower for k in ['奈非', '奈飞', 'netflix', '看不了奈非', '看不了奈飞', '流媒体']):
        add_by_id('streaming_issue')
        add_by_id('streaming_support')
    if any(k in text_lower for k in ['线路是不是有更新', '线路更新', '线路是不是调整了', '节点维护', '线路维护']):
        add_by_id('line_update_issue')
    if any(k in text_lower for k in ['几台设备', '几个设备', '同时在线', '能同时用吗', '一个账号能登录几个设备', '多设备', '同时登录']):
        add_by_id('multi_device')
        selected = [faq for faq in selected if faq.id != 'multi_device']
        selected.insert(0, next(faq for faq in FAQS if faq.id == 'multi_device'))
        selected_ids = {item.id for item in selected}
    if any(k in text_lower for k in ['chatgpt', 'gemini', 'claude', 'ai平台', 'ai 节点', 'ai节点']):
        add_by_id('ai_platform_support')
    if any(k in text_lower for k in ['ai节点用不了', 'ai 节点用不了', 'ai节点不能用', 'ai节点不正常', 'gemini用不了', '解锁不了gemini']):
        add_by_id('ai_node_issue')

    return selected


def retrieve_faq_candidates(text: str, top_k: int = 3) -> List[tuple[tuple[int, int, int], FAQItem]]:
    scored = [(score_item(text, item), item) for item in FAQS]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(meta, item) for meta, item in scored if meta[0] > 0][:top_k]


def should_use_fast_path(text: str, items: List[FAQItem]) -> bool:
    if not items:
        return False

    text_lower = text.lower()

    # vague help requests should not jump to device/download fast paths
    if is_vague_help(text):
        return False

    # explicit platform support/download asks should go fast even if faq candidate scoring is weak
    explicit_fast_terms = [
        '支持mac吗', 'mac能用吗', 'mac可以用吗', '支持 windows', '支持windows', 'windows可以用吗', 'windows能用吗',
        '安卓怎么下载', 'iphone怎么下载', 'ios怎么下载', 'windows连上节点后上不了网', 'mac连上节点后上不了网'
    ]
    if any(term in text_lower for term in explicit_fast_terms):
        return True

    candidates = retrieve_faq_candidates(text, top_k=3)
    if not candidates:
        return False

    best_meta, best_item = candidates[0]
    best_score, matched_question, matched_keywords = best_meta
    second_score = candidates[1][0][0] if len(candidates) > 1 else 0

    # obvious support/download/platform questions should be answered immediately
    fast_intent_terms = [
        '支持', '下载', '怎么下', '怎么下载', '安装',
        '掉线', '断开', '上不了网', '打不开网页', '连接中', '连不上', 'gemini能用吗', '支持gemini吗',
        '套餐', 'vip', '几台设备', '几个设备', '同时在线', '能同时用吗', 'windows可以用吗', 'windows能用吗', '支持mac吗', 'mac能用吗'
    ]
    if any(term in text_lower for term in fast_intent_terms):
        return True

    # direct or high-confidence FAQ hit
    if matched_question:
        return True
    if best_score >= 18 and matched_keywords >= 2:
        return True
    if best_score >= 24 and second_score <= 6:
        return True

    # sensitive policy answers should prefer deterministic FAQ output
    if best_item.id in SENSITIVE_IDS:
        return True

    return False


def compose_fast_reply(text: str, items: List[FAQItem]) -> str:
    if not items:
        return FALLBACK_REPLY

    text_lower = text.lower()
    item_map = {item.id: item for item in items}

    # vague help requests should stay generic
    if is_vague_help(text):
        return build_vague_help_reply()

    # device support/download fast paths should only trigger when the current message clearly mentions the platform intent
    if any(k in text_lower for k in ['mac连上节点后上不了网', 'mac 连上节点后上不了网', 'mac连上后上不了网']):
        answer = item_map['mac_no_internet_after_connect'].answer if 'mac_no_internet_after_connect' in item_map else ''
        return make_support_style_reply(answer)

    if any(k in text_lower for k in ['支持mac', 'mac支持', 'mac怎么下载', 'macbook', '苹果电脑', '设备是mac', 'mac 可以用吗', '支持 mac', 'mac怎么下', 'mac 下载', '支持mac吗', 'mac能用吗']):
        return handle_mac_download()

    if any(k in text_lower for k in ['windows连上节点后上不了网', 'windows 连上节点后上不了网', 'windows连上后上不了网']):
        answer = item_map['windows_no_internet_after_connect'].answer if 'windows_no_internet_after_connect' in item_map else ''
        return make_support_style_reply(answer)

    if any(k in text_lower for k in ['支持windows', 'windows支持', 'windows怎么下载', 'windows可以用吗', '支持 windows', 'win10', 'win11', 'windows 下载', 'windows能用吗']):
        return handle_windows_download()

    if any(k in text_lower for k in ['支持安卓', '安卓支持', '安卓怎么下载', 'android支持', 'android怎么下载', '安卓可以用吗', 'android可以用吗', 'android 下载', '安卓 下载']):
        include_upgrade_guidance = any(k in text_lower for k in ['连接中', 'wifi', '校园网', '连不上'])
        return handle_android_download(include_upgrade_guidance=include_upgrade_guidance)

    if any(k in text_lower for k in ['支持iphone', '支持ios', 'iphone怎么下载', 'ios怎么下载', '苹果手机', 'iphone可以用吗', 'ios可以用吗', 'iphone 下载', 'ios 下载']):
        return handle_ios_download()

    if any(k in text_lower for k in ['几台设备', '几个设备', '同时在线', '能同时用吗', '一个账号能登录几个设备', '多设备', '同时登录']):
        return handle_multi_device()

    if 'plans' in item_map and any(k in text_lower for k in ['套餐', 'vip套餐']):
        return handle_plan_query()

    if 'ai_platform_support' in item_map and is_ai_platform_support(text):
        return handle_ai_platform_support()

    if 'ai_node_issue' in item_map and is_ai_node_issue(text):
        return handle_ai_node_issue()

    if 'streaming_support' in item_map and is_streaming_support(text):
        return handle_streaming_support()

    if 'streaming_issue' in item_map and is_streaming_issue(text):
        return handle_streaming_issue(detect_node_name(text))

    handler_reply = render_handler_reply(items[0].handler, text, items[0])
    if handler_reply:
        return handler_reply

    if items[0].id in SENSITIVE_IDS:
        return format_answer(items[0])

    return make_support_style_reply(items[0].answer, '如果你愿意，也可以把具体情况继续发我，我帮你往下排查。')


def format_answer(item: FAQItem) -> str:
    suffix = "\n\n如果你的情况不一样，也可以把设备类型、截图或报错提示发我，我再继续帮你看。"
    return item.answer + suffix


def render_handler_reply(handler_name: Optional[str], text: str, item: Optional[FAQItem] = None) -> Optional[str]:
    if not handler_name:
        return None

    if handler_name == 'plan_query':
        return handle_plan_query()
    if handler_name == 'vip_vs_free':
        return handle_vip_vs_free()
    if handler_name == 'become_vip':
        return handle_become_vip()
    if handler_name == 'vip_benefit':
        return handle_vip_benefits()
    if handler_name == 'android_download':
        include_upgrade_guidance = any(k in text.lower() for k in ['连接中', 'wifi', '校园网', '连不上'])
        return handle_android_download(include_upgrade_guidance=include_upgrade_guidance)
    if handler_name == 'ios_download':
        return handle_ios_download()
    if handler_name == 'windows_download':
        return handle_windows_download()
    if handler_name == 'mac_download':
        return handle_mac_download()
    if handler_name == 'editions_difference':
        return handle_editions_difference()
    if handler_name == 'streaming_support':
        return handle_streaming_support()
    if handler_name == 'streaming_issue':
        return handle_streaming_issue(detect_node_name(text))
    if handler_name == 'ai_platform_support':
        return handle_ai_platform_support()
    if handler_name == 'ai_node_issue':
        return handle_ai_node_issue()
    if handler_name == 'multi_device':
        return handle_multi_device()
    if handler_name == 'speed_issue':
        return handle_speed_issue()
    if handler_name == 'android_wifi_connecting_issue':
        return handle_android_wifi_connecting_issue()
    if handler_name == 'disconnect_issue':
        return handle_disconnect_issue()

    return None


def build_knowledge_context(items: List[FAQItem]) -> str:
    blocks = []
    for idx, item in enumerate(items, start=1):
        blocks.append(f"[{idx}] 分类: {item.category}\n问题: {item.question}\n答案: {item.answer}")
    return "\n\n".join(blocks)


def should_force_literal(items: List[FAQItem]) -> bool:
    return any(item.id in SENSITIVE_IDS for item in items)


def detect_short_context_reply(text: str) -> dict:
    t = text.strip().lower()
    result = {}

    # network type: only infer when the phrase explicitly refers to network environment
    if any(k in t for k in ['用的是wifi', '是wifi', 'wifi', 'wi-fi', '校园网', '家用wifi', '无线网络']):
        result['network_type'] = 'wifi'
    elif any(k in t for k in ['用的是流量', '是流量', '手机流量', '4g', '5g', 'mobile data']):
        result['network_type'] = 'mobile'

    # device type: avoid using generic "电脑" alone because it can misclassify context
    if any(k in t for k in ['安卓', 'android', '安卓的']):
        result['device_type'] = 'android'
    elif any(k in t for k in ['iphone', 'ios', 'ipad', '苹果手机', '苹果的']):
        result['device_type'] = 'ios'
    elif any(k in t for k in ['mac', 'macbook', '苹果电脑', 'mac的']):
        result['device_type'] = 'mac'
    elif any(k in t for k in ['windows', 'win10', 'win11', 'win 10', 'win 11', '是windows的', '我是windows', 'windows的']):
        result['device_type'] = 'windows'

    if any(k in t for k in ['连接中', '卡死', '一直转圈', '一直连接中']):
        result['issue_type'] = 'connecting'
    elif any(k in t for k in ['掉线', '断开', '自动变成断开', '老是掉线', '自动断开', '用着用着会断开', '过一段时间就断开', '会自己断开', '视频也能刷但是会断开']):
        result['issue_type'] = 'disconnecting'
    elif any(k in t for k in ['连不上', '连接失败', '无法连接']):
        result['issue_type'] = 'cannot_connect'
    elif any(k in t for k in ['上不了网', '打不开网页', '没网']):
        result['issue_type'] = 'no_internet'

    if any(k in t for k in ['其他可以', '其他节点可以', '只有这个节点不行', '只有美国1有问题', '只有这个节点有问题', '别的节点正常', '不太正常，其他还可以', '只有这个节点异常']):
        result['node_scope'] = 'single_node_problem'
    elif any(k in t for k in ['都有问题', '所有节点都有问题', '全部节点都不行', '每个节点都会断', '换别的也一样', '其他节点也不行', '所有节点都这样']):
        result['node_scope'] = 'all_nodes_problem'

    return result


def format_device_name(device: str) -> str:
    mapping = {
        'android': '安卓',
        'ios': 'iPhone / iOS',
        'mac': 'Mac',
        'windows': 'Windows',
    }
    return mapping.get(device, device)


def should_keep_context(reply: str) -> bool:
    keep_terms = ['告诉我一下设备类型', '你现在用的是', '截图', '节点名称', '继续帮你排查', '继续跟进处理', '工程师继续跟进']
    return any(term in reply for term in keep_terms)


def ask_next_question(ctx: dict) -> str:
    if not ctx.get('issue_type'):
        return '明白了。你这边具体是连接不上、一直显示连接中、老是掉线，还是连上节点后上不了网？'

    issue = ctx.get('issue_type')

    # First: use a unified troubleshooting flow before splitting by platform.
    if ctx.get('node_scope') == 'single_node_problem':
        node_name = ctx.get('node_name')
        first_line = f'收到，{node_name} 这边比较像是单个节点异常，不是全面连接问题。' if node_name else '收到，那就比较像是单个节点异常，不是全面连接问题。'
        return (
            first_line + '\n\n'
            '你可以先临时使用其他正常节点，我们这边会把这个节点的问题记录下来，并让技术继续跟进处理。\n\n'
            '如果方便，也可以把有问题的节点名称、设备类型和截图一起发我，我这边更好登记。'
        )

    if ctx.get('node_scope') == 'all_nodes_problem':
        return (
            '收到，如果所有节点都有类似问题，那就更像不是单个节点异常，而是本地网络环境、设备状态、代理冲突或者客户端本身的问题。\n\n'
            '建议你先确认当前网络是否稳定，并检查有没有同时开着其他 VPN、代理或网络工具；如果有，请先关闭后再试。\n\n'
            '如果方便，也请把设备类型、系统版本、当前网络环境和截图发我，我继续帮你排查。'
        )

    if issue in {'disconnecting', 'no_internet', 'connecting', 'cannot_connect'}:
        base_reply = []
        if issue == 'disconnecting':
            base_reply.append('明白了，这种情况更像是连接建立后中途断开。')
        elif issue == 'no_internet':
            base_reply.append('明白了，这种情况更像是节点已经连上了，但后续网络没有正常走出去。')
        elif issue == 'connecting':
            base_reply.append('明白了，这种情况更像是连接建立过程卡住了。')
        else:
            base_reply.append('明白了，这种情况更像是连接建立没有成功。')

        regions = format_recommended_regions()
        base_reply.append(
            '你先统一按这个顺序排查看看：\n'
            '1）先确认本机本身网络正常；\n'
            '2）检查是否同时开着其他 VPN、代理或网络工具，如果有请先关闭；\n'
            '3）切换其他节点测试一下，看看是只有个别节点有问题，还是所有节点都这样；\n'
            f'4）切换节点时，也建议优先尝试{regions}，这些节点通常速度更快、节点也更多；\n'
            '5）如果其他节点正常，可以先临时使用其他节点，我们这边会记录问题并让技术继续跟进。'
        )

        # Only after the common steps, ask for device/platform details.
        if not ctx.get('device_type'):
            base_reply.append('另外再麻烦告诉我一下设备类型，是安卓、iPhone、Windows 还是 Mac？')
        elif not ctx.get('network_type'):
            base_reply.append('另外再确认一下，你现在用的是 Wi‑Fi 还是流量？')
        else:
            device = ctx.get('device_type')
            network = 'Wi‑Fi' if ctx.get('network_type') == 'wifi' else '流量'
            if device == 'android' and network == 'Wi‑Fi' and issue in {'connecting', 'cannot_connect'}:
                base_reply.append(
                    '如果你这边是安卓 + Wi‑Fi 环境，尤其校园网 Wi‑Fi，建议优先升级到 10.0.0 以上版本后再测试：\n'
                    'https://q1w2e3r4.xyz/android/aox-v10.0.0.apk\n'
                    '也可以直接在官网下载安装。'
                )
            elif device == 'windows' and issue == 'no_internet':
                base_reply.append('如果前面的通用排查都做过了，Windows 这边再继续看一下防火墙、安全软件，以及虚拟网卡 utun99 是否创建成功。')
            elif device == 'mac' and issue == 'no_internet':
                base_reply.append('如果前面的通用排查都做过了，Mac 这边再继续看一下系统权限、防火墙、网络扩展权限，以及虚拟网卡 tun0 是否创建成功。')

        return '\n\n'.join(base_reply)

    return '收到，我已经记下你的情况了。你再把当前报错提示或截图发我，我继续帮你判断。'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_REPLY)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_REPLY)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id if user else 0
    message_id = update.message.message_id if update.message else None
    text_lower = text.lower()

    if is_greeting(text):
        clear_user_context(user_id)
        await update.message.reply_text(GREETING_REPLY)
        return

    if is_duplicate_message(user_id, text, message_id=message_id):
        logger.info('Skip duplicate message -> user_id=%s text=%s', user_id, text)
        return

    if is_recommended_nodes_query(text):
        clear_user_context(user_id)
        regions = format_recommended_regions()
        reply = make_support_style_reply(
            f'一般情况下，建议你优先尝试{regions}，这些节点通常速度更快、节点也更多。',
            '如果你这边主要是 AI 平台使用，可以优先选择 AI 节点；如果是看 Netflix、YouTube 等流媒体，可以优先选择流媒体节点。'
        )
        await update.message.reply_text(reply)
        return

    if is_greeting(text):
        clear_user_context(user_id)
        await update.message.reply_text(GREETING_REPLY)
        return

    ctx = get_user_context(user_id)
    if ctx and is_context_expired(ctx):
        clear_user_context(user_id)
        ctx = {}

    extracted = detect_short_context_reply(text)
    node_name = detect_node_name(text)

    # Strong first-turn routing for high-frequency real scenarios.
    if is_recommended_nodes_query(text):
        clear_user_context(user_id)
        await update.message.reply_text(handle_recommended_nodes())
        return

    if is_ios_download_query(text):
        items = retrieve_faqs(text, top_k=AI_TOP_K if AI_ENABLED else 1)
        await update.message.reply_text(compose_fast_reply('iphone怎么下载', items))
        clear_user_context(user_id)
        return

    if is_platform_support_query(text):
        normalized_text = text
        if text_lower in {'mac', '苹果电脑'}:
            normalized_text = '支持mac吗'
        elif text_lower in {'windows'}:
            normalized_text = 'windows可以用吗'
        elif text_lower in {'安卓', 'android'}:
            normalized_text = '安卓怎么下载'
        elif text_lower in {'ios', 'iphone', '苹果手机'}:
            normalized_text = 'iphone怎么下载'
        items = retrieve_faqs(normalized_text, top_k=AI_TOP_K if AI_ENABLED else 1)
        await update.message.reply_text(compose_fast_reply(normalized_text, items))
        clear_user_context(user_id)
        return

    if is_multi_device_query(text):
        await update.message.reply_text(handle_multi_device())
        clear_user_context(user_id)
        return

    if is_plan_query(text):
        await update.message.reply_text(handle_plan_query())
        clear_user_context(user_id)
        return

    if is_editions_query(text):
        await update.message.reply_text(handle_editions_difference())
        clear_user_context(user_id)
        return

    if is_vip_query(text):
        if any(k in text_lower for k in ['vip和免费的区别', 'vip和免费有什么区别']):
            reply = handle_vip_vs_free()
        elif any(k in text_lower for k in ['vip有什么作用', 'vip有什么用', '开vip有什么用', 'vip有什么权益', 'vip的作用']):
            reply = handle_vip_benefits()
        else:
            reply = handle_become_vip()
        await update.message.reply_text(reply)
        clear_user_context(user_id)
        return

    if is_ai_platform_support(text):
        await update.message.reply_text(handle_ai_platform_support())
        clear_user_context(user_id)
        return

    if is_ai_node_issue(text):
        reply = handle_ai_node_issue()
        set_user_context(user_id, issue_type='ai_node_issue', awaiting_field='followup')
        if node_name:
            set_user_context(user_id, node_name=node_name)
        await update.message.reply_text(reply)
        return

    if is_streaming_support(text):
        await update.message.reply_text(handle_streaming_support())
        clear_user_context(user_id)
        return

    if is_vague_help(text):
        clear_user_context(user_id)
        await update.message.reply_text(build_vague_help_reply())
        return

    # If we are already in a troubleshooting thread, prefer treating short messages as follow-up.
    if ctx:
        followup_hit = bool(extracted) or looks_like_context_followup(text) or bool(node_name)
        if followup_hit:
            patch = dict(extracted)

            if is_recommended_nodes_query(text):
                clear_user_context(user_id)
                await update.message.reply_text(handle_recommended_nodes())
                return

            if node_name:
                patch['node_name'] = node_name
                if 'node_scope' not in patch and ('其他' not in text_lower and '都有问题' not in text_lower):
                    patch['node_scope'] = 'single_node_problem'
            if ctx.get('issue_type') == 'ai_node_issue' and node_name:
                patch['node_scope'] = patch.get('node_scope', 'single_node_problem')
            if patch:
                set_user_context(user_id, **patch)
            ctx = get_user_context(user_id)

            # Dedicated follow-up reply for AI node issues.
            if ctx.get('issue_type') == 'ai_node_issue':
                if ctx.get('node_scope') == 'all_nodes_problem':
                    reply = (
                        '收到，如果所有 AI 节点都有类似情况，那更像不是单个节点异常。\n\n'
                        '你可以先确认当前网络是否正常，并切换其他普通节点测试一下。我们这边也会先记录情况，并让工程师继续跟进处理。\n\n'
                        '如果方便，也请把设备类型和截图发我。'
                    )
                else:
                    node_name = ctx.get('node_name')
                    if node_name:
                        first_line = f'收到，如果是 {node_name} 暂时解锁不了 Gemini，建议你先切换到其他可用节点测试一下。'
                    else:
                        first_line = '收到，如果暂时解锁不了 Gemini，建议你先切换到其他可用节点测试一下。'
                    reply = (
                        first_line + '\n\n'
                        '如果只是个别 AI 节点异常，我们这边会先记录问题，并让工程师继续跟进处理。\n\n'
                        '如果方便，也请把设备类型和截图发我，我这边一起登记。'
                    )
                set_user_context(user_id, awaiting_field='followup')
                await update.message.reply_text(reply)
                return

            reply = ask_next_question(ctx)
            if ctx.get('node_scope') == 'single_node_problem' or ctx.get('node_scope') == 'all_nodes_problem':
                set_user_context(user_id, awaiting_field='followup')
            elif not ctx.get('device_type'):
                set_user_context(user_id, awaiting_field='device_type')
            elif not ctx.get('network_type'):
                set_user_context(user_id, awaiting_field='network_type')
            elif not ctx.get('issue_type'):
                set_user_context(user_id, awaiting_field='issue_type')
            else:
                set_user_context(user_id, awaiting_field='followup')
            await update.message.reply_text(reply)
            return

    # Start a lightweight troubleshooting context from short/direct issue descriptions.
    if len(text) <= 80 and (extracted or node_name or any(k in text_lower for k in ['不太稳定', '解锁不了', 'gemini', '奈非', '奈飞', 'netflix'])):
        patch = dict(extracted)
        if node_name:
            patch['node_name'] = node_name
        if is_ai_node_issue(text):
            patch['issue_type'] = 'ai_node_issue'
        elif is_streaming_issue(text):
            patch['issue_type'] = patch.get('issue_type') or 'streaming_issue'
        elif '不太稳定' in text_lower and 'issue_type' not in patch:
            patch['issue_type'] = 'disconnecting'
        if patch:
            set_user_context(user_id, **patch)
            ctx = get_user_context(user_id)
            set_user_context(user_id, awaiting_field='followup')
            if ctx.get('issue_type') == 'ai_node_issue':
                items = retrieve_faqs(text, top_k=AI_TOP_K if AI_ENABLED else 1)
                await update.message.reply_text(compose_fast_reply(text, items))
                return
            if ctx.get('issue_type') == 'streaming_issue':
                items = retrieve_faqs(text, top_k=AI_TOP_K if AI_ENABLED else 1)
                await update.message.reply_text(compose_fast_reply(text, items))
                return
            await update.message.reply_text(ask_next_question(ctx))
            return

    items = retrieve_faqs(text, top_k=AI_TOP_K if AI_ENABLED else 1)
    if not items:
        clear_user_context(user_id)
        await update.message.reply_text(FALLBACK_REPLY)
        return

    if should_use_fast_path(text, items):
        logger.info('Fast path -> faq_hits=%s text=%s', len(items), text)
        reply = compose_fast_reply(text, items)
        if should_keep_context(reply):
            patch = dict(extracted)
            if node_name:
                patch['node_name'] = node_name
            if any(k in text_lower for k in ['连接中', '连不上', '上不了网', '打不开网页', '掉线', '断开', '不太稳定']):
                issue_type = patch.get('issue_type')
                if not issue_type and any(k in text_lower for k in ['不稳定', '会断', '会自己断', '自动断']):
                    patch['issue_type'] = 'disconnecting'
            if is_ai_node_issue(text):
                patch['issue_type'] = 'ai_node_issue'
            if patch:
                set_user_context(user_id, **patch)
            set_user_context(user_id, awaiting_field='followup')
        else:
            clear_user_context(user_id)
        await update.message.reply_text(reply)
        return

    if AI_ENABLED:
        ai_reply = generate_ai_reply(
            user_text=text,
            items=items,
            ai_enabled=AI_ENABLED,
            ai_provider=AI_PROVIDER,
            ai_api_base=AI_API_BASE,
            ai_api_key=AI_API_KEY,
            openclaw_gateway_token=OPENCLAW_GATEWAY_TOKEN,
            ai_model=AI_MODEL,
            ai_timeout_seconds=AI_TIMEOUT_SECONDS,
            force_literal=should_force_literal(items),
            knowledge=build_knowledge_context(items),
            logger=logger,
        )
        if ai_reply:
            clear_user_context(user_id)
            await update.message.reply_text(ai_reply)
            return

    clear_user_context(user_id)
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
