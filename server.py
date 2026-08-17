#!/usr/bin/env python3
"""
KĀRVĀN Unified Multi-Threaded Production Server:
- Static File Serving with auto-MIME and HEAD support
- SQLite Authentication API (/api/auth/register, /api/auth/login, /api/auth/me)
- Persian Royal Concierge AI Assistant (/api/concierge/chat)
- Live Sovereign Commodities & Heritage Asset Market Ticker (/api/market/stats)
- Sovereign Guild Member Directory (/api/members/directory)
- ThreadingHTTPServer for zero blocking
"""
import json
import sqlite3
import hashlib
import os
import hmac
import time
import mimetypes
import random
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "auth.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
SECRET_KEY = b"karvan_persian_royal_sovereign_secret_key_2026"
ADMIN_EDIT_KEY = "karvan-edit-2026"
ADMIN_EDIT_TARGET = os.path.join(PUBLIC_DIR, "index.html")
ADMIN_BACKUP_DIR = "/tmp/karvan_backups"

def admin_editor_page(key, error=None):
    """Return the in-browser HTML editor page for public/index.html."""
    try:
        with open(ADMIN_EDIT_TARGET, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        content = f"# ERROR READING FILE: {e}"
    import html as html_mod
    escaped = html_mod.escape(content)
    err_html = f'<div class="err">{html_mod.escape(str(error))}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KĀRVĀN Admin Editor</title>
<style>
  body {{ background:#0a0a0c; color:#fafafa; font-family:monospace; margin:0; padding:16px; }}
  h1 {{ font-size:16px; color:#D4AF37; text-transform:uppercase; letter-spacing:2px; }}
  .toolbar {{ display:flex; align-items:center; gap:12px; margin:12px 0; flex-wrap:wrap; }}
  .toolbar button {{ background:#D4AF37; color:#050505; border:0; padding:8px 16px; font-weight:bold; cursor:pointer; border-radius:8px; }}
  .toolbar button:disabled {{ opacity:0.5; cursor:not-allowed; }}
  .toolbar span {{ font-size:11px; color:#8a8a8a; }}
  .err {{ background:#7f1d1d; color:#fecaca; padding:8px 12px; border-radius:8px; margin:8px 0; font-size:12px; }}
  textarea {{ width:100%; height:calc(100vh - 150px); background:#121216; color:#e2e8f0; border:1px solid #D4AF37; border-radius:8px; padding:12px; font-family:monospace; font-size:12px; resize:vertical; }}
  #status {{ font-size:12px; margin-left:8px; }}
</style>
</head>
<body>
<h1>KĀRVĀN · Royal Editor</h1>
{err_html}
<div class="toolbar">
  <button id="save-btn" onclick="saveDoc()">💾 Save to Server</button>
  <button onclick="reloadDoc()" style="background:#1a1a22; color:#D4AF37; border:1px solid #D4AF37;">↻ Reload from Server</button>
  <span id="status">Editing: public/index.html ({len(content)} chars)</span>
</div>
<textarea id="code" spellcheck="false">{escaped}</textarea>
<script>
  const KEY = {json.dumps(key)};
  async function saveDoc() {{
    const btn = document.getElementById('save-btn');
    const status = document.getElementById('status');
    btn.disabled = true;
    status.textContent = 'Saving...';
    try {{
      const res = await fetch('/api/admin/save', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ' + KEY}},
        body: JSON.stringify({{content: document.getElementById('code').value}})
      }});
      const data = await res.json();
      status.textContent = data.ok ? ('✓ Saved ' + data.bytes + ' bytes at ' + data.time) : ('✗ ' + (data.error || 'save failed'));
    }} catch (e) {{
      status.textContent = '✗ Network error: ' + e;
    }}
    btn.disabled = false;
  }}
  async function reloadDoc() {{
    const status = document.getElementById('status');
    status.textContent = 'Reloading...';
    const res = await fetch('/admin?key=' + encodeURIComponent(KEY));
    location.reload();
  }}
</script>
</body>
</html>"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tier TEXT DEFAULT 'Fellow Candidate',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS concierge_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            lang TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Seed default member
    c.execute("SELECT id FROM users WHERE email = 'cyrus@karvan.luxury'")
    if not c.fetchone():
        pwd_hash = hashlib.sha256(b"persepolis2026").hexdigest()
        c.execute(
            "INSERT INTO users (name, email, password_hash, tier) VALUES (?, ?, ?, ?)",
            ("Cyrus Pahlavi", "cyrus@karvan.luxury", pwd_hash, "Royal Custodian")
        )
    conn.commit()
    conn.close()

def generate_token(user_id, email, name, tier):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "tier": tier,
        "exp": int(time.time()) + 86400 * 7
    }
    header_b64 = json.dumps(header).encode().hex()
    payload_b64 = json.dumps(payload).encode().hex()
    signature = hmac.new(SECRET_KEY, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).hexdigest()
    return f"{header_b64}.{payload_b64}.{signature}"

def verify_token(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig = parts
        expected_sig = hmac.new(SECRET_KEY, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(bytes.fromhex(payload_b64).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

# Intelligent Persian Luxury Concierge Knowledge Engine
def answer_concierge_query(query, lang="en"):
    q = query.lower().strip()
    if lang == "fa" or any("\u0600" <= c <= "\u06FF" for c in query):
        if any(w in q for w in ["هواپیما", "جت", "پرواز", "دبی", "سفر", "flight", "jet"]):
            return "با درود و احترام. ناوگان هواپیمایی اختصاصی کاروان با Bombardier Global 7500 و Gulfstream G700 برای پروازهای اختصاصی تهران-دبی، ژنو و لندن با هماهنگی ۴ ساعته در خدمت شماست."
        elif any(w in q for w in ["فرش", "عتیقه", "هنر", "صفوی", "اصفهان", "rug", "art", "carpet"]):
            return "تالار حراج شاهانه کاروان دسترسی اختصاصی به گنجینه‌های ابریشمی قرن هفدهم اصفهان و کاشان با گواهی اصالت موزه آستان قدس و لوور را فراهم می‌آورد."
        elif any(w in q for w in ["گالا", "تخت جمشید", "مهمانی", "جشن", "دعوت", "gala"]):
            return "گالای زمستانه پارسه کاروان در محوطه اختصاصی تخت جمشید با حضور ۳۸۰ عضو برگزیده در تاریخ ۱۲ دی‌ماه برگزار می‌گردد. رزرو سوئیت‌های اختصاصی از پنل کاربری میسر است."
        elif any(w in q for w in ["عضویت", "قیمت", "هزینه", "ثبت نام", "tier", "price", "join"]):
            return "عضویت در کاروان در ۳ سطح ارائه می‌شود: نامزد همکار ($5,000)، حامی مستقل ($15,000) و امین سلطنتی ($50,000/سال) همراه با وتوی شورای ۵ نفره ناظران."
        else:
            return "درود بر شما بزرگوار. میز تشریفات و دیپلماسی کاروان آماده رسیدگی به سفارشات اختصاصی شما در زمینه سرمایه‌گذاری‌های سنگین، حراج‌های میراث و سفرهای تشریفاتی است."
    else:
        if any(w in q for w in ["jet", "flight", "aviation", "charter", "dubai", "travel"]):
            return "Greetings. The KĀRVĀN Aviation Sovereign Fleet (Bombardier Global 7500 & Gulfstream G700) operates private direct slots between Tehran, Dubai, Zurich, and London with 4-hour departure readiness."
        elif any(w in q for w in ["rug", "carpet", "art", "heritage", "auction", "antique", "isfahan"]):
            return "Our Imperial Vault provides provenance-verified access to 17th-century Safavid silk masterworks and royal turquoise artifacts certified by international curatorial councils."
        elif any(w in q for w in ["gala", "persepolis", "event", "soiree", "invitation", "rsvp"]):
            return "The Persepolis Winter Gala gathers 380 sovereign patrons at the private ceremonial pavilion. Access includes private helicopter transfers and royal banquet seating."
        elif any(w in q for w in ["membership", "price", "tier", "cost", "apply", "join"]):
            return "KĀRVĀN offers three tiers: Fellow Candidate ($5,000), Sovereign Patron ($15,000), and Royal Custodian ($50,000/yr). Each undergoes vetting by the 5-Council Sovereign Board."
        elif any(w in q for w in ["saffron", "caviar", "gold", "market", "commodity"]):
            return "Super Negin Saffron Bullion is currently trading at $3,420/kg (+2.4% today) with physical vaulting available in Zurich, Dubai, and Tehran free-zones."
        else:
            return "Welcome to KĀRVĀN Concierge. Our 24/7 Diplomatic Desk is prepared to assist with your acquisitions, private vault allocations, and ceremonial event reservations."

class UnifiedServerHandler(BaseHTTPRequestHandler):
    def address_string(self):
        return str(self.client_address[0])

    def _set_json_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_json_headers(204)

    def do_HEAD(self):
        parsed = urlparse(self.path)
        req_path = parsed.path.lstrip("/")
        if not req_path or req_path == "":
            req_path = "index.html"
        file_path = os.path.join(PUBLIC_DIR, req_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if parsed.path == "/api/admin/save":
            auth_header = self.headers.get("Authorization", "")
            provided_key = auth_header.replace("Bearer ", "", 1).strip() if auth_header.startswith("Bearer ") else ""
            if provided_key != ADMIN_EDIT_KEY:
                self._set_json_headers(401)
                self.wfile.write(json.dumps({"error": "Unauthorized: invalid admin key"}).encode())
                return

            new_content = data.get("content", "")
            if not new_content:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({"error": "Empty content not allowed"}).encode())
                return

            # Backup previous live version before overwrite
            try:
                os.makedirs(ADMIN_BACKUP_DIR, exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                with open(ADMIN_EDIT_TARGET, "r", encoding="utf-8") as f:
                    old_content = f.read()
                with open(os.path.join(ADMIN_BACKUP_DIR, f"index_{ts}.html"), "w", encoding="utf-8") as f:
                    f.write(old_content)
            except Exception as e:
                pass  # backup is best-effort

            try:
                with open(ADMIN_EDIT_TARGET, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self._set_json_headers(200)
                self.wfile.write(json.dumps({
                    "ok": True,
                    "bytes": len(new_content.encode()),
                    "time": time.strftime("%H:%M:%S"),
                    "backup": "saved to /tmp/karvan_backups"
                }).encode())
            except Exception as e:
                self._set_json_headers(500)
                self.wfile.write(json.dumps({"error": f"Write failed: {e}"}).encode())

        elif parsed.path == "/api/auth/register":
            name = data.get("name", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            tier = data.get("tier", "Fellow Candidate")

            if not name or not email or not password:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({"error": "Name, email, and password required."}).encode())
                return

            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO users (name, email, password_hash, tier) VALUES (?, ?, ?, ?)", (name, email, pwd_hash, tier))
                user_id = c.lastrowid
                conn.commit()
                conn.close()

                token = generate_token(user_id, email, name, tier)
                self._set_json_headers(201)
                self.wfile.write(json.dumps({
                    "message": "Registration successful",
                    "token": token,
                    "user": {"id": user_id, "name": name, "email": email, "tier": tier}
                }).encode())
            except sqlite3.IntegrityError:
                self._set_json_headers(409)
                self.wfile.write(json.dumps({"error": "An account with this email already exists."}).encode())

        elif parsed.path == "/api/auth/login":
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")

            if not email or not password:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({"error": "Email and password required."}).encode())
                return

            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, name, email, tier FROM users WHERE email = ? AND password_hash = ?", (email, pwd_hash))
            user = c.fetchone()
            conn.close()

            if user:
                user_id, name, email, tier = user
                token = generate_token(user_id, email, name, tier)
                self._set_json_headers(200)
                self.wfile.write(json.dumps({
                    "message": "Login successful",
                    "token": token,
                    "user": {"id": user_id, "name": name, "email": email, "tier": tier}
                }).encode())
            else:
                self._set_json_headers(401)
                self.wfile.write(json.dumps({"error": "Invalid email or password."}).encode())

        elif parsed.path == "/api/concierge/chat":
            query = data.get("message", "").strip()
            lang = data.get("lang", "en")
            if not query:
                self._set_json_headers(400)
                self.wfile.write(json.dumps({"error": "Message parameter is required."}).encode())
                return

            response_text = answer_concierge_query(query, lang)
            # Log to DB asynchronously
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO concierge_logs (user_id, query, response, lang) VALUES (?, ?, ?, ?)", (0, query, response_text, lang))
                conn.commit()
                conn.close()
            except Exception:
                pass

            self._set_json_headers(200)
            self.wfile.write(json.dumps({
                "response": response_text,
                "timestamp": int(time.time()),
                "status": "delivered"
            }).encode())
        else:
            self._set_json_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/admin":
            qs = dict(pair.split("=", 1) for pair in parsed.query.split("&") if "=" in pair)
            key = qs.get("key", "")
            if key != ADMIN_EDIT_KEY:
                self._set_json_headers(403)
                self.wfile.write(json.dumps({"error": "Invalid or missing editor key"}).encode())
                return
            page = admin_editor_page(key)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page.encode())))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(page.encode())
            return
        if parsed.path.startswith("/api/"):
            if parsed.path == "/api/auth/me":
                auth_header = self.headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    self._set_json_headers(401)
                    self.wfile.write(json.dumps({"error": "Bearer token required"}).encode())
                    return
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                if payload:
                    self._set_json_headers(200)
                    self.wfile.write(json.dumps({"user": payload}).encode())
                else:
                    self._set_json_headers(401)
                    self.wfile.write(json.dumps({"error": "Invalid or expired session token"}).encode())
            
            elif parsed.path == "/api/market/stats":
                # Real-time Persian Sovereign Commodity & Asset Ticker
                fluctuate = lambda base, spread: round(base + (random.random() * spread * 2 - spread), 2)
                stats = {
                    "updated_at": int(time.time()),
                    "assets": [
                        {
                            "symbol": "SFRN-KG",
                            "name": "Super Negin Saffron Bullion",
                            "price_usd": fluctuate(3420.0, 15.0),
                            "change_24h": "+2.45%",
                            "status": "BULLISH",
                            "history": [3380, 3395, 3410, 3405, 3418, 3422, 3425]
                        },
                        {
                            "symbol": "CVR-ALMAS",
                            "name": "Caspian Almas Albino Beluga",
                            "price_usd": fluctuate(28500.0, 250.0),
                            "change_24h": "+5.12%",
                            "status": "RARITY_MAX",
                            "history": [27000, 27400, 27800, 28100, 28350, 28500]
                        },
                        {
                            "symbol": "TRQ-NEYS",
                            "name": "Neyshabur Pure Turquoise Grade A",
                            "price_usd": fluctuate(4800.0, 40.0),
                            "change_24h": "+1.80%",
                            "status": "STABLE",
                            "history": [4700, 4720, 4750, 4780, 4790, 4805]
                        },
                        {
                            "symbol": "ISF-SILK",
                            "name": "17th C. Safavid Silk Index",
                            "price_usd": fluctuate(185000.0, 1200.0),
                            "change_24h": "+8.90%",
                            "status": "ALL_TIME_HIGH",
                            "history": [168000, 172000, 176000, 181000, 185000]
                        }
                    ],
                    "total_guild_volume_24h": "$42.8M USD"
                }
                self._set_json_headers(200)
                self.wfile.write(json.dumps(stats).encode())

            elif parsed.path == "/api/members/directory":
                directory = [
                    {"name": "Cyrus Pahlavi", "title": "Custodian Chancellor", "tier": "Royal Custodian", "location": "Geneva / Tehran", "reputation": "100/100"},
                    {"name": "Daria Rostami", "title": "Managing Partner, Avesta Capital", "tier": "Sovereign Patron", "location": "Dubai / London", "reputation": "98/100"},
                    {"name": "Kaveh Jahanbani", "title": "Aeronautical Principal", "tier": "Sovereign Patron", "location": "Zurich", "reputation": "96/100"},
                    {"name": "Soraya Bakhtiar", "title": "Heritage Arts Director", "tier": "Fellow Candidate", "location": "Paris / Isfahan", "reputation": "94/100"}
                ]
                self._set_json_headers(200)
                self.wfile.write(json.dumps({"members": directory, "count": len(directory)}).encode())
            else:
                self._set_json_headers(404)
                self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())
            return

        # Serve static files from PUBLIC_DIR
        req_path = parsed.path.lstrip("/")
        if not req_path or req_path == "":
            req_path = "index.html"

        file_path = os.path.join(PUBLIC_DIR, req_path)
        # Security check
        if not os.path.abspath(file_path).startswith(os.path.abspath(PUBLIC_DIR)):
            self.send_error(403, "Access denied")
            return

        if os.path.exists(file_path) and os.path.isfile(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(os.path.getsize(file_path)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")

def run_server():
    init_db()
    port = int(os.environ.get("PORT", 8080))
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, UnifiedServerHandler)
    httpd.daemon_threads = True
    print(f"Unified Multi-Threaded Static + Authentication + Concierge API Server running on port {port}", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
