from facts_loader import get_editions_facts
from reply_templates import build_editions_difference_reply


def handle_editions_difference() -> str:
    editions = get_editions_facts()
    return build_editions_difference_reply(editions)
