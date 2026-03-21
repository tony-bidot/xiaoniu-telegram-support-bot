from facts_loader import get_multi_device_limit, get_vip_facts
from reply_templates import (
    build_become_vip_reply,
    build_multi_device_reply,
    build_plan_reply,
    build_vip_benefits_reply,
    build_vip_vs_free_reply,
)


def handle_vip_benefits() -> str:
    vip = get_vip_facts()
    return build_vip_benefits_reply(vip)


def handle_vip_vs_free() -> str:
    vip = get_vip_facts()
    return build_vip_vs_free_reply(vip)


def handle_become_vip() -> str:
    vip = get_vip_facts()
    return build_become_vip_reply(vip)


def handle_plan_query() -> str:
    vip = get_vip_facts()
    return build_plan_reply(vip)


def handle_multi_device() -> str:
    limit = get_multi_device_limit()
    return build_multi_device_reply(limit)
