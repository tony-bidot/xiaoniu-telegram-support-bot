from facts_loader import get_android_facts, format_recommended_regions
from reply_templates import (
    build_android_wifi_connecting_issue_reply,
    build_disconnect_issue_reply,
    build_speed_issue_reply,
)


def handle_speed_issue() -> str:
    return build_speed_issue_reply(format_recommended_regions())


def handle_android_wifi_connecting_issue() -> str:
    android = get_android_facts()
    return build_android_wifi_connecting_issue_reply(android)


def handle_disconnect_issue() -> str:
    return build_disconnect_issue_reply(format_recommended_regions())
