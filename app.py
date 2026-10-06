# ============================================================
#   🔥 RIXOR PROXY — FULL SMART SYSTEM v2.0
#   Smart Force Join + UID Verify + Admin Panel + Help Button
# ============================================================

import os, json, time, random, string, threading, secrets, csv, io
from datetime import datetime
from flask import (Flask, request, jsonify, make_response,
                   redirect, Response)
import requests

# ================== ⚙️ CONFIG ==================
BOT_TOKEN   = "8727812348:AAG-3hPXAlrDP97EGStvVPUop6uHQGhf6KY"          # ← এখানে বসাও
CHANNEL_1   = "@rixorchate"
CHANNEL_2   = "@rixonevergiveup"
ADMIN_PASS  = "Rixor2.0"
SUPPORT_ID  = "rakibz4"                   # Help button → Telegram
DOMAIN      = "rixor.proxy.com"
PORT        = 3000

BG_IMAGE    = "https://i.ibb.co.com/HDKSr4Sz/Gemini-Generated-Image-1211e1211e1211e1.jpg"

settings = {
    "proxy_host":  "rixor.proxy.com",
    "proxy_port":  "8080",
    "proxy_user":  "rixor_user",
    "proxy_pass":  "rixor_pass_2024",
    "session_hours": 1,
    "notice": "",
}

DATA_FILE = "data.json"
# ==============================================

app = Flask(__name__)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

sessions = {}
stats = {"total_joins":0, "total_verifies":0, "active_sessions":0}
uid_logs = []
banned_users = []
banned_ips = []

def load_data():
    global stats, uid_logs, banned_users, banned_ips, settings
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                stats = d.get("stats", stats)
                uid_logs = d.get("uid_logs", [])
                banned_users = d.get("banned_users", [])
                banned_ips = d.get("banned_ips", [])
                settings.update(d.get("settings", {}))
        except Exception as e:
            print("Load error:", e)

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "stats": stats,
                "uid_logs": uid_logs[-1000:],
                "banned_users": banned_users,
                "banned_ips": banned_ips,
                "settings": settings
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Save error:", e)

load_data()

_cache = {}
def is_member(user_id, channel):
    key = (str(user_id), channel)
    now = time.time()
    if key in _cache:
        res, ts = _cache[key]
        if now - ts < 30:
            return res
    try:
        r = requests.get(f"{TELEGRAM_API}/getChatMember",
            params={"chat_id": channel, "user_id": user_id},
            timeout=8).json()
        ok = r.get("ok") and r["result"]["status"] in (
            "member", "administrator", "creator")
        _cache[key] = (ok, now)
        return ok
    except Exception as e:
        print("Member error:", e)
        return False

_hits = {}
def rate_limited(ip, limit=20, window=60):
    now = time.time()
    h = [t for t in _hits.get(ip, []) if now - t < window]
    h.append(now)
    _hits[ip] = h
    return len(h) > limit

def get_ip():
    return request.headers.get("X-Forwarded-For",
        request.remote_addr).split(",")[0].strip()

def cleaner():
    while True:
        now_ms = int(time.time() * 1000)
        dead = [k for k, v in sessions.items() if v["expiresAt"] < now_ms]
        for k in dead:
            sessions.pop(k, None)
        stats["active_sessions"] = len(sessions)
        time.sleep(30)

threading.Thread(target=cleaner, daemon=True).start()

ADMIN_SESSIONS = {}
LOGIN_ATTEMPTS = {}
ADMIN_TIMEOUT = 30 * 60
MAX_ATTEMPTS = 5
BLOCK_TIME = 15 * 60

def is_blocked(ip):
    now = time.time()
    a = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < BLOCK_TIME]
    LOGIN_ATTEMPTS[ip] = a
    return len(a) >= MAX_ATTEMPTS

def record_fail(ip):
    LOGIN_ATTEMPTS.setdefault(ip, []).append(time.time())

def check_admin():
    token = request.cookies.get("admin_token")
    if not token: return False
    exp = ADMIN_SESSIONS.get(token)
    if not exp or time.time() > exp:
        ADMIN_SESSIONS.pop(token, None)
        return False
    ADMIN_SESSIONS[token] = time.time() + ADMIN_TIMEOUT
    return True

# ============================================================
#                    🎨 STYLES
# ============================================================

BASE_CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%}}
body{{
font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
background:url('{BG_IMAGE}') no-repeat center center fixed;
background-size:cover;color:#fff;
display:flex;justify-content:center;align-items:center;
min-height:100vh;padding:20px;position:relative;overflow-x:hidden;
}}
body::before{{
content:'';position:absolute;inset:0;
background:linear-gradient(135deg,rgba(0,20,40,.78),rgba(10,0,30,.88));
z-index:0;
}}
.card{{
position:relative;z-index:1;
background:rgba(15,20,35,.78);
backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
padding:36px 32px;border-radius:24px;
max-width:440px;width:100%;
box-shadow:0 25px 60px rgba(0,0,0,.8),
           0 0 0 1px rgba(0,217,255,.15) inset;
border:1px solid rgba(0,217,255,.2);
animation:fadeUp .6s ease;
}}
@keyframes fadeUp{{
from{{opacity:0;transform:translateY(30px)}}
to{{opacity:1;transform:translateY(0)}}
}}
h1,h2{{
text-align:center;
background:linear-gradient(135deg,#00d9ff,#7c3aed);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
background-clip:text;font-weight:800;letter-spacing:.5px;
}}
h2{{font-size:26px;margin-bottom:6px}}
.sub{{text-align:center;font-size:14px;color:#9ca3af;
margin-bottom:22px;line-height:1.5}}
input,button,select,textarea{{
width:100%;padding:15px 16px;margin-top:12px;
border-radius:14px;border:none;font-size:15px;
font-family:inherit;transition:all .25s;
}}
input,select,textarea{{
background:rgba(0,0,0,.5);color:#fff;
border:1.5px solid rgba(255,255,255,.12);outline:none;
}}
input::placeholder,textarea::placeholder{{color:#6b7280}}
input:focus,select:focus,textarea:focus{{
border-color:#00d9ff;
box-shadow:0 0 0 4px rgba(0,217,255,.15);
background:rgba(0,0,0,.6);
}}
button{{
background:linear-gradient(135deg,#00d9ff,#7c3aed);
color:#fff;font-weight:800;cursor:pointer;
font-size:15px;letter-spacing:.5px;
box-shadow:0 10px 25px rgba(0,217,255,.35);
}}
button:hover{{transform:translateY(-2px);
box-shadow:0 15px 32px rgba(124,58,237,.5)}}
button:active{{transform:translateY(0) scale(.98)}}
button:disabled{{opacity:.6;cursor:not-allowed;transform:none}}
.msg{{margin-top:16px;text-align:center;font-size:14px;
min-height:22px;font-weight:600}}
.ok{{color:#4ade80;text-shadow:0 0 12px rgba(74,222,128,.5)}}
.err{{color:#f87171;text-shadow:0 0 12px rgba(248,113,113,.5)}}
.info{{color:#60a5fa}}
.timer{{
font-size:48px;font-weight:900;
background:linear-gradient(135deg,#00d9ff,#7c3aed);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
font-family:'Courier New',monospace;
text-align:center;margin:22px 0;
filter:drop-shadow(0 0 15px rgba(0,217,255,.5));
letter-spacing:2px;
}}
.box{{
background:rgba(0,0,0,.55);padding:16px;border-radius:14px;
margin:12px 0;font-family:'Courier New',monospace;font-size:13px;
word-break:break-all;
border:1px solid rgba(0,217,255,.15);line-height:1.8;
}}
.box div{{display:flex;justify-content:space-between;gap:10px}}
.box .k{{color:#9ca3af}}
.box .v{{color:#00d9ff;font-weight:700}}
.label{{color:#6b7280;font-size:11px;text-transform:uppercase;
letter-spacing:1.5px;margin-top:16px;font-weight:700;}}
.hint{{font-size:11px;color:#4b5563;text-align:center;
margin-top:18px;line-height:1.6;}}
.badge{{
display:inline-block;padding:4px 10px;border-radius:20px;
font-size:11px;font-weight:700;letter-spacing:.5px;
background:rgba(0,217,255,.15);color:#00d9ff;
border:1px solid rgba(0,217,255,.3);margin-bottom:12px;
}}
.notice{{
background:linear-gradient(135deg,rgba(251,191,36,.2),rgba(245,158,11,.2));
border:1px solid rgba(251,191,36,.4);
padding:12px;border-radius:12px;margin-bottom:16px;
font-size:13px;color:#fbbf24;text-align:center;font-weight:600;
}}
@keyframes pulse{{
0%,100%{{transform:scale(1)}}
50%{{transform:scale(1.04)}}
}}

/* ===== 🆘 HELP BUTTON ===== */
.help-btn{{
position:fixed;bottom:24px;right:24px;z-index:9999;
width:60px;height:60px;border-radius:50%;
background:linear-gradient(135deg,#00d9ff,#7c3aed);
color:#fff;font-size:26px;font-weight:800;
display:flex;align-items:center;justify-content:center;
cursor:pointer;border:none;
box-shadow:0 10px 30px rgba(0,217,255,.5),
           0 0 0 1px rgba(255,255,255,.15) inset;
transition:all .3s cubic-bezier(.4,0,.2,1);
animation:helpPulse 2s infinite;
padding:0;margin:0;
}}
.help-btn:hover{{
transform:scale(1.1) rotate(10deg);
box-shadow:0 15px 40px rgba(124,58,237,.7);
animation:none;
}}
.help-btn.open{{transform:rotate(135deg);animation:none}}

@keyframes helpPulse{{
0%,100%{{box-shadow:0 10px 30px rgba(0,217,255,.5),
        0 0 0 0 rgba(0,217,255,.7)}}
50%{{box-shadow:0 10px 30px rgba(0,217,255,.5),
     0 0 0 18px rgba(0,217,255,0)}}
}}

.help-menu{{
position:fixed;bottom:100px;right:24px;z-index:9998;
background:rgba(15,20,35,.95);
backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
border:1px solid rgba(0,217,255,.25);
border-radius:20px;padding:16px;
min-width:240px;
box-shadow:0 20px 50px rgba(0,0,0,.7);
opacity:0;transform:translateY(20px) scale(.95);
pointer-events:none;
transition:all .3s cubic-bezier(.4,0,.2,1);
}}
.help-menu.open{{
opacity:1;transform:translateY(0) scale(1);
pointer-events:auto;
}}
.help-menu h4{{
color:#00d9ff;font-size:14px;margin-bottom:12px;
text-align:center;letter-spacing:.5px;
}}
.help-item{{
display:flex;align-items:center;gap:12px;
padding:12px 14px;border-radius:12px;
text-decoration:none;color:#fff;
transition:all .25s;margin-bottom:8px;
background:rgba(0,0,0,.3);
border:1px solid rgba(255,255,255,.05);
}}
.help-item:last-child{{margin-bottom:0}}
.help-item:hover{{
background:rgba(0,217,255,.15);
border-color:rgba(0,217,255,.4);
transform:translateX(5px);
}}
.help-item .ico{{
width:36px;height:36px;flex-shrink:0;
display:flex;align-items:center;justify-content:center;
background:linear-gradient(135deg,#00d9ff,#7c3aed);
border-radius:10px;font-size:18px;
}}
.help-item .txt{{flex:1;line-height:1.3}}
.help-item .txt b{{display:block;font-size:13px;font-weight:800}}
.help-item .txt span{{font-size:11px;color:#9ca3af}}

@media(max-width:600px){{
.help-btn{{width:54px;height:54px;font-size:24px;
bottom:18px;right:18px}}
.help-menu{{bottom:86px;right:18px;min-width:220px}}
}}
"""

JOIN_BTN_CSS = """
.chan{
display:flex;align-items:center;justify-content:space-between;gap:12px;
background:linear-gradient(135deg,#0088cc 0%,#00b0e0 50%,#00d9ff 100%);
background-size:200% 200%;color:#fff;padding:16px 20px;
border-radius:16px;margin:14px 0;text-decoration:none;
font-weight:700;font-size:15px;
transition:all .3s cubic-bezier(.4,0,.2,1);
box-shadow:0 10px 25px rgba(0,136,204,.4),
           0 0 0 1px rgba(255,255,255,.1) inset;
position:relative;overflow:hidden;
animation:slideIn .5s ease backwards;
}
.chan:nth-child(1){animation-delay:.1s}
.chan:nth-child(2){animation-delay:.2s}
.chan::before{
content:'';position:absolute;top:0;left:-120%;width:80%;height:100%;
background:linear-gradient(90deg,transparent,
rgba(255,255,255,.5),transparent);
transform:skewX(-20deg);transition:left .7s;
}
.chan:hover::before{left:130%}
.chan:hover{
transform:translateY(-4px) scale(1.02);
background-position:100% 50%;
box-shadow:0 18px 40px rgba(0,176,224,.6),
           0 0 0 1px rgba(255,255,255,.2) inset;
}
.chan:active{transform:translateY(-1px) scale(.99)}
.chan-icon{
width:38px;height:38px;flex-shrink:0;
display:flex;align-items:center;justify-content:center;
background:rgba(255,255,255,.2);border-radius:12px;font-size:20px;
box-shadow:0 4px 12px rgba(0,0,0,.2) inset;
}
.chan-text{flex:1;text-align:left;line-height:1.3}
.chan-text .title{font-size:15px;font-weight:800;display:block}
.chan-text .sub{font-size:11px;opacity:.85;
font-weight:500;color:#fff;margin:2px 0 0}
.chan-btn{
background:rgba(255,255,255,.25);padding:8px 16px;border-radius:20px;
font-size:12px;font-weight:800;letter-spacing:.5px;
box-shadow:0 4px 10px rgba(0,0,0,.15);
transition:all .25s;flex-shrink:0;
}
.chan:hover .chan-btn{
background:#fff;color:#0088cc;
box-shadow:0 6px 15px rgba(255,255,255,.4);
}
@keyframes slideIn{
from{opacity:0;transform:translateX(-30px)}
to{opacity:1;transform:translateX(0)}
}
"""

ADMIN_CSS = """
body{font-family:'Segoe UI',sans-serif;
background:linear-gradient(135deg,#0a0a1a,#1a0a2a);
color:#fff;padding:24px;margin:0;min-height:100vh}
.header{display:flex;justify-content:space-between;align-items:center;
max-width:1200px;margin:0 auto 24px;flex-wrap:wrap;gap:12px}
h1{background:linear-gradient(135deg,#00d9ff,#7c3aed);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;
font-size:28px;margin:0}
.logout,.nav-btn{background:linear-gradient(135deg,#ef4444,#dc2626);
color:#fff;padding:10px 22px;border-radius:10px;
text-decoration:none;font-weight:700;font-size:14px;
box-shadow:0 8px 20px rgba(239,68,68,.3);display:inline-block}
.nav-btn{background:linear-gradient(135deg,#00d9ff,#7c3aed);
box-shadow:0 8px 20px rgba(0,217,255,.3);margin-right:8px}
.logout:hover,.nav-btn:hover{transform:translateY(-2px)}
.tabs{display:flex;gap:8px;max-width:1200px;margin:0 auto 20px;flex-wrap:wrap}
.tab{background:rgba(20,20,40,.7);padding:12px 22px;border-radius:12px;
color:#9ca3af;text-decoration:none;font-weight:700;font-size:14px;
border:1px solid rgba(255,255,255,.08);transition:all .25s}
.tab:hover{color:#fff;border-color:rgba(0,217,255,.4)}
.tab.active{background:linear-gradient(135deg,#00d9ff,#7c3aed);
color:#fff;border:none;box-shadow:0 8px 20px rgba(0,217,255,.3)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
gap:14px;max-width:1200px;margin:0 auto 24px}
.stat{background:rgba(20,20,40,.7);padding:22px;
border-radius:16px;text-align:center;
border:1px solid rgba(0,217,255,.2);
box-shadow:0 8px 25px rgba(0,0,0,.4)}
.stat .n{font-size:34px;font-weight:900;
background:linear-gradient(135deg,#00d9ff,#7c3aed);
-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat .l{font-size:11px;color:#888;text-transform:uppercase;
letter-spacing:1.5px;font-weight:700;margin-top:4px}
.panel{max-width:1200px;margin:0 auto 20px;background:rgba(20,20,40,.7);
padding:24px;border-radius:16px;
border:1px solid rgba(0,217,255,.15);
box-shadow:0 10px 30px rgba(0,0,0,.5)}
.panel h3{margin:0 0 16px;color:#00d9ff;font-size:18px}
table{width:100%;border-collapse:collapse;background:rgba(20,20,40,.7);
border-radius:16px;overflow:hidden;
box-shadow:0 10px 30px rgba(0,0,0,.5);margin:0 auto}
th,td{padding:14px;text-align:left;
border-bottom:1px solid rgba(255,255,255,.05);font-size:14px}
th{background:linear-gradient(135deg,#00d9ff,#7c3aed);color:#fff;
font-weight:800;text-transform:uppercase;font-size:12px;
letter-spacing:1px}
tr:hover td{background:rgba(0,217,255,.05)}
.empty{text-align:center;color:#555;padding:40px}
.btn{padding:8px 14px;border-radius:8px;border:none;
font-weight:700;font-size:12px;cursor:pointer;
color:#fff;text-decoration:none;display:inline-block}
.btn-red{background:linear-gradient(135deg,#ef4444,#dc2626)}
.btn-blue{background:linear-gradient(135deg,#00d9ff,#7c3aed)}
.btn-green{background:linear-gradient(135deg,#4ade80,#22c55e)}
.search{display:flex;gap:10px;max-width:1200px;margin:0 auto 20px}
.search input{margin:0;flex:1}
.search button{width:auto;margin:0;padding:14px 28px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.form-grid input{margin-top:0}
@media(max-width:600px){.form-grid{grid-template-columns:1fr}}
"""

# ============================================================
#                    🆘 HELP BUTTON SNIPPET
# ============================================================

HELP_BUTTON = f"""
<div class="help-menu" id="helpMenu">
    <h4>🆘 Help & Support</h4>
    <a class="help-item" href="https://t.me/{SUPPORT_ID}" target="_blank">
        <div class="ico">💬</div>
        <div class="txt"><b>Telegram Support</b>
        <span>@{SUPPORT_ID}</span></div>
    </a>
    <a class="help-item" href="https://t.me/rixorchate" target="_blank">
        <div class="ico">📢</div>
        <div class="txt"><b>Main Channel</b>
        <span>Rixor Chat</span></div>
    </a>
    <a class="help-item" href="https://t.me/rixonevergiveup" target="_blank">
        <div class="ico">🚀</div>
        <div class="txt"><b>Backup Channel</b>
        <span>Never Give Up</span></div>
    </a>
</div>
<button class="help-btn" id="helpBtn" onclick="toggleHelp()">?</button>
<script>
function toggleHelp(){{
    const m=document.getElementById('helpMenu');
    const b=document.getElementById('helpBtn');
    m.classList.toggle('open');b.classList.toggle('open');
}}
document.addEventListener('click',function(e){{
    const m=document.getElementById('helpMenu');
    const b=document.getElementById('helpBtn');
    if(!m.contains(e.target)&&!b.contains(e.target)){{
        m.classList.remove('open');b.classList.remove('open');
    }}
}});
</script>
"""

def notice_html():
    if settings.get("notice"):
        return f'<div class="notice">📢 {settings["notice"]}</div>'
    return ""

# ============================================================
#                    📄 USER PAGES
# ============================================================

PAGE_JOIN = f"""<!DOCTYPE html><html lang="bn"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔐 Rixor Proxy Access</title>
<style>{BASE_CSS}</style>
<style>{JOIN_BTN_CSS}</style></head><body>
<div class="card">
<div style="text-align:center"><span class="badge">🔐 SECURE ACCESS</span></div>
<h2>Rixor Proxy</h2>
<p class="sub" id="subtitle">Telegram ID দাও — চেক করবো তুমি join করা আছো কিনা</p>
{notice_html()}
<div id="joinSection">
  <a class="chan" href="https://t.me/CH1" target="_blank">
    <div class="chan-icon">📢</div>
    <div class="chan-text">
      <span class="title">Rixor Chat</span>
      <span class="sub">মেইন চ্যানেল — আপডেট পেতে</span>
    </div>
    <div class="chan-btn">JOIN →</div>
  </a>
  <a class="chan" href="https://t.me/CH2" target="_blank">
    <div class="chan-icon">🚀</div>
    <div class="chan-text">
      <span class="title">Rixor Never Give Up</span>
      <span class="sub">ব্যাকআপ চ্যানেল — নোটিসের জন্য</span>
    </div>
    <div class="chan-btn">JOIN →</div>
  </a>
</div>
<input id="tgId" placeholder="🆔 তোমার Telegram User ID"
inputmode="numeric" autocomplete="off">
<button id="btn" onclick="checkJoin()">🔍 Check & Continue</button>
<div class="msg" id="msg"></div>
<p class="hint">💡 Telegram ID পেতে <b>@userinfobot</b> এ মেসেজ দাও</p>
</div>
<script>
async function checkJoin(){{
const tgId=document.getElementById('tgId').value.trim();
const msg=document.getElementById('msg');
const btn=document.getElementById('btn');
const sub=document.getElementById('subtitle');
if(!tgId){{msg.className='msg err';msg.textContent='⚠️ Telegram ID দাও';return}}
btn.disabled=true;btn.textContent='⏳ Checking...';
msg.className='msg info';msg.textContent='⏳ চেক করা হচ্ছে...';
sub.textContent='Bot যাচাই করছে...';
try{{
const r=await fetch('/api/check-join',{{method:'POST',
headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{tgId}})}});
const d=await r.json();
if(d.ok){{
  localStorage.setItem('tgId',tgId);
  msg.className='msg ok';
  msg.textContent='✅ তুমি আগে থেকেই join করা আছো!';
  sub.textContent='UID verify পেজে নিয়ে যাচ্ছি...';
  btn.textContent='✅ Verified — Redirecting...';
  setTimeout(()=>location.href='/verify',800);
}}
else{{
  msg.className='msg err';
  msg.textContent='❌ তুমি এখনো join করো নাই!';
  sub.innerHTML='উপরের <b>২টা চ্যানেল</b> join করে আবার চেষ্টা করো';
  btn.disabled=false;btn.textContent='🔄 আবার চেক করো';
  document.getElementById('joinSection').style.animation='pulse 1s ease 2';
}}
}}catch(e){{
  msg.className='msg err';msg.textContent='⚠️ সার্ভার সমস্যা';
  btn.disabled=false;btn.textContent='🔍 Check & Continue';
}}
}}
document.getElementById('tgId').addEventListener('keypress',
e=>{{if(e.key==='Enter')checkJoin()}});
</script>
{HELP_BUTTON}
</body></html>"""

PAGE_VERIFY = f"""<!DOCTYPE html><html lang="bn"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🎮 UID Verify</title><style>{BASE_CSS}</style></head><body>
<div class="card">
<div style="text-align:center"><span class="badge">🎮 STEP 2/2</span></div>
<h2>Free Fire UID</h2>
<p class="sub">তোমার Free Fire UID দাও<br>{settings['session_hours']} ঘণ্টার proxy access পাবে</p>
{notice_html()}
<input id="uid" placeholder="🆔 Free Fire UID (যেমন: 123456789)"
inputmode="numeric" autocomplete="off">
<button id="btn" onclick="verify()">🔓 Verify & Get Access</button>
<div class="msg" id="msg"></div>
<p class="hint">💡 Free Fire প্রোফাইল → UID কপি করো</p>
</div>
<script>
async function verify(){{
const uid=document.getElementById('uid').value.trim();
const tgId=localStorage.getItem('tgId');
const msg=document.getElementById('msg');const btn=document.getElementById('btn');
if(!tgId){{location.href='/';return}}
if(!uid||uid.length<6){{msg.className='msg err';
msg.textContent='⚠️ সঠিক UID দাও (৬+ ডিজিট)';return}}
btn.disabled=true;btn.textContent='⏳ Verifying...';
msg.className='msg info';msg.textContent='⏳ Verify হচ্ছে...';
try{{
const r=await fetch('/api/verify-uid',{{method:'POST',
headers:{{'Content-Type':'application/json'}},
body:JSON.stringify({{tgId,uid}})}});
const d=await r.json();
if(d.ok){{localStorage.setItem('token',d.token);
msg.className='msg ok';msg.textContent='✅ Verified!';
setTimeout(()=>location.href='/access',600)}}
else{{msg.className='msg err';msg.textContent='❌ '+d.msg;
btn.disabled=false;btn.textContent='🔓 Verify & Get Access'}}
}}catch(e){{msg.className='msg err';msg.textContent='⚠️ সার্ভার সমস্যা';
btn.disabled=false;btn.textContent='🔓 Verify & Get Access'}}
}}
document.getElementById('uid').addEventListener('keypress',
e=>{{if(e.key==='Enter')verify()}});
</script>
{HELP_BUTTON}
</body></html>"""

PAGE_ACCESS = f"""<!DOCTYPE html><html lang="bn"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>✅ Access Granted</title><style>{BASE_CSS}</style></head><body>
<div class="card">
<div style="text-align:center"><span class="badge">✅ ACCESS GRANTED</span></div>
<h2 style="background:linear-gradient(135deg,#4ade80,#00d9ff);
-webkit-background-clip:text;-webkit-text-fill-color:transparent">
সেশন সক্রিয়</h2>
<div class="timer" id="timer">{settings['session_hours']:02d}:00:00</div>
<div class="label">🎮 তোমার UID</div>
<div class="box"><div><span class="k">UID</span>
<span class="v" id="uidBox">...</span></div></div>
<div class="label">🌐 Proxy Server</div>
<div class="box" id="proxyBox">
<div><span class="k">Host</span><span class="v">{settings['proxy_host']}</span></div>
<div><span class="k">Port</span><span class="v">{settings['proxy_port']}</span></div>
<div><span class="k">User</span><span class="v">{settings['proxy_user']}</span></div>
<div><span class="k">Pass</span><span class="v">{settings['proxy_pass']}</span></div>
</div>
<button onclick="copyProxy()">📋 Copy Proxy Info</button>
<div class="msg" id="msg"></div>
<p class="hint">⏰ {settings['session_hours']} ঘণ্টা পর সেশন অটো শেষ হবে</p>
</div>
<script>
const token=localStorage.getItem('token');
if(!token)location.href='/';
let exp=0,timer,warned=false;
async function load(){{
try{{
const r=await fetch('/api/session/'+token);
const d=await r.json();
if(!d.ok){{alert('⏰ '+d.msg);localStorage.removeItem('token');
location.href='/';return}}
document.getElementById('uidBox').textContent=d.uid;
if(d.proxy){{
const p=d.proxy;
document.getElementById('proxyBox').innerHTML=
'<div><span class="k">Host</span><span class="v">'+p.host+'</span></div>'+
'<div><span class="k">Port</span><span class="v">'+p.port+'</span></div>'+
'<div><span class="k">User</span><span class="v">'+p.user+'</span></div>'+
'<div><span class="k">Pass</span><span class="v">'+p.pass+'</span></div>';}}
exp=d.expiresAt;tick();timer=setInterval(tick,1000);
}}catch(e){{alert('⚠️ সার্ভার সমস্যা');location.href='/'}}
}}
function tick(){{
const left=exp-Date.now();
if(left<=0){{clearInterval(timer);
document.getElementById('timer').textContent='00:00:00';
alert('⏰ সেশন শেষ! আবার verify করো।');
localStorage.removeItem('token');location.href='/';return}}
if(left<=120000&&!warned){{warned=true;
const m=document.getElementById('msg');
m.className='msg err';
m.textContent='⚠️ আর ২ মিনিট বাকি!';}}
const h=Math.floor(left/3600000),m=Math.floor((left%3600000)/60000),
s=Math.floor((left%60000)/1000);
document.getElementById('timer').textContent=
String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+
String(s).padStart(2,'0');}}
function copyProxy(){{
const p=document.getElementById('proxyBox').innerText;
navigator.clipboard.writeText(p).then(()=>{{
const m=document.getElementById('msg');
m.className='msg ok';m.textContent='✅ Copy হয়েছে!';
setTimeout(()=>m.textContent='',1500)}})}}
load();
</script>
{HELP_BUTTON}
</body></html>"""

# ============================================================
#                    🛣️ USER ROUTES
# ============================================================

@app.route("/")
def home():
    ip = get_ip()
    if ip in banned_ips:
        return "<h2 style='color:#f87171;text-align:center;margin-top:100px;font-family:sans-serif'>🚫 তোমার IP ব্লক</h2>", 403
    return (PAGE_JOIN
            .replace("CH1", CHANNEL_1.replace("@",""))
            .replace("CH2", CHANNEL_2.replace("@","")))

@app.route("/verify")
def verify_page(): return PAGE_VERIFY

@app.route("/access")
def access_page(): return PAGE_ACCESS

@app.route("/api/check-join", methods=["POST"])
def api_check_join():
    ip = get_ip()
    if ip in banned_ips:
        return jsonify(ok=False, msg="তোমার IP ব্লক"), 403
    if rate_limited(ip):
        return jsonify(ok=False, msg="অনেকবার চেষ্টা, ১ মিনিট পর"), 429
    d = request.get_json() or {}
    tg = str(d.get("tgId","")).strip()
    if not tg or not tg.isdigit():
        return jsonify(ok=False, msg="সঠিক Telegram ID দাও"), 400
    if tg in banned_users:
        return jsonify(ok=False, msg="তোমার অ্যাকাউন্ট ব্লক"), 403
    a = is_member(tg, CHANNEL_1)
    b = is_member(tg, CHANNEL_2)
    if a and b:
        stats["total_joins"] += 1; save_data()
        return jsonify(ok=True, msg="সব চ্যানেলে join করা আছে")
    miss = []
    if not a: miss.append("Rixor Chat")
    if not b: miss.append("Never Give Up")
    return jsonify(ok=False, msg=f"join করো: {', '.join(miss)}")

@app.route("/api/verify-uid", methods=["POST"])
def api_verify_uid():
    ip = get_ip()
    if ip in banned_ips:
        return jsonify(ok=False, msg="তোমার IP ব্লক"), 403
    if rate_limited(ip):
        return jsonify(ok=False, msg="অনেকবার চেষ্টা, ১ মিনিট পর"), 429
    d = request.get_json() or {}
    tg = str(d.get("tgId","")).strip()
    uid = str(d.get("uid","")).strip()
    if not tg or not uid:
        return jsonify(ok=False, msg="UID দাও"), 400
    if tg in banned_users:
        return jsonify(ok=False, msg="তোমার অ্যাকাউন্ট ব্লক"), 403
    if not uid.isdigit() or not (6 <= len(uid) <= 12):
        return jsonify(ok=False, msg="সঠিক Free Fire UID দাও"), 400
    if not (is_member(tg, CHANNEL_1) and is_member(tg, CHANNEL_2)):
        return jsonify(ok=False, msg="আগে দুইটা চ্যানেল join করো"), 403
    tk = "RX" + "".join(random.choices(string.ascii_uppercase+string.digits, k=18))
    now_ms = int(time.time()*1000)
    exp = now_ms + settings["session_hours"]*60*60*1000
    sessions[tk] = {"tgId":tg,"uid":uid,"expiresAt":exp,"createdAt":now_ms}
    stats["total_verifies"] += 1
    stats["active_sessions"] = len(sessions)
    uid_logs.append({"tgId":tg,"uid":uid,
        "time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip":ip})
    save_data()
    return jsonify(ok=True, token=tk, expiresAt=exp)

@app.route("/api/session/<token>")
def api_session(token):
    s = sessions.get(token)
    if not s:
        return jsonify(ok=False, msg="Invalid token")
    if int(time.time()*1000) > s["expiresAt"]:
        sessions.pop(token, None)
        return jsonify(ok=False, msg="সেশন শেষ, আবার verify করো")
    return jsonify(ok=True, uid=s["uid"], expiresAt=s["expiresAt"],
        proxy={
            "host":settings["proxy_host"], "port":settings["proxy_port"],
            "user":settings["proxy_user"], "pass":settings["proxy_pass"]
        })

# ============================================================
#                    👑 ADMIN
# ============================================================

@app.route("/admin", methods=["GET","POST"])
def admin():
    ip = get_ip()
    if request.method == "GET" and check_admin():
        return redirect("/admin/dashboard")
    if is_blocked(ip):
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
        <title>Blocked</title><style>{BASE_CSS}</style></head><body>
        <div class="card"><h2>🚫 Blocked</h2>
        <p class="sub" style="color:#f87171">
        অনেকবার ভুল পাসওয়ার্ড!<br>১৫ মিনিট পর চেষ্টা।</p>
        </div></body></html>""", 429
    if request.method == "POST":
        pwd = request.form.get("pass","")
        if pwd == ADMIN_PASS:
            LOGIN_ATTEMPTS.pop(ip, None)
            tk = secrets.token_urlsafe(32)
            ADMIN_SESSIONS[tk] = time.time() + ADMIN_TIMEOUT
            resp = make_response(redirect("/admin/dashboard"))
            resp.set_cookie("admin_token", tk,
                max_age=ADMIN_TIMEOUT, httponly=True, samesite="Lax")
            return resp
        else:
            record_fail(ip)
            left = MAX_ATTEMPTS - len(LOGIN_ATTEMPTS.get(ip, []))
            return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
            <title>Login</title><style>{BASE_CSS}</style></head><body>
            <div class="card"><h2>👑 Admin</h2>
            <p class="sub" style="color:#f87171">
            ❌ ভুল পাসওয়ার্ড!<br>আর {left} বার।</p>
            <form method="POST">
            <input type="password" name="pass" placeholder="🔑 Password"
            required autofocus>
            <button type="submit">🔓 Login</button>
            </form></div></body></html>""", 401
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>👑 Admin Login</title><style>{BASE_CSS}</style></head><body>
    <div class="card">
    <div style="text-align:center"><span class="badge">👑 ADMIN</span></div>
    <h2>Admin Login</h2>
    <p class="sub">শুধুমাত্র অ্যাডমিনের জন্য</p>
    <form method="POST">
    <input type="password" name="pass" placeholder="🔑 Password"
    required autofocus>
    <button type="submit">🔓 Login</button>
    </form>
    <p class="hint">🔒 সুরক্ষিত লগইন</p>
    </div></body></html>"""

@app.route("/admin/logout")
def admin_logout():
    tk = request.cookies.get("admin_token")
    if tk: ADMIN_SESSIONS.pop(tk, None)
    resp = make_response(redirect("/admin"))
    resp.delete_cookie("admin_token")
    return resp

def admin_header(active="dashboard"):
    tabs = [("dashboard","📊 Dashboard"),("logs","📋 UID Logs"),
            ("bans","🚫 Bans"),("settings","⚙️ Settings")]
    t = ""
    for k,l in tabs:
        c = "tab active" if k==active else "tab"
        t += f'<a class="{c}" href="/admin/{k}">{l}</a>'
    return f"""
    <div class="header">
        <h1>👑 Rixor Admin</h1>
        <div>
            <a class="nav-btn" href="/" target="_blank">🌐 Site</a>
            <a class="logout" href="/admin/logout">🚪 Logout</a>
        </div>
    </div>
    <div class="tabs">{t}</div>
    """

def admin_stats():
    now = int(time.time()*1000)
    active = sum(1 for s in sessions.values() if s["expiresAt"]>now)
    return f"""
    <div class="stats">
        <div class="stat"><div class="n">{stats['total_joins']}</div>
        <div class="l">Total Joins</div></div>
        <div class="stat"><div class="n">{stats['total_verifies']}</div>
        <div class="l">Verifies</div></div>
        <div class="stat"><div class="n">{active}</div>
        <div class="l">Active Now</div></div>
        <div class="stat"><div class="n">{len(uid_logs)}</div>
        <div class="l">Total UID</div></div>
        <div class="stat"><div class="n">{len(banned_users)}</div>
        <div class="l">Banned Users</div></div>
        <div class="stat"><div class="n">{len(banned_ips)}</div>
        <div class="l">Banned IPs</div></div>
    </div>"""

def admin_page(content, active="dashboard"):
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>👑 Admin</title><style>{ADMIN_CSS}</style></head><body>
    {admin_header(active)}{admin_stats()}{content}
    </body></html>"""

@app.route("/admin/dashboard")
def admin_dashboard():
    if not check_admin(): return redirect("/admin")
    rows = ""
    for lg in reversed(uid_logs[-20:]):
        rows += f"""<tr>
        <td>{lg['tgId']}</td>
        <td><b style="color:#00d9ff">{lg['uid']}</b></td>
        <td>{lg['time']}</td><td>{lg.get('ip','-')}</td>
        <td><a class="btn btn-red"
        href="/admin/ban_user?tg={lg['tgId']}">Ban User</a>
        <a class="btn btn-red"
        href="/admin/ban_ip?ip={lg.get('ip','')}">Ban IP</a></td>
        </tr>"""
    content = f"""<div class="panel">
    <h3>🕐 Recent Activity (শেষ ২০টি)</h3>
    <table><tr><th>Telegram ID</th><th>Free Fire UID</th>
    <th>Time</th><th>IP</th><th>Actions</th></tr>
    {rows or '<tr><td colspan=5 class="empty">কোনো ডেটা নেই</td></tr>'}
    </table></div>"""
    return admin_page(content, "dashboard")

@app.route("/admin/logs")
def admin_logs():
    if not check_admin(): return redirect("/admin")
    q = request.args.get("q","").strip()
    filtered = uid_logs
    if q:
        filtered = [l for l in uid_logs
                    if q in str(l['tgId']) or q in str(l['uid'])
                    or q in l.get('ip','')]
    rows = ""
    for lg in reversed(filtered[-200:]):
        rows += f"""<tr>
        <td>{lg['tgId']}</td>
        <td><b style="color:#00d9ff">{lg['uid']}</b></td>
        <td>{lg['time']}</td><td>{lg.get('ip','-')}</td>
        <td><a class="btn btn-red"
        href="/admin/ban_user?tg={lg['tgId']}">Ban</a></td>
        </tr>"""
    content = f"""
    <div class="search">
        <form method="GET" action="/admin/logs"
        style="display:flex;gap:10px;width:100%">
            <input name="q" value="{q}"
            placeholder="🔍 Telegram ID / UID / IP">
            <button type="submit">🔍 Search</button>
        </form>
        <a class="btn btn-green" href="/admin/export"
        style="padding:14px 28px;white-space:nowrap">📥 CSV</a>
    </div>
    <table><tr><th>Telegram ID</th><th>Free Fire UID</th>
    <th>Time</th><th>IP</th><th>Action</th></tr>
    {rows or '<tr><td colspan=5 class="empty">কোনো লগ নেই</td></tr>'}
    </table>"""
    return admin_page(content, "logs")

@app.route("/admin/export")
def admin_export():
    if not check_admin(): return redirect("/admin")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Telegram ID","Free Fire UID","Time","IP"])
    for lg in uid_logs:
        writer.writerow([lg['tgId'], lg['uid'], lg['time'], lg.get('ip','')])
    return Response(output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition":"attachment; filename=rixor_logs.csv"})

@app.route("/admin/bans")
def admin_bans():
    if not check_admin(): return redirect("/admin")
    ur = ""
    for u in banned_users:
        ur += f"""<tr><td>{u}</td><td><a class="btn btn-green"
        href="/admin/unban_user?tg={u}">Unban</a></td></tr>"""
    ir = ""
    for i in banned_ips:
        ir += f"""<tr><td>{i}</td><td><a class="btn btn-green"
        href="/admin/unban_ip?ip={i}">Unban</a></td></tr>"""
    content = f"""
    <div class="panel" style="margin-bottom:20px">
    <h3>🚫 Ban User</h3>
    <form method="POST" action="/admin/ban_user"
    style="display:flex;gap:10px">
    <input name="tg" placeholder="Telegram ID" required>
    <button type="submit" style="width:auto;padding:0 30px">Ban</button>
    </form></div>
    <div class="panel" style="margin-bottom:20px">
    <h3>🚫 Ban IP</h3>
    <form method="POST" action="/admin/ban_ip"
    style="display:flex;gap:10px">
    <input name="ip" placeholder="IP Address" required>
    <button type="submit" style="width:auto;padding:0 30px">Ban</button>
    </form></div>
    <div class="panel" style="margin-bottom:20px">
    <h3>🚫 Banned Users ({len(banned_users)})</h3>
    <table><tr><th>Telegram ID</th><th>Action</th></tr>
    {ur or '<tr><td colspan=2 class="empty">কেউ ব্লক নেই</td></tr>'}
    </table></div>
    <div class="panel">
    <h3>🚫 Banned IPs ({len(banned_ips)})</h3>
    <table><tr><th>IP Address</th><th>Action</th></tr>
    {ir or '<tr><td colspan=2 class="empty">কোনো IP ব্লক নেই</td></tr>'}
    </table></div>"""
    return admin_page(content, "bans")

@app.route("/admin/ban_user", methods=["GET","POST"])
def admin_ban_user():
    if not check_admin(): return redirect("/admin")
    tg = request.args.get("tg") or request.form.get("tg","")
    if tg and tg not in banned_users:
        banned_users.append(tg); save_data()
    return redirect("/admin/bans")

@app.route("/admin/unban_user")
def admin_unban_user():
    if not check_admin(): return redirect("/admin")
    tg = request.args.get("tg","")
    if tg in banned_users:
        banned_users.remove(tg); save_data()
    return redirect("/admin/bans")

@app.route("/admin/ban_ip", methods=["GET","POST"])
def admin_ban_ip():
    if not check_admin(): return redirect("/admin")
    ip = request.args.get("ip") or request.form.get("ip","")
    if ip and ip not in banned_ips:
        banned_ips.append(ip); save_data()
    return redirect("/admin/bans")

@app.route("/admin/unban_ip")
def admin_unban_ip():
    if not check_admin(): return redirect("/admin")
    ip = request.args.get("ip","")
    if ip in banned_ips:
        banned_ips.remove(ip); save_data()
    return redirect("/admin/bans")

@app.route("/admin/settings", methods=["GET","POST"])
def admin_settings():
    if not check_admin(): return redirect("/admin")
    if request.method == "POST":
        settings["proxy_host"] = request.form.get("proxy_host","").strip()
        settings["proxy_port"] = request.form.get("proxy_port","").strip()
        settings["proxy_user"] = request.form.get("proxy_user","").strip()
        settings["proxy_pass"] = request.form.get("proxy_pass","").strip()
        try:
            settings["session_hours"] = int(request.form.get("session_hours",1))
        except: pass
        settings["notice"] = request.form.get("notice","").strip()
        save_data()
        return redirect("/admin/settings")
    content = f"""
    <div class="panel">
    <h3>⚙️ Proxy Settings</h3>
    <form method="POST">
    <div class="form-grid">
    <input name="proxy_host" value="{settings['proxy_host']}"
    placeholder="Proxy Host">
    <input name="proxy_port" value="{settings['proxy_port']}"
    placeholder="Proxy Port">
    <input name="proxy_user" value="{settings['proxy_user']}"
    placeholder="Proxy User">
    <input name="proxy_pass" value="{settings['proxy_pass']}"
    placeholder="Proxy Password">
    </div>
    <h3 style="margin-top:24px">⏰ Session Hours</h3>
    <input name="session_hours" type="number" min="1" max="24"
    value="{settings['session_hours']}">
    <h3 style="margin-top:24px">📢 Notice</h3>
    <textarea name="notice" rows="3"
    placeholder="খালি রাখলে notice দেখাবে না">{settings['notice']}</textarea>
    <button type="submit" style="margin-top:20px">💾 Save</button>
    </form></div>
    <div class="panel" style="margin-top:20px">
    <h3>🔄 Quick Actions</h3>
    <a class="btn btn-red" href="/admin/clear_sessions"
    onclick="return confirm('সব session মুছবে?')">🗑️ Clear Sessions</a>
    <a class="btn btn-blue" href="/admin/clear_logs"
    onclick="return confirm('সব log মুছবে?')">🗑️ Clear Logs</a>
    <a class="btn btn-green" href="/admin/export">📥 Export CSV</a>
    </div>"""
    return admin_page(content, "settings")

@app.route("/admin/clear_sessions")
def admin_clear_sessions():
    if not check_admin(): return redirect("/admin")
    sessions.clear(); save_data()
    return redirect("/admin/settings")

@app.route("/admin/clear_logs")
def admin_clear_logs():
    if not check_admin(): return redirect("/admin")
    uid_logs.clear(); save_data()
    return redirect("/admin/settings")

# ============================================================
#                    🚀 RUN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 RIXOR PROXY v2.0 — Full System")
    print(f"🌐 Site:     https://{DOMAIN}")
    print(f"👑 Admin:    https://{DOMAIN}/admin")
    print(f"🔑 Pass:     {ADMIN_PASS}")
    print(f"💬 Support:  @{SUPPORT_ID}")
    print(f"📢 Channel1: {CHANNEL_1}")
    print(f"📢 Channel2: {CHANNEL_2}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=PORT, debug=False)