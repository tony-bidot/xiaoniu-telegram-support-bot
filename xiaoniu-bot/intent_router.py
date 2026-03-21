from typing import Optional


def is_ios_download_query(text: str) -> bool:
    t = text.strip().lower()
    ios_terms = ['ios', 'iphone', 'ios下载', 'iphone下载', 'ios下载地址', 'iphone怎么下载', '苹果下载']
    block_terms = ['登录', '连不上', '上不了网', '连接中', '掉线']
    return any(k in t for k in ios_terms) and not any(k in t for k in block_terms)


def is_platform_support_query(text: str) -> bool:
    t = text.strip().lower()
    exact_terms = {
        'mac', '苹果电脑', 'windows', '安卓', 'android', 'ios', 'iphone', '苹果手机'
    }
    if t in exact_terms:
        return True
    return any(k in t for k in [
        '支持mac吗', 'mac能用吗', 'mac可以用吗', '支持 windows', '支持windows', 'windows可以用吗', 'windows能用吗',
        '安卓怎么下载', 'iphone怎么下载', 'ios怎么下载'
    ])


def is_multi_device_query(text: str) -> bool:
    t = text.strip().lower()
    return any(k in t for k in ['几台设备', '几个设备', '同时在线', '能同时用吗', '一个账号能登录几个设备', '多设备', '同时登录'])


def is_plan_query(text: str) -> bool:
    t = text.strip().lower()
    return any(k in t for k in ['套餐', 'vip套餐'])


def is_editions_query(text: str) -> bool:
    t = text.strip().lower()
    return any(k in t for k in ['常规版和极速版', '极速版', '常规版', '极速版是什么', '常规版不稳定'])


def is_vip_query(text: str) -> bool:
    t = text.strip().lower()
    return any(k in t for k in [
        'vip怎么购买', '怎么买vip', '请问vip怎么购买', '怎么成为vip', '怎么开通vip',
        'vip有什么作用', 'vip有什么用', '开vip有什么用', 'vip有什么权益',
        'vip和免费的区别', 'vip和免费有什么区别'
    ])


def is_greeting(text: str) -> bool:
    t = text.strip().lower()
    greetings = {
        'hi', 'hello', '你好', '您好', '在吗', '有人吗', '哈喽', '嗨', 'hello啊', '你好呀', 'hello!', 'hi!'
    }
    return t in greetings


def is_vague_help(text: str) -> bool:
    text_lower = text.lower().strip()
    if text_lower in {'有问题', '有个问题', '我有问题', '有点问题', '出问题了', '帮我看看', '帮忙看下'}:
        return True
    return False


def is_ai_platform_support(text: str) -> bool:
    t = text.lower()
    support_terms = [
        'chatgpt', 'gemini', 'claude', 'ai平台', 'ai 节点', 'ai节点',
        '什么节点可以用chatgpt', '什么节点可以用gemini', '哪些节点支持ai', 'ai相关',
        '支持chatgpt吗', '支持gemini吗', '可以用gemini吗', 'gemini能用吗', '小牛可以支持gemini吗'
    ]
    issue_terms = ['用不了', '不能用', '不正常', '异常', '解锁不了']
    return any(k in t for k in support_terms) and not any(k in t for k in issue_terms)


def is_ai_node_issue(text: str) -> bool:
    t = text.lower()
    if is_ai_platform_support(text):
        return False
    return any(k in t for k in ['ai节点用不了', 'ai 节点用不了', 'ai节点不能用', 'ai节点不正常', 'gemini用不了', '解锁不了gemini', 'gemini不能用'])


def is_streaming_support(text: str) -> bool:
    t = text.lower()
    support_terms = ['奈非', '奈飞', 'netflix', 'youtube', '流媒体', '看视频', '什么节点可以看netflix', '什么节点可以看youtube', '哪些节点支持流媒体', '流媒体节点']
    issue_terms = ['看不了', '不能看', '解锁不了', '不正常', '异常']
    return any(k in t for k in support_terms) and not any(k in t for k in issue_terms)


def is_streaming_issue(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ['看不了奈非', '看不了奈飞', '看不了netflix', '解锁不了奈飞', '解锁不了奈非'])


def detect_node_name(text: str) -> Optional[str]:
    t = text.strip()
    if '节点' not in t:
        return None
    generic_names = {'推荐节点', '普通节点', '流媒体节点', 'ai节点', 'ai 节点'}
    if t.lower() in generic_names or t in generic_names:
        return None
    if len(t) <= 12:
        return t
    return None


def is_recommended_nodes_query(text: str) -> bool:
    t = text.strip().lower()
    phrases = [
        '推荐节点', '有什么推荐节点吗', '有什么推荐节点', '推荐什么节点',
        '有推荐节点吗', '哪些节点比较推荐', '什么节点比较推荐', '什么节点比较快', '哪些节点比较快',
        '什么节点速度比较快', '哪些节点速度比较快'
    ]
    return any(p in t for p in phrases)


def looks_like_context_followup(text: str) -> bool:
    t = text.strip().lower()
    followup_terms = [
        '用的是', '当前是', '现在是', '一直', '自动', '断开', '掉线', '上不了网',
        '打不开网页', '连不上', '连接中', '校园网', 'wifi', 'wi-fi', '流量',
        '安卓', 'android', 'iphone', 'ios', 'ipad', 'mac', 'macbook', 'windows', 'win10', 'win11',
        '其他还可以', '都有问题', '其他可以', '节点不太正常', '看不了奈非', '看不了奈飞', 'netflix', '线路是不是有更新', '不太稳定',
        'gemini', 'ai节点', 'ai 节点', '解锁不了', '节点', '还是不行', '不能用', '美国1节点',
        '推荐节点', '有什么推荐节点吗', '推荐什么节点', '有推荐节点吗'
    ]
    return any(term in t for term in followup_terms)
