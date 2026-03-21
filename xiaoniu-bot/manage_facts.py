import html
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

BASE_DIR = Path(__file__).resolve().parent
FACTS_PATH = BASE_DIR / 'facts.json'
SYNC_SCRIPT = BASE_DIR / 'sync_support_assets.py'
HOST = '127.0.0.1'
PORT = 8765


def load_facts_text() -> str:
    return FACTS_PATH.read_text(encoding='utf-8')


def save_facts_text(text: str) -> None:
    parsed = json.loads(text)
    FACTS_PATH.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run_sync() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ['python3', str(SYNC_SCRIPT)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = (result.stdout or '') + (result.stderr or '')
        return result.returncode == 0, output.strip() or 'sync finished'
    except Exception as e:
        return False, str(e)


def render_page(message: str = '', error: bool = False) -> bytes:
    facts_text = load_facts_text()
    msg_html = ''
    if message:
        color = '#b00020' if error else '#0a7f2e'
        msg_html = f'<div style="margin:12px 0;padding:10px;border-radius:8px;background:#f6f6f6;color:{color};white-space:pre-wrap;">{html.escape(message)}</div>'

    page = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Xiaoniu Facts Manager</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 24px; background:#fafafa; color:#222; }}
    h1 {{ margin-bottom: 6px; }}
    .hint {{ color:#666; margin-bottom: 18px; }}
    textarea {{ width: 100%; min-height: 70vh; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 14px; line-height: 1.45; padding: 12px; box-sizing: border-box; border-radius: 10px; border: 1px solid #ccc; background:white; }}
    .actions {{ margin-top: 12px; display:flex; gap:12px; }}
    button {{ padding: 10px 16px; border: 0; border-radius: 8px; background:#111; color:white; cursor:pointer; }}
    button.secondary {{ background:#555; }}
  </style>
</head>
<body>
  <h1>Xiaoniu Facts Manager</h1>
  <div class="hint">修改单一事实源 <code>facts.json</code>，保存后会自动执行 <code>sync_support_assets.py</code>。</div>
  {msg_html}
  <form method="POST" action="/save">
    <textarea name="facts">{html.escape(facts_text)}</textarea>
    <div class="actions">
      <button type="submit">保存并同步</button>
      <button class="secondary" type="button" onclick="window.location.reload()">重新加载</button>
    </div>
  </form>
</body>
</html>'''
    return page.encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            self.send_error(404)
            return
        body = render_page()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != '/save':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8')
        form = parse_qs(raw)
        facts_text = form.get('facts', [''])[0]

        try:
            save_facts_text(facts_text)
            ok, output = run_sync()
            body = render_page('保存成功。\n\n' + output, error=not ok)
            status = 200 if ok else 500
        except Exception as e:
            body = render_page(f'保存失败：\n{e}', error=True)
            status = 400

        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == '__main__':
    server = HTTPServer((HOST, PORT), Handler)
    print(f'Facts manager running at http://{HOST}:{PORT}')
    server.serve_forever()
