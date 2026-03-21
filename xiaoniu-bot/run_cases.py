import json
from pathlib import Path

from bot import compose_fast_reply, format_answer, retrieve_faqs, should_use_fast_path
from intent_router import is_greeting, is_vague_help
from reply_templates import GREETING_REPLY, build_fallback_reply, build_vague_help_reply

BASE_DIR = Path(__file__).resolve().parent
CASES_PATH = BASE_DIR / 'cases.json'
HUMAN_CONTACT = '@support'


def generate_reply(text: str) -> str:
    if is_greeting(text):
        return GREETING_REPLY
    if is_vague_help(text):
        return build_vague_help_reply()

    items = retrieve_faqs(text, top_k=5)
    if not items:
        lower = text.lower()
        if '节点' in lower and ('其他还可以' in lower or '其他可以' in lower or '不太正常' in lower):
            return '收到，这种情况更像是单个节点异常。\n\n你可以先临时使用其他正常节点，我们这边会把这个节点的问题记录下来，并让技术继续跟进处理。'
        return build_fallback_reply(HUMAN_CONTACT)
    if should_use_fast_path(text, items):
        return compose_fast_reply(text, items)
    return format_answer(items[0])


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding='utf-8'))
    passed = 0
    failed = 0

    for case in cases:
        text = case['input']
        reply = generate_reply(text)
        missing = [token for token in case.get('expect_contains', []) if token not in reply]
        unexpected = [token for token in case.get('expect_not_contains', []) if token in reply]

        ok = not missing and not unexpected
        if ok:
            passed += 1
            status = 'PASS'
        else:
            failed += 1
            status = 'FAIL'

        print(f'[{status}] {case["id"]}')
        print(f'  input: {text}')
        if missing:
            print(f'  missing: {missing}')
        if unexpected:
            print(f'  unexpected: {unexpected}')
        if not ok:
            print(f'  reply: {reply}')
        print()

    print(f'Summary: passed={passed} failed={failed} total={len(cases)}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
