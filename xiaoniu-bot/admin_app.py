import html
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
FACTS_PATH = BASE_DIR / 'facts.json'
SYNC_SCRIPT = BASE_DIR / 'sync_support_assets.py'
RESTART_BOT_SCRIPT = BASE_DIR / 'restart_bot.sh'
ADMIN_USERNAME = os.getenv('FACTS_ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('FACTS_ADMIN_PASSWORD', 'changeme')
SESSION_SECRET = os.getenv('FACTS_ADMIN_SESSION_SECRET', 'change-this-secret')

app = FastAPI(title='Xiaoniu Facts Admin')
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)


def load_facts() -> dict:
    return json.loads(FACTS_PATH.read_text(encoding='utf-8'))


def load_facts_text() -> str:
    return FACTS_PATH.read_text(encoding='utf-8')


def save_facts(data: dict) -> None:
    FACTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save_facts_text(text: str) -> None:
    parsed = json.loads(text)
    save_facts(parsed)


def run_sync() -> tuple[bool, str]:
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


def restart_bot() -> tuple[bool, str]:
    result = subprocess.run(
        ['bash', str(RESTART_BOT_SCRIPT)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = (result.stdout or '') + (result.stderr or '')
    return result.returncode == 0, output.strip() or 'bot restart finished'


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get('logged_in'))


def require_login(request: Request) -> Optional[RedirectResponse]:
    if not is_logged_in(request):
        return RedirectResponse('/admin/login', status_code=303)
    return None


def render_layout(title: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin:0; font-family:system-ui,-apple-system,sans-serif; background:#f6f7fb; color:#222; }}
    .shell {{ display:flex; min-height:100vh; }}
    .nav {{ width:240px; background:#111827; color:#fff; padding:24px 16px; box-sizing:border-box; }}
    .nav h1 {{ font-size:18px; margin:0 0 20px; }}
    .nav a {{ display:block; color:#d1d5db; text-decoration:none; padding:10px 12px; border-radius:8px; margin-bottom:6px; }}
    .nav a:hover {{ background:#1f2937; color:#fff; }}
    .main {{ flex:1; padding:24px; box-sizing:border-box; }}
    .card {{ background:#fff; border-radius:14px; padding:20px; box-shadow:0 4px 18px rgba(0,0,0,0.06); }}
    .hint {{ color:#666; margin:6px 0 18px; }}
    textarea {{ width:100%; min-height:65vh; padding:12px; box-sizing:border-box; border-radius:10px; border:1px solid #ccc; font-family:ui-monospace,monospace; font-size:14px; line-height:1.45; }}
    input {{ width:100%; padding:10px 12px; margin:8px 0 14px; box-sizing:border-box; border-radius:10px; border:1px solid #ccc; }}
    button {{ border:0; border-radius:10px; background:#111827; color:#fff; padding:10px 16px; cursor:pointer; }}
    .msg {{ margin:12px 0; padding:12px; border-radius:10px; background:#f3f4f6; white-space:pre-wrap; }}
    .ok {{ color:#166534; }}
    .err {{ color:#b91c1c; }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="nav">
      <h1>Xiaoniu Admin</h1>
      <a href="/admin">Dashboard</a>
      <a href="/admin/facts">Facts 编辑</a>
      <a href="/admin/sync">同步结果</a>
      <a href="/admin/logout">退出登录</a>
    </aside>
    <main class="main">
      {body}
    </main>
  </div>
</body>
</html>'''


@app.get('/admin/login', response_class=HTMLResponse)
def login_page(error: str = ''):
    msg = f'<div class="msg err">{html.escape(error)}</div>' if error else ''
    body = f'''
      <div class="card" style="max-width:480px;margin:40px auto;">
        <h2>登录 Facts 管理后台</h2>
        <div class="hint">这是第一版骨架，先用最简单的账号密码保护。</div>
        {msg}
        <form method="post" action="/admin/login">
          <label>用户名</label>
          <input name="username" autocomplete="username" />
          <label>密码</label>
          <input type="password" name="password" autocomplete="current-password" />
          <button type="submit">登录</button>
        </form>
      </div>
    '''
    return render_layout('Facts Admin Login', body)


@app.post('/admin/login')
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session['logged_in'] = True
        return RedirectResponse('/admin', status_code=303)
    return RedirectResponse('/admin/login?error=用户名或密码错误', status_code=303)


@app.get('/admin/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/admin/login', status_code=303)


@app.get('/admin', response_class=HTMLResponse)
def dashboard(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    body = '''
      <div class="card">
        <h2>Dashboard</h2>
        <div class="hint">第一版骨架已就位：单一事实源 + 手动同步。</div>
        <ul>
          <li><strong>Facts 编辑</strong>：直接编辑 <code>facts.json</code></li>
          <li><strong>同步</strong>：执行 <code>sync_support_assets.py</code></li>
          <li><strong>重启 Bot</strong>：调用 <code>restart_bot.sh</code></li>
          <li>下一步可继续扩成分区表单、测试结果页、diff 预览</li>
        </ul>
        <form method="post" action="/admin/bot/restart" style="margin-top:16px;">
          <button type="submit">重启 bot.py</button>
        </form>
      </div>
    '''
    return render_layout('Dashboard', body)


@app.get('/admin/facts', response_class=HTMLResponse)
def facts_page(request: Request, message: str = '', error: str = ''):
    redirect = require_login(request)
    if redirect:
        return redirect
    msg_html = ''
    if message:
        msg_html += f'<div class="msg ok">{html.escape(message)}</div>'
    if error:
        msg_html += f'<div class="msg err">{html.escape(error)}</div>'

    facts = load_facts()
    product = facts['product']
    ios = facts['platforms']['ios']
    windows = facts['platforms']['windows']
    mac = facts['platforms']['mac']
    vip = facts['vip']
    multi = facts['multiDevice']
    recommended = '\n'.join(facts['recommendedRegions'])

    body = f'''
      <div class="card">
        <h2>Facts 编辑</h2>
        <div class="hint">第一版分区表单：常改内容先拆出来，保存后自动同步到其他文件。</div>
        {msg_html}
        <form method="post" action="/admin/facts/save-form">
          <h3>产品定位</h3>
          <label>产品名称</label>
          <input name="product_name" value="{html.escape(product['name'])}" />
          <label>产品定位</label>
          <input name="product_positioning" value="{html.escape(product['positioning'])}" />
          <label>稳定运行起始年份</label>
          <input name="product_stable_since" value="{html.escape(product['stableSince'])}" />
          <label>产品用途简介</label>
          <textarea name="product_summary" style="min-height:120px;">{html.escape(product['summary'])}</textarea>

          <h3>通用推荐节点</h3>
          <label>每行一个节点</label>
          <textarea name="recommended_regions" style="min-height:120px;">{html.escape(recommended)}</textarea>

          <h3>iPhone / iOS</h3>
          <label>分发方式</label>
          <input name="ios_distribution" value="{html.escape(ios['distribution'])}" />
          <label>下载链接</label>
          <input name="ios_download_url" value="{html.escape(ios['downloadUrl'])}" />
          <label>上架说明</label>
          <textarea name="ios_store_release_note" style="min-height:100px;">{html.escape(ios['storeReleaseNote'])}</textarea>

          <h3>Windows</h3>
          <label>最低支持版本</label>
          <input name="windows_min_version" value="{html.escape(windows['minVersion'])}" />
          <label>下载链接</label>
          <input name="windows_download_url" value="{html.escape(windows['downloadUrl'])}" />
          <label>虚拟网卡名</label>
          <input name="windows_virtual_adapter" value="{html.escape(windows['virtualAdapter'])}" />

          <h3>Mac</h3>
          <label>版本号</label>
          <input name="mac_version" value="{html.escape(mac['version'])}" />
          <label>下载链接</label>
          <input name="mac_download_url" value="{html.escape(mac['downloadUrl'])}" />
          <label>虚拟网卡名</label>
          <input name="mac_virtual_adapter" value="{html.escape(mac['virtualAdapter'])}" />

          <h3>VIP / 免费 / 多设备</h3>
          <label>VIP 套餐说明</label>
          <textarea name="vip_plans_note" style="min-height:80px;">{html.escape(vip['plansNote'])}</textarea>
          <label>VIP 购买说明</label>
          <textarea name="vip_purchase_note" style="min-height:80px;">{html.escape(vip['purchaseUrlNote'])}</textarea>
          <label>VIP 权益</label>
          <textarea name="vip_benefits" style="min-height:80px;">{html.escape(vip['benefits'])}</textarea>
          <label>免费用户限制</label>
          <textarea name="vip_free_limit" style="min-height:80px;">{html.escape(vip['freeUserLimit'])}</textarea>
          <label>多设备同时在线数量</label>
          <input name="multi_device_max" value="{html.escape(str(multi['maxOnlineDevices']))}" />

          <div style="margin-top:16px;"><button type="submit">保存并同步</button></div>
        </form>

        <hr style="margin:24px 0;border:none;border-top:1px solid #eee;" />
        <details>
          <summary>高级模式：直接编辑原始 facts.json</summary>
          <form method="post" action="/admin/facts/save" style="margin-top:12px;">
            <textarea name="facts">{html.escape(load_facts_text())}</textarea>
            <div style="margin-top:12px;"><button type="submit">按原始 JSON 保存并同步</button></div>
          </form>
        </details>
      </div>
    '''
    return render_layout('Facts Editor', body)


@app.post('/admin/facts/save')
def facts_save(request: Request, facts: str = Form(...)):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        save_facts_text(facts)
        ok, output = run_sync()
        if ok:
            return RedirectResponse('/admin/facts?message=保存并同步成功', status_code=303)
        return RedirectResponse('/admin/facts?error=' + output, status_code=303)
    except Exception as e:
        return RedirectResponse('/admin/facts?error=' + str(e), status_code=303)


@app.post('/admin/facts/save-form')
def facts_save_form(
    request: Request,
    product_name: str = Form(...),
    product_positioning: str = Form(...),
    product_stable_since: str = Form(...),
    product_summary: str = Form(...),
    recommended_regions: str = Form(...),
    ios_distribution: str = Form(...),
    ios_download_url: str = Form(...),
    ios_store_release_note: str = Form(...),
    windows_min_version: str = Form(...),
    windows_download_url: str = Form(...),
    windows_virtual_adapter: str = Form(...),
    mac_version: str = Form(...),
    mac_download_url: str = Form(...),
    mac_virtual_adapter: str = Form(...),
    vip_plans_note: str = Form(...),
    vip_purchase_note: str = Form(...),
    vip_benefits: str = Form(...),
    vip_free_limit: str = Form(...),
    multi_device_max: str = Form(...),
):
    redirect = require_login(request)
    if redirect:
        return redirect
    try:
        facts = load_facts()
        facts['product']['name'] = product_name.strip()
        facts['product']['positioning'] = product_positioning.strip()
        facts['product']['stableSince'] = product_stable_since.strip()
        facts['product']['summary'] = product_summary.strip()
        facts['recommendedRegions'] = [line.strip() for line in recommended_regions.splitlines() if line.strip()]
        facts['platforms']['ios']['distribution'] = ios_distribution.strip()
        facts['platforms']['ios']['downloadUrl'] = ios_download_url.strip()
        facts['platforms']['ios']['storeReleaseNote'] = ios_store_release_note.strip()
        facts['platforms']['windows']['minVersion'] = windows_min_version.strip()
        facts['platforms']['windows']['downloadUrl'] = windows_download_url.strip()
        facts['platforms']['windows']['virtualAdapter'] = windows_virtual_adapter.strip()
        facts['platforms']['mac']['version'] = mac_version.strip()
        facts['platforms']['mac']['downloadUrl'] = mac_download_url.strip()
        facts['platforms']['mac']['virtualAdapter'] = mac_virtual_adapter.strip()
        facts['vip']['plansNote'] = vip_plans_note.strip()
        facts['vip']['purchaseUrlNote'] = vip_purchase_note.strip()
        facts['vip']['benefits'] = vip_benefits.strip()
        facts['vip']['freeUserLimit'] = vip_free_limit.strip()
        facts['multiDevice']['maxOnlineDevices'] = int(multi_device_max.strip())
        save_facts(facts)
        ok, output = run_sync()
        if ok:
            return RedirectResponse('/admin/facts?message=保存并同步成功', status_code=303)
        return RedirectResponse('/admin/facts?error=' + output, status_code=303)
    except Exception as e:
        return RedirectResponse('/admin/facts?error=' + str(e), status_code=303)


@app.get('/admin/sync', response_class=HTMLResponse)
def sync_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    ok, output = run_sync()
    body = f'''
      <div class="card">
        <h2>同步结果</h2>
        <div class="msg {'ok' if ok else 'err'}">{html.escape(output)}</div>
        <form method="get" action="/admin/sync">
          <button type="submit">重新执行同步</button>
        </form>
      </div>
    '''
    return render_layout('Sync Result', body)


@app.post('/admin/bot/restart', response_class=HTMLResponse)
def restart_bot_page(request: Request):
    redirect = require_login(request)
    if redirect:
        return redirect
    ok, output = restart_bot()
    body = f'''
      <div class="card">
        <h2>Bot 重启结果</h2>
        <div class="msg {'ok' if ok else 'err'}">{html.escape(output)}</div>
        <a href="/admin"><button>返回 Dashboard</button></a>
      </div>
    '''
    return render_layout('Bot Restart Result', body)
