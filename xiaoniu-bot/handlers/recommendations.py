from facts_loader import format_recommended_regions, get_node_types
from reply_templates import (
    build_ai_node_issue_reply,
    build_ai_platform_reply,
    build_recommended_nodes_reply,
    build_streaming_issue_reply,
    build_streaming_support_reply,
)


def handle_recommended_nodes() -> str:
    return build_recommended_nodes_reply(format_recommended_regions())


def handle_ai_platform_support() -> str:
    node_types = get_node_types()
    return build_ai_platform_reply(format_recommended_regions(), node_types.get('ai', {}))


def handle_ai_node_issue() -> str:
    return build_ai_node_issue_reply()


def handle_streaming_support() -> str:
    node_types = get_node_types()
    return build_streaming_support_reply(format_recommended_regions(), node_types.get('streaming', {}))


def handle_streaming_issue(node_name: str | None = None) -> str:
    return build_streaming_issue_reply(node_name)
