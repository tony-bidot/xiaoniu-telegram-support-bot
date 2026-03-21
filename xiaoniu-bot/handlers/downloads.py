from facts_loader import get_android_facts, get_ios_facts, get_mac_facts, get_windows_facts
from reply_templates import (
    build_android_download_reply,
    build_ios_download_reply,
    build_mac_download_reply,
    build_windows_download_reply,
)


def handle_android_download(include_upgrade_guidance: bool = False) -> str:
    facts = get_android_facts()
    return build_android_download_reply(facts, include_upgrade_guidance=include_upgrade_guidance)


def handle_ios_download() -> str:
    facts = get_ios_facts()
    return build_ios_download_reply(facts)


def handle_windows_download() -> str:
    facts = get_windows_facts()
    return build_windows_download_reply(facts)


def handle_mac_download() -> str:
    facts = get_mac_facts()
    return build_mac_download_reply(facts)
