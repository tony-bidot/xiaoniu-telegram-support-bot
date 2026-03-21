FALLBACK_REPLY = (
    "你好，我在的。\n"
    "如果你这边是遇到使用问题，可以直接把情况发我，我帮你一起判断。\n\n"
    "为了更快帮你排查，建议你顺手补充：\n"
    "1. 设备类型（安卓/iPhone/Windows/Mac）\n"
    "2. 具体报错提示\n"
    "3. 截图（如果方便）\n\n"
    "如果你想直接找人工，也可以联系：{human_contact}"
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

GREETING_REPLY = (
    "你好，我在的。\n"
    "如果你这边有下载、登录、连接、掉线或者节点使用方面的问题，都可以直接发我，我来帮你看。"
)


def build_fallback_reply(human_contact: str) -> str:
    return FALLBACK_REPLY.format(human_contact=human_contact)


def build_vague_help_reply() -> str:
    return '可以，你直接说下具体遇到什么情况，我帮你看。\n\n如果方便，也可以顺手带上设备类型、当前情况和截图，这样我判断会更快。'


def make_support_style_reply(*parts: str) -> str:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if not cleaned:
        return ''
    return "\n\n".join(cleaned)


def build_android_download_reply(facts: dict, include_upgrade_guidance: bool = False) -> str:
    parts = [
        '支持安卓，可以使用。',
        f"安卓下载地址如下：\n{facts.get('downloadUrl', '')}",
    ]
    if include_upgrade_guidance:
        parts.append(
            f"如果你这边是连接中卡住、Wi‑Fi 或校园网环境下不太稳定，建议优先升级到 {facts.get('upgradeVersion', '')} 以上版本。\n升级地址：\n{facts.get('upgradeUrl', '')}"
        )
    parts.append('如果你要的话，我也可以继续帮你看安装、升级或者连接问题。')
    return make_support_style_reply(*parts)


def build_ios_download_reply(facts: dict) -> str:
    return make_support_style_reply(
        '支持 iPhone / iOS。',
        f"iOS 目前没有正式上架版本，当前仅提供 {facts.get('distribution', '')} 版本。\n下载地址如下：\n{facts.get('downloadUrl', '')}\n\n{facts.get('storeReleaseNote', '')}",
        '如果你告诉我你的设备型号和系统版本，我也可以继续按设备引导你。'
    )


def build_windows_download_reply(facts: dict) -> str:
    return make_support_style_reply(
        f"支持的，不过 Windows 目前仅支持 {facts.get('minVersion', '')} 及以上版本。",
        f"Windows 下载地址：\n{facts.get('downloadUrl', '')}",
        '如果你方便的话，也可以直接告诉我你是 Windows 什么版本，我按设备继续发你对应步骤。'
    )


def build_mac_download_reply(facts: dict) -> str:
    return make_support_style_reply(
        '支持的，Mac 可以使用。',
        f"Mac 最新版本下载信息如下：\nMac {facts.get('version', '')}：\n{facts.get('downloadUrl', '')}",
        '如果你需要，我也可以继续帮你看安装或连接步骤。'
    )


def build_vip_benefits_reply(vip: dict) -> str:
    return make_support_style_reply(vip.get('benefits', ''))


def build_vip_vs_free_reply(vip: dict) -> str:
    return make_support_style_reply(f"{vip.get('benefits', '')}；{vip.get('freeUserLimit', '')}")


def build_become_vip_reply(vip: dict) -> str:
    return make_support_style_reply(vip.get('purchaseUrlNote', ''))


def build_plan_reply(vip: dict) -> str:
    return make_support_style_reply(vip.get('plansNote', ''))


def build_multi_device_reply(limit: int) -> str:
    return make_support_style_reply(f"一个账号目前支持 {limit} 个设备同时在线使用。")


def build_recommended_nodes_reply(regions_text: str) -> str:
    return make_support_style_reply(
        f"一般情况下，建议你优先尝试{regions_text}，这些节点通常速度更快、节点也更多。",
        '如果你这边主要是 AI 平台使用，可以优先选择 AI 节点；如果是看 Netflix、YouTube 等流媒体，可以优先选择流媒体节点。'
    )


def build_ai_platform_reply(regions_text: str, ai_node_facts: dict) -> str:
    platforms = '、'.join(ai_node_facts.get('platforms', ['ChatGPT', 'Gemini', 'Claude']))
    node_name = ai_node_facts.get('name', 'AI 节点')
    return make_support_style_reply(
        '支持的。',
        f"如果你需要使用 {platforms} 或其他 AI 平台，请选择 {node_name} 进行连接。",
        f"一般情况下，也建议优先尝试{regions_text}，这些节点通常速度更快、节点也更多。",
        '如果你已经选择了 AI 节点但还是不能正常使用，也可以把节点名称、设备类型和截图发我，我继续帮你看。'
    )


def build_ai_node_issue_reply() -> str:
    return make_support_style_reply(
        '收到，如果 AI 节点（例如 Gemini 相关节点）暂时不能正常使用，建议你先切换到其他可用节点测试一下。',
        '如果只是个别 AI 节点异常，我们这边会先记录问题，并让工程师继续跟进处理。',
        '如果方便，也请把有问题的节点名称、设备类型和截图发我。'
    )


def build_streaming_support_reply(regions_text: str, streaming_facts: dict) -> str:
    platforms = '、'.join(streaming_facts.get('platforms', ['Netflix', 'YouTube']))
    node_name = streaming_facts.get('name', '流媒体节点')
    return make_support_style_reply(
        f"如果你需要看 {platforms} 或其他流媒体，请选择{node_name}进行连接。",
        f"一般情况下，也建议优先尝试{regions_text}，这些节点通常速度更快、节点也更多。",
        '如果只是个别节点的流媒体可用性不正常，你也可以先切换到其他流媒体节点使用，我们这边会记录问题并让技术继续跟进处理。'
    )


def build_streaming_issue_reply(node_name: str | None = None) -> str:
    intro = f'收到，如果是 {node_name} 看不了奈飞 / Netflix，但其他节点正常，那更像是单个节点的流媒体可用性问题。' if node_name else '收到，如果是某个节点看不了奈飞 / Netflix，但其他节点正常，那更像是单个节点的流媒体可用性问题。'
    return make_support_style_reply(
        intro,
        '你可以先临时切换到其他可用节点使用，我们这边会记录这个节点的问题，并让技术继续跟进处理。',
        '如果方便，也可以把有问题的节点名称和截图发我。'
    )


def build_editions_difference_reply(editions: dict) -> str:
    regular = editions.get('regular', {}).get('name', '常规版')
    speed = editions.get('speed', {}).get('name', '极速版')
    desc = editions.get('speed', {}).get('description', '采用新技术更新的版本，只保留核心 VPN 功能。')
    recommend = editions.get('speed', {}).get('recommendedWhenUnstable', True)
    extra = f'如果 {regular} 使用不稳定，建议优先尝试 {speed}。' if recommend else ''
    return make_support_style_reply(
        f'目前所有平台都分为{regular}和{speed}。{speed}是{desc}',
        extra,
    )


def build_speed_issue_reply(regions_text: str) -> str:
    return make_support_style_reply(
        f'如果速度较慢或感觉节点不太稳定，建议先尝试：1）切换网络；2）更换线路或节点；3）优先尝试{regions_text}；4）关闭后台占用流量的软件；5）重启应用后重新连接。',
        '如果还是很慢，请把你的设备类型和当前使用情况发给客服。'
    )


def build_android_wifi_connecting_issue_reply(android: dict) -> str:
    return make_support_style_reply(
        '之前各平台的 VPN 都有部分用户遇到一直显示“连接中”、卡死需要重启 App，或者在 Wi‑Fi 环境下连接不上（尤其是校园网 Wi‑Fi）的情况。',
        f"如果你使用的是安卓客户端，建议优先升级到 {android.get('upgradeVersion', '')} 以上版本后再测试。\n下载地址：\n{android.get('upgradeUrl', '')}\n也可以直接在官网下载安装。",
        '升级后建议：\n1）先完全退出旧版 App；\n2）安装新版后重新打开；\n3）在 Wi‑Fi 和流量环境下分别测试一次；\n4）如果还是卡在“连接中”，请把手机型号、安卓版本、当前网络环境（如校园网 Wi‑Fi / 家用 Wi‑Fi / 流量）和截图发给客服。'
    )


def build_disconnect_issue_reply(regions_text: str) -> str:
    return make_support_style_reply(
        '明白了，这种情况更像是连接建立后中途断开。建议先按下面顺序排查：\n1）先确认本机本身网络正常；\n2）检查是否同时开着其他 VPN、代理或网络工具，如果有请先关闭；\n3）切换其他节点测试一下，看看是所有节点都会这样，还是只有个别节点会断开；\n4）切换节点时，也建议优先尝试' + regions_text + '，这些节点通常速度更快、节点也更多；\n5）如果只有部分节点会断，建议先临时使用其他正常节点，我们这边会记录问题并让技术继续跟进处理；\n6）如果所有节点都会这样，更像是本地网络环境、设备状态、代理冲突或客户端本身的问题，建议继续提供设备类型、系统版本和截图给客服排查。',
        '如果方便，也请把设备类型、系统版本、客户端截图和当前网络环境发给客服。'
    )
