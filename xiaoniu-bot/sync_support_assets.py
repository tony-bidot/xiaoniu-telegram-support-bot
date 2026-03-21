import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FACTS_PATH = BASE_DIR / 'facts.json'
PRODUCT_FACTS_MD = BASE_DIR / 'product_facts.md'
FAQ_PATH = BASE_DIR / 'faq.json'
CASES_PATH = BASE_DIR / 'cases.json'


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')


def replace_faq_answer(faq_items, faq_id: str, answer: str):
    for item in faq_items:
        if item.get('id') == faq_id:
            item['answer'] = answer
            return True
    return False


def replace_case_expect_contains(cases, case_id: str, expect_contains):
    for item in cases:
        if item.get('id') == case_id:
            item['expect_contains'] = expect_contains
            return True
    return False


def render_product_facts_md(facts: dict) -> str:
    product = facts['product']
    rec = '、'.join(facts['recommendedRegions'])
    ios = facts['platforms']['ios']
    windows = facts['platforms']['windows']
    mac = facts['platforms']['mac']
    android = facts['platforms']['android']
    vip = facts['vip']
    multi = facts['multiDevice']

    return f'''# 小牛VPN Product Facts

## 1. 产品定位
- {product['name']} 是一个{product['positioning']}。
- 当前对外表达可包含：自 {product['stableSince']} 年开始稳定运行至今。
- 常见用途包括：{product['summary']}

## 2. 支持平台
- 支持安卓
- 支持 iPhone / iOS
- 支持 Windows
- 支持 Mac

### Windows 限制
- Windows 目前仅支持 {windows['minVersion']} 及以上版本。

## 3. 通用优先推荐节点
- {rec}
- 这些节点通常速度更快、节点也更多。

## 4. 下载与安装事实

### Android
- 安卓客户端下载方式 / 下载地址应以 FAQ 为准。
- 安卓在连接中卡住、Wi‑Fi / 校园网问题时，优先建议升级到 {android['upgradeVersion']} 以上版本。
- 当前安卓升级下载地址：
  `{android['upgradeUrl']}`

### Windows
- Windows 下载地址：
  `{windows['downloadUrl']}`
- Windows 虚拟网卡名称：`{windows['virtualAdapter']}`

### Mac
- 当前 Mac 最新版本下载信息：
  - Mac {mac['version']}
  - `{mac['downloadUrl']}`
- Mac 虚拟网卡名称：`{mac['virtualAdapter']}`

### iPhone / iOS
- iOS 目前没有正式上架版本。
- 当前仅提供 {ios['distribution']} 版本。
- 当前 {ios['distribution']} 下载地址：
  `{ios['downloadUrl']}`
- {ios['storeReleaseNote']}

## 5. 版本类型
- 目前所有平台都分为常规版和极速版。
- 极速版是{facts['editions']['speed']['description']}
- 如果常规版使用不稳定，建议优先尝试极速版。

## 6. VIP / 免费用户与购买
- VIP 套餐选择：{vip['plansNote']}
- VIP 用户：{vip['benefits']}
- 免费用户：{vip['freeUserLimit']}
- 成为 VIP：{vip['purchaseUrlNote']}

## 7. 多设备使用
- 一个账号目前支持 {multi['maxOnlineDevices']} 个设备同时在线使用。
'''


def sync_product_facts_md(facts: dict):
    PRODUCT_FACTS_MD.write_text(render_product_facts_md(facts), encoding='utf-8')


def sync_faq(facts: dict):
    faq_items = load_json(FAQ_PATH)
    ios = facts['platforms']['ios']
    windows = facts['platforms']['windows']
    mac = facts['platforms']['mac']
    vip = facts['vip']
    multi = facts['multiDevice']
    speed_desc = '、'.join(facts['recommendedRegions'])

    replace_faq_answer(
        faq_items,
        'ios_download',
        f"iOS 目前没有正式上架版本，当前仅提供 {ios['distribution']} 版本。\n下载地址如下：\n{ios['downloadUrl']}\n\n{ios['storeReleaseNote']}"
    )
    replace_faq_answer(
        faq_items,
        'windows_download',
        f"Windows 目前仅支持 {windows['minVersion']} 及以上版本。\nWindows 下载地址：\n{windows['downloadUrl']}\n\n你也可以通过官网下载安装。如果你是 Windows 电脑，也可以直接告诉我系统版本，我帮你按设备说明。"
    )
    replace_faq_answer(
        faq_items,
        'mac_download',
        f"Mac 最新版本下载信息如下：\nMac {mac['version']}：\n{mac['downloadUrl']}\n\n你也可以通过官网下载安装。如果下载安装后仍有问题，请把 macOS 版本、错误提示和截图发给客服。"
    )
    replace_faq_answer(
        faq_items,
        'plans',
        vip['plansNote']
    )
    replace_faq_answer(
        faq_items,
        'vip_vs_free',
        f"{vip['benefits']}；{vip['freeUserLimit']}"
    )
    replace_faq_answer(
        faq_items,
        'become_vip',
        vip['purchaseUrlNote']
    )
    replace_faq_answer(
        faq_items,
        'multi_device',
        f"一个账号目前支持 {multi['maxOnlineDevices']} 个设备同时在线使用。"
    )
    replace_faq_answer(
        faq_items,
        'speed_issue',
        f"如果速度较慢或感觉节点不太稳定，建议先尝试：1）切换网络；2）更换线路或节点；3）优先尝试{speed_desc}；4）关闭后台占用流量的软件；5）重启应用后重新连接。\n\n如果还是很慢，请把你的设备类型和当前使用情况发给客服。"
    )
    dump_json(FAQ_PATH, faq_items)


def sync_cases(facts: dict):
    cases = load_json(CASES_PATH)
    ios = facts['platforms']['ios']
    multi = facts['multiDevice']

    replace_case_expect_contains(
        cases,
        'ios_testflight_only',
        ['没有正式上架版本', ios['distribution'], ios['downloadUrl']]
    )
    replace_case_expect_contains(
        cases,
        'multi_device',
        [f"{multi['maxOnlineDevices']} 个设备同时在线"]
    )
    dump_json(CASES_PATH, cases)


def main():
    facts = load_json(FACTS_PATH)
    sync_product_facts_md(facts)
    sync_faq(facts)
    sync_cases(facts)
    print('Synced support assets from facts.json')


if __name__ == '__main__':
    main()
