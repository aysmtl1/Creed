#!/usr/bin/env python3
"""
CHAPTER / — local server
------------------------
1) Serves the app (index.html).
2) Accounts: real sign-up / log-in with hashed passwords, a session cookie and one shared
   SQLite database (chapter.db), so every person has their own library and people who use the
   same server can find each other, add friends, see each other's shelves and chat.
3) Forwards book-API requests (Gutenberg, Open Library, Internet Archive, Vikikaynak) that the
   browser can't make directly (CORS). Only the hosts in ALLOWED are forwarded.

Run:    python server.py                 (macOS/Linux: python3 server.py)
Open:   http://localhost:8000
Check:  python server.py --check         (tests every book source)
Share on your Wi-Fi (classmates on the same network):  HOST=0.0.0.0  python server.py
        then they open  http://<your-computer's-IP>:8000
Real Google sign-in (optional): GOOGLE_CLIENT_ID=<your OAuth client id>  python server.py
Needs only the Python standard library (Python 3.8+).
"""
import http.server, socketserver, urllib.request, urllib.parse, urllib.error, ssl, os, sys, time, socket
import json, sqlite3, hashlib, hmac, secrets, re, threading, tempfile
from http.cookies import SimpleCookie
from concurrent.futures import Future

PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "127.0.0.1")
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CHAPTER_DB", os.path.join(HERE, "chapter.db"))
def _client_id():
    v = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if v: return v
    try:   # or simply paste it into google_client_id.txt next to this file
        with open(os.path.join(HERE, "google_client_id.txt"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and line.endswith(".apps.googleusercontent.com"): return line
    except OSError:
        pass
    return ""
GOOGLE_CLIENT_ID = _client_id()

def _books_key():
    """Google Books API key (starts with AIza...). From GOOGLE_BOOKS_KEY, or a line in google_books_key.txt
    (or google_client_id.txt). It stays on this computer: the server adds it to Google Books requests itself."""
    v = os.environ.get("GOOGLE_BOOKS_KEY", "").strip()
    if v: return v
    for name in ("google_books_key.txt", "google_client_id.txt"):
        try:
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AIza") and len(line) > 30: return line
        except OSError:
            pass
    return ""
GOOGLE_BOOKS_KEY = _books_key()
# Open Library asks API users to identify themselves; put your own contact here.
CONTACT = os.environ.get("CHAPTER_CONTACT", "student@example.com")
USER_AGENT = f"CHAPTER-reading-app/1.3 ({CONTACT})"
ALLOWED = (
    "openlibrary.org", "covers.openlibrary.org", "archive.org",   # also matches ia*.us.archive.org
    "gutendex.com", "gutenberg.org",                               # also matches www.gutenberg.org
    "wikisource.org",                                              # tr.wikisource.org, en.wikisource.org
    "pglaf.org", "nabasny.com",                                    # official Project Gutenberg file mirrors
)
# www.gutenberg.org sometimes answers 503 (busy, or it rate-limits a network). The same files are on
# Project Gutenberg's own mirrors, so book files and covers are fetched from there instead.
GB_MIRRORS = ("https://aleph.pglaf.org", "https://gutenberg.pglaf.org", "http://gutenberg.nabasny.com")
_gb_down = [0.0]   # time www.gutenberg.org last failed; for 10 min we go straight to the mirrors
MAX_BYTES = 40 * 1024 * 1024
TIMEOUT = 45
CATALOG_TIMEOUT = 6  # interactive searches can switch to another catalogue
CATALOG_COOLDOWN = 60
_catalog_retry_at = {}
_catalog_lock = threading.Lock()
_catalog_pending = {}  # share identical in-flight queries between UI sections
SESSION_DAYS = 30
COOKIE = "chapter_sid"
_last = {}   # tiny politeness limiter (Open Library: ~1 request/second without a key)
_cache = {}  # url -> (time, ctype, body): searches and books are kept for 30 min so repeats are instant
CACHE_TTL, CACHE_MAX = 1800, 120 * 1024 * 1024
_fails = {}  # email -> [timestamps of failed logins]  (slows down password guessing)

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CTX = ssl.create_default_context()
try:
    sys.stdout.reconfigure(errors="replace"); sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- database
_db_lock = threading.Lock()
from contextlib import contextmanager
@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback(); raise
    finally:
        con.close()

def init_db():
    with _db_lock, db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            email TEXT PRIMARY KEY, name TEXT NOT NULL, provider TEXT NOT NULL,
            pw TEXT, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
            token TEXT PRIMARY KEY, email TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS libraries(
            email TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS friends(
            owner TEXT NOT NULL, friend TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(owner, friend));
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT, pair TEXT NOT NULL, sender TEXT NOT NULL,
            text TEXT NOT NULL, book TEXT, ts REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS msg_pair ON messages(pair, id);
        CREATE TABLE IF NOT EXISTS books(
            id TEXT PRIMARY KEY, owner TEXT NOT NULL, title TEXT, author TEXT, data TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS reads(
            owner TEXT NOT NULL, other TEXT NOT NULL, last_id INTEGER NOT NULL, PRIMARY KEY(owner, other));
        """)

def hash_pw(pw, salt=None, n=200_000):
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, n)
    return f"pbkdf2_sha256${n}${salt.hex()}${dk.hex()}"

def check_pw(pw, stored):
    try:
        _, n, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), int(n))
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False

EMAIL_RX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
def pub(u):
    return {"email": u["email"], "name": u["name"], "provider": u["provider"]}
def pair(a, b):
    return "|".join(sorted([a, b]))

# ---------------------------------------------------------------- book proxy
def allowed(url):
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    if host == "www.googleapis.com":                       # Google Books API only, nothing else on googleapis
        return u.scheme == "https" and u.path.startswith("/books/v1/")
    return u.scheme in ("http", "https") and any(host == h or host.endswith("." + h) for h in ALLOWED)

def with_books_key(url):
    u = urllib.parse.urlparse(url)
    if GOOGLE_BOOKS_KEY and u.hostname == "www.googleapis.com" and "key=" not in (u.query or ""):
        return url + ("&" if u.query else "?") + "key=" + urllib.parse.quote(GOOGLE_BOOKS_KEY)
    return url

def explain(e, timeout):
    s = str(e)
    if isinstance(e, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in s:
        return "SSL certificate problem - run:  pip install certifi   then restart server.py"
    if isinstance(e, (socket.timeout, TimeoutError)) or "timed out" in s:
        return f"the source did not answer within {timeout}s (it may be busy - try again)"
    if "getaddrinfo" in s or "Name or service not known" in s or "nodename" in s:
        return "no internet / DNS problem on this computer"
    return s[:200]

def gb_mirror_paths(url):
    """www.gutenberg.org URL -> the same file's path on a mirror (cache/epub/<id>/...), or None."""
    u = urllib.parse.urlparse(url)
    if not (u.hostname or "").endswith("gutenberg.org"):
        return None
    p = u.path
    m = re.match(r"^/cache/epub/(\d+)/(.+)$", p)
    if m: return p
    m = re.match(r"^/ebooks/(\d+)\.(epub3\.images|epub\.images|epub\.noimages|txt\.utf-8|html\.images)$", p)
    if m:
        i, kind = m.group(1), m.group(2)
        name = {"epub3.images": f"pg{i}-images-3.epub", "epub.images": f"pg{i}-images.epub",
                "epub.noimages": f"pg{i}.epub", "txt.utf-8": f"pg{i}.txt", "html.images": f"pg{i}-images.html"}[kind]
        return f"/cache/epub/{i}/{name}"
    return None

def fetch(url, cache=True):
    host = urllib.parse.urlparse(url).hostname or ""
    if cache and api_cacheable(url):                 # catalogue answers: kept on disk for 12 h, so the app opens fast
        hit = api_cache_get(url)
        if hit: return 200, hit[1], hit[0]
        with _catalog_lock:
            pending = _catalog_pending.get(url)
            if pending is None:
                future = _catalog_pending[url] = Future()
        if pending is not None:
            return pending.result()
        try:
            code, body, ctype = _fetch_api(url, host)
            if code == 200: api_cache_put(url, ctype, body)
            future.set_result((code, body, ctype))
            return future.result()
        except Exception as error:
            future.set_exception(error)
            raise
        finally:
            with _catalog_lock:
                del _catalog_pending[url]
    return _fetch_api(url, host, cache)

def _fetch_api(url, host, cache=True):
    # Wikisource also uses its API to download the text of entire chapters.
    if host.endswith("wikisource.org") and urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("action") == ["parse"]:
        return fetch_one(url, cache)
    if api_cacheable(url):
        # Cache hits have already been served by fetch(). A catalog outage shouldn't
        # hold up each new mood, search or language choice for two download timeouts.
        with _catalog_lock:
            if time.monotonic() < _catalog_retry_at.get(host, 0):
                return 503, f"{host} temporarily unavailable; try another catalogue".encode(), "text/plain"
        code, body, ctype = fetch_one(with_books_key(url), cache, retries=1, timeout=CATALOG_TIMEOUT)
        if code >= 500 or code == 429:
            with _catalog_lock:
                _catalog_retry_at[host] = time.monotonic() + CATALOG_COOLDOWN
        if host == "www.googleapis.com" and GOOGLE_BOOKS_KEY:
            body = body.replace(GOOGLE_BOOKS_KEY.encode(), b"<key>")
        return code, body, ctype
    if host == "www.googleapis.com":
        code, body, ctype = fetch_one(with_books_key(url), cache)
        if GOOGLE_BOOKS_KEY:
            body = body.replace(GOOGLE_BOOKS_KEY.encode(), b"<key>")
        return code, body, ctype
    if not host.endswith("gutenberg.org"):
        return fetch_one(url, cache)
    path = gb_mirror_paths(url)
    if not path:
        return fetch_one(url, cache, retries=1)
    disk = book_cache_get(path) if cache else None  # downloaded before -> instant, even after a restart
    if disk: return 200, disk[1], disk[0]
    sources = ([] if time.time() - _gb_down[0] < 600 else [url]) + [m + path for m in GB_MIRRORS]
    code, body, ctype, winner = race(sources)
    if winner != url and url in sources: _gb_down[0] = time.time()
    if code == 200 and cache: book_cache_put(path, ctype, body)
    return code, body, ctype

API_TTL = 12 * 3600
def api_cacheable(url):
    u = urllib.parse.urlparse(url); h = (u.hostname or "").lower(); p = u.path
    return (h == "gutendex.com" or (h == "www.googleapis.com" and p.startswith("/books/v1/volumes"))
            or (h == "openlibrary.org" and p == "/search.json") or (h.endswith("wikisource.org") and p.endswith("/api.php"))
            or (h.endswith("gutenberg.org") and "search.opds" in p))
def _api_name(url):
    return os.path.join(BOOK_CACHE, "api", hashlib.sha1(url.encode("utf-8")).hexdigest())
def api_cache_get(url):
    f = _api_name(url)
    try:
        if time.time() - os.path.getmtime(f) > API_TTL: return None
        with open(f, "rb") as fh:
            ctype, _, body = fh.read().partition(b"\n")
        return ctype.decode("ascii", "replace"), body
    except OSError:
        return None
def api_cache_put(url, ctype, body):
    try:
        os.makedirs(os.path.join(BOOK_CACHE, "api"), exist_ok=True)
        write_cache_file(_api_name(url), (ctype or "application/json").encode("ascii", "replace") + b"\n" + body)
    except OSError:
        pass

def write_cache_file(path, data):
    # Concurrent requests for the same title must never share a partially written file.
    tmp = tempfile.NamedTemporaryFile(dir=os.path.dirname(path), suffix=".part", delete=False)
    try:
        with tmp:
            tmp.write(data)
        os.replace(tmp.name, path)
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

def race(urls):
    """Ask every source at once and keep the first good answer (mirror speed varies a lot by country)."""
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    pool = ThreadPoolExecutor(max_workers=len(urls))
    futs = {pool.submit(fetch_one, u, False, 1): u for u in urls}
    first = None
    try:
        while futs:
            done, _ = wait(list(futs), return_when=FIRST_COMPLETED)
            for f in done:
                u = futs.pop(f)
                code, body, ctype = f.result()
                if code == 200:
                    return code, body, ctype, u
                first = first or (code, body, ctype)
    finally:
        for f in futs:
            f.cancel()
        pool.shutdown(wait=False)
    return first + (None,)

BOOK_CACHE = os.path.join(HERE, "book-cache")   # Gutenberg files kept on disk (never served directly)
def _bc_name(path):
    return os.path.join(BOOK_CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", path.strip("/")))
def book_cache_get(path):
    try:
        with open(_bc_name(path), "rb") as f:
            data = f.read()
        ctype = "application/epub+zip" if path.endswith(".epub") else "text/plain; charset=utf-8" if path.endswith(".txt") else "image/jpeg" if path.endswith(".jpg") else "application/octet-stream"
        return ctype, data
    except OSError:
        return None
def book_cache_put(path, ctype, body):
    if not path.endswith((".epub", ".txt", ".jpg")): return   # books and covers
    try:
        os.makedirs(BOOK_CACHE, exist_ok=True)
        files = sorted((os.path.getmtime(os.path.join(BOOK_CACHE, n)), n) for n in os.listdir(BOOK_CACHE) if not n.endswith(".part") and os.path.isfile(os.path.join(BOOK_CACHE, n)))
        total = sum(os.path.getsize(os.path.join(BOOK_CACHE, n)) for _, n in files)
        while files and total > 300 * 1024 * 1024:                  # keep the folder under ~300 MB
            _, n = files.pop(0); total -= os.path.getsize(os.path.join(BOOK_CACHE, n)); os.remove(os.path.join(BOOK_CACHE, n))
        write_cache_file(_bc_name(path), body)
    except OSError:
        pass

def fetch_one(url, cache=True, retries=2, timeout=TIMEOUT):
    host = urllib.parse.urlparse(url).hostname or ""
    hit = _cache.get(url)
    if cache and hit and time.time() - hit[0] < CACHE_TTL:
        return 200, hit[2], hit[1]
    for attempt in range(1, retries + 1):
        wait = 1.0 - (time.time() - _last.get(host, 0))
        if host.endswith("openlibrary.org") and wait > 0:
            time.sleep(wait)
        _last[host] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                if not allowed(r.geturl()) and not r.geturl().startswith("https://oauth2.googleapis.com/"):
                    return 403, b"redirect not allowed", "text/plain"
                body = r.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    return 413, b"file too large", "text/plain"
                ctype = r.headers.get("Content-Type", "application/octet-stream")
                if cache:
                    if sum(len(v[2]) for v in _cache.values()) + len(body) > CACHE_MAX:
                        _cache.clear()
                    _cache[url] = (time.time(), ctype, body)
                return 200, body, ctype
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < retries:
                time.sleep(1.5); continue
            return e.code, f"{host} answered HTTP {e.code}".encode(), "text/plain"
        except Exception as e:
            if attempt < retries and ("timed out" in str(e) or isinstance(e, (socket.timeout, TimeoutError))):
                continue
            return 502, f"{host}: {explain(e, timeout)}".encode(), "text/plain"
    return 502, f"{host}: no answer".encode(), "text/plain"

# ---------------------------------------------------------------- HTTP
class ApiError(Exception):
    def __init__(self, code, msg, field=None):
        super().__init__(msg); self.code, self.msg, self.field = code, msg, field

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json", ".js": "text/javascript"}
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        # Validate the resolved filename for both GET and HEAD. The working folder
        # also contains credentials, account data, source files and private caches.
        path = os.path.realpath(self.translate_path(self.path))
        root = os.path.realpath(HERE)
        relative = os.path.relpath(path, root).replace(os.sep, "/")
        shell = relative in (".", "index.html", "sw.js", "manifest.webmanifest")
        asset = (relative.startswith(("icons/", "ornek-kitaplar/")) and os.path.isfile(path))
        if shell or asset:
            return super().send_head()
        self.send_error(404, "File not found")
        return None

    # ---- routing
    def do_GET(self):
        p = self.path
        if p.startswith("/proxy/ping"):  return self._send(200, b"chapter-proxy", "text/plain")
        if p.startswith("/proxy?"):      return self._proxy()
        if p.startswith("/api/"):        return self._api("GET")
        if p.startswith("/favicon.ico"): self.send_response(204); self.end_headers(); return
        return super().do_GET()
    def do_POST(self):   return self._api("POST") if self.path.startswith("/api/") else self._send(404, b"", "text/plain")
    def do_PUT(self):    return self._api("PUT") if self.path.startswith("/api/") else self._send(404, b"", "text/plain")
    def do_DELETE(self): return self._api("DELETE") if self.path.startswith("/api/") else self._send(404, b"", "text/plain")

    def _send(self, code, body, ctype, headers=None):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, BrokenPipeError):
            pass

    def _json(self, code, obj, headers=None):
        return self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", headers)

    def log_message(self, fmt, *args):
        pass

    # ---- proxy
    def _proxy(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        url = (qs.get("url") or [""])[0]
        if not allowed(url):
            print(f"  x 403  not on the allow-list: {url[:90]}")
            return self._send(403, b"host not allowed", "text/plain", {"Access-Control-Allow-Origin": "*"})
        t = time.time()
        code, body, ctype = fetch(url)
        host = urllib.parse.urlparse(url).hostname
        if code == 200:
            print(f"  ok {code}  {host}  {len(body)//1024} KB  {time.time()-t:.1f}s{'  (cache)' if time.time()-t < 0.01 else ''}")
        else:
            print(f"  x  {code}  {body.decode('utf-8','replace')[:220]}")
        return self._send(code, body, ctype, {"Access-Control-Allow-Origin": "*"})

    # ---- accounts API
    def _body(self, limit=2_000_000):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit: raise ApiError(413, "Too much data.")
        if not n: return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            raise ApiError(400, "Bad request.")

    def _same_origin(self):
        # cookies + JSON from our own page only (blocks other websites posting to the API)
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
            raise ApiError(403, "Cross-site request refused.")
        if self.command != "GET" and "application/json" not in (self.headers.get("Content-Type") or ""):
            raise ApiError(415, "JSON expected.")

    def _token(self):
        c = SimpleCookie(self.headers.get("Cookie") or "")
        return c[COOKIE].value if COOKIE in c else None

    def _me(self, con, required=True):
        tok = self._token()
        row = None
        if tok:
            row = con.execute("SELECT u.* , s.created AS sc FROM sessions s JOIN users u ON u.email=s.email WHERE s.token=?", (tok,)).fetchone()
            if row and time.time() - row["sc"] > SESSION_DAYS * 86400:
                con.execute("DELETE FROM sessions WHERE token=?", (tok,)); row = None
        if required and not row: raise ApiError(401, "Please sign in.")
        return row

    def _start_session(self, con, email):
        tok = secrets.token_urlsafe(32)
        con.execute("INSERT INTO sessions(token,email,created) VALUES(?,?,?)", (tok, email, time.time()))
        return {"Set-Cookie": f"{COOKIE}={tok}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS*86400}"}

    def _is_friend(self, con, me, other):
        return con.execute("SELECT 1 FROM friends WHERE owner=? AND friend=?", (me, other)).fetchone() is not None

    def _api(self, method):
        u = urllib.parse.urlparse(self.path); path = u.path; qs = urllib.parse.parse_qs(u.query)
        q = lambda k: (qs.get(k) or [""])[0]
        try:
            self._same_origin()
            with _db_lock, db() as con:
                # -- public
                if path == "/api/config" and method == "GET":
                    return self._json(200, {"server": True, "google_client_id": GOOGLE_CLIENT_ID or None, "google_books_key": bool(GOOGLE_BOOKS_KEY)})
                if path == "/api/signup" and method == "POST":
                    b = self._body(); name = str(b.get("name", "")).strip()[:60]
                    email = str(b.get("email", "")).strip().lower(); pw = str(b.get("password", ""))
                    if len(name) < 2: raise ApiError(400, "Tell us what to call you.", "name")
                    if not EMAIL_RX.match(email): raise ApiError(400, "That doesn’t look like an email — check for “@” and a domain.", "email")
                    if len(pw) < 8: raise ApiError(400, "Use at least 8 characters.", "password")
                    if con.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                        raise ApiError(409, "This email already has an account — log in instead.", "email")
                    con.execute("INSERT INTO users(email,name,provider,pw,created) VALUES(?,?,?,?,?)", (email, name, "email", hash_pw(pw), time.time()))
                    print(f"  + new account: {name}")
                    return self._json(200, {"user": {"email": email, "name": name, "provider": "email"}, "created": True}, self._start_session(con, email))
                if path == "/api/login" and method == "POST":
                    b = self._body(); email = str(b.get("email", "")).strip().lower(); pw = str(b.get("password", ""))
                    recent = [t for t in _fails.get(email, []) if time.time() - t < 300]
                    if len(recent) >= 5: raise ApiError(429, "Too many wrong tries — wait 5 minutes and try again.", "password")
                    row = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                    if not row:
                        raise ApiError(404, "No account with this email yet.", "email")
                    if not row["pw"]:
                        raise ApiError(400, "This account uses Google sign-in.", "email")
                    if not check_pw(pw, row["pw"]):
                        _fails[email] = recent + [time.time()]
                        raise ApiError(401, "Wrong password — try again.", "password")
                    _fails.pop(email, None)
                    return self._json(200, {"user": pub(row), "created": False}, self._start_session(con, email))
                if path == "/api/google" and method == "POST":
                    if not GOOGLE_CLIENT_ID: raise ApiError(400, "Google sign-in isn’t set up on this server.")
                    cred = str(self._body().get("credential", ""))
                    code, body, _ = _google_tokeninfo(cred)
                    if code != 200: raise ApiError(401, "Google couldn’t confirm this sign-in.")
                    info = json.loads(body)
                    if info.get("aud") != GOOGLE_CLIENT_ID or str(info.get("email_verified")).lower() != "true" \
                       or info.get("iss") not in ("accounts.google.com", "https://accounts.google.com") or int(info.get("exp", 0)) < time.time():
                        raise ApiError(401, "Google couldn’t confirm this sign-in.")
                    email = info["email"].lower(); name = info.get("name") or email.split("@")[0]
                    row = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                    created = row is None
                    if created:
                        con.execute("INSERT INTO users(email,name,provider,pw,created) VALUES(?,?,?,?,?)", (email, name, "google", None, time.time()))
                        row = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                    return self._json(200, {"user": pub(row), "created": created}, self._start_session(con, email))
                if path == "/api/logout" and method == "POST":
                    tok = self._token()
                    if tok: con.execute("DELETE FROM sessions WHERE token=?", (tok,))
                    return self._json(200, {"ok": True}, {"Set-Cookie": f"{COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"})

                # -- signed in
                me = self._me(con, required=(path != "/api/me"))
                if path == "/api/me":
                    return self._json(200, {"user": pub(me) if me else None})
                email = me["email"]
                if path == "/api/data":
                    if method == "GET":
                        row = con.execute("SELECT data FROM libraries WHERE email=?", (email,)).fetchone()
                        return self._json(200, {"data": json.loads(row["data"]) if row else None})
                    if method == "PUT":
                        d = self._body()
                        if not isinstance(d.get("lib"), dict) or not isinstance(d.get("week"), list): raise ApiError(400, "Bad library data.")
                        clean = {"lib": d["lib"], "week": d["week"][:7], "books": d.get("books") if isinstance(d.get("books"), dict) else {},
                                 "days": [str(x)[:10] for x in d.get("days", [])][:4000] if isinstance(d.get("days"), list) else [],
                                 "notes": d.get("notes") if isinstance(d.get("notes"), dict) else {},
                                 "onb": bool(d.get("onb"))}
                        con.execute("INSERT INTO libraries(email,data,updated) VALUES(?,?,?) ON CONFLICT(email) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                                    (email, json.dumps(clean, ensure_ascii=False), time.time()))
                        return self._json(200, {"ok": True})
                if path == "/api/users" and method == "GET":
                    term = q("q").strip().lower()
                    if term:
                        rows = con.execute("SELECT * FROM users WHERE email<>? AND (lower(name) LIKE ? OR email LIKE ?) ORDER BY name LIMIT 20",
                                           (email, f"%{term}%", f"%{term}%")).fetchall()
                    else:
                        rows = con.execute("SELECT * FROM users WHERE email<>? ORDER BY created DESC LIMIT 12", (email,)).fetchall()
                    mine = {r["friend"] for r in con.execute("SELECT friend FROM friends WHERE owner=?", (email,))}
                    return self._json(200, {"users": [dict(pub(r), friend=r["email"] in mine) for r in rows]})
                if path == "/api/friends":
                    if method == "GET":
                        rows = con.execute("""SELECT u.*, l.data FROM friends f JOIN users u ON u.email=f.friend
                                              LEFT JOIN libraries l ON l.email=f.friend WHERE f.owner=? ORDER BY f.created""", (email,)).fetchall()
                        out = []
                        for r in rows:
                            d = json.loads(r["data"]) if r["data"] else {}
                            m = con.execute("SELECT sender,text,ts FROM messages WHERE pair=? ORDER BY id DESC LIMIT 1", (pair(email, r["email"]),)).fetchone()
                            out.append(dict(pub(r), lib=d.get("lib", {}), books=d.get("books", {}),
                                            last=({"from": m["sender"], "text": m["text"][:120], "t": int(m["ts"]*1000)} if m else None)))
                        return self._json(200, {"friends": out})
                    if method == "POST":
                        other = str(self._body().get("email", "")).strip().lower()
                        if other == email: raise ApiError(400, "That’s you!")
                        if not con.execute("SELECT 1 FROM users WHERE email=?", (other,)).fetchone():
                            raise ApiError(404, "No one has signed up with that email yet.")
                        for a, b2 in ((email, other), (other, email)):   # friendship is mutual
                            con.execute("INSERT OR IGNORE INTO friends(owner,friend,created) VALUES(?,?,?)", (a, b2, time.time()))
                        return self._json(200, {"ok": True})
                    if method == "DELETE":
                        other = q("email").lower()
                        con.execute("DELETE FROM friends WHERE (owner=? AND friend=?) OR (owner=? AND friend=?)", (email, other, other, email))
                        return self._json(200, {"ok": True})
                if path.startswith("/api/books/"):
                    bid = urllib.parse.unquote(path[len("/api/books/"):])[:120]
                    if not bid: raise ApiError(404, "No book.")
                    row = con.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
                    if method == "PUT":                       # save your own uploaded / downloaded book on the server
                        if row and row["owner"] != email: return self._json(200, {"ok": True, "shared": True})   # same public text already here
                        b = self._body(limit=30_000_000).get("book")
                        if not isinstance(b, dict) or not isinstance(b.get("sections"), list): raise ApiError(400, "Bad book.")
                        b["owner"] = email
                        con.execute("INSERT INTO books(id,owner,title,author,data,created) VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,title=excluded.title,author=excluded.author",
                                    (bid, email, str(b.get("title",""))[:200], str(b.get("author",""))[:200], json.dumps(b, ensure_ascii=False), time.time()))
                        return self._json(200, {"ok": True})
                    if not row: raise ApiError(404, "This book isn’t on the server.")
                    if method == "DELETE":
                        if row["owner"] != email: raise ApiError(403, "Only the person who added it can remove it.")
                        con.execute("DELETE FROM books WHERE id=?", (bid,)); return self._json(200, {"ok": True})
                    if method == "GET":                       # owner, the owner's friends, or anyone who already has it on their shelf
                        ok = row["owner"] == email or self._is_friend(con, email, row["owner"])
                        if not ok:
                            lib = con.execute("SELECT data FROM libraries WHERE email=?", (email,)).fetchone()
                            ok = bool(lib) and bid in (json.loads(lib["data"]).get("lib") or {})
                        if not ok: raise ApiError(403, "Add the person who shared this book as a friend to read it.")
                        b = json.loads(row["data"]); b["sharedBy"] = row["owner"]
                        o = con.execute("SELECT name FROM users WHERE email=?", (row["owner"],)).fetchone()
                        b["sharedByName"] = o["name"] if o else ""
                        return self._json(200, {"book": b})
                if path == "/api/unread" and method == "GET":
                    out, last = {}, {}
                    for f in con.execute("SELECT friend FROM friends WHERE owner=?", (email,)).fetchall():
                        other = f["friend"]
                        r = con.execute("SELECT last_id FROM reads WHERE owner=? AND other=?", (email, other)).fetchone()
                        rows = con.execute("SELECT id,text FROM messages WHERE pair=? AND sender=? AND id>? ORDER BY id",
                                           (pair(email, other), other, r["last_id"] if r else 0)).fetchall()
                        if rows:
                            out[other] = len(rows); last[other] = rows[-1]["text"][:80]
                    return self._json(200, {"unread": out, "last": last})
                if path == "/api/chat":
                    if method == "GET":
                        other = q("with").lower(); since = int(q("after") or 0)
                        if not self._is_friend(con, email, other): raise ApiError(403, "You can only chat with friends.")
                        rows = con.execute("SELECT id,sender,text,book,ts FROM messages WHERE pair=? AND id>? ORDER BY id LIMIT 500", (pair(email, other), since)).fetchall()
                        if rows:   # the chat is open, so these messages are now read
                            con.execute("INSERT INTO reads(owner,other,last_id) VALUES(?,?,?) ON CONFLICT(owner,other) DO UPDATE SET last_id=max(last_id,excluded.last_id)",
                                        (email, other, rows[-1]["id"]))
                        return self._json(200, {"messages": [{"id": r["id"], "from": r["sender"], "text": r["text"], "book": r["book"], "t": int(r["ts"]*1000)} for r in rows]})
                    if method == "POST":
                        b = self._body(); other = str(b.get("with", "")).lower(); text = str(b.get("text", "")).strip()[:2000]
                        if not text: raise ApiError(400, "Empty message.")
                        if not self._is_friend(con, email, other): raise ApiError(403, "You can only chat with friends.")
                        book = (str(b.get("book")) if b.get("book") else None)
                        cur = con.execute("INSERT INTO messages(pair,sender,text,book,ts) VALUES(?,?,?,?,?)", (pair(email, other), email, text, book, time.time()))
                        return self._json(200, {"id": cur.lastrowid})
                raise ApiError(404, "Unknown API route.")
        except ApiError as e:
            return self._json(e.code, {"error": e.msg, "field": e.field})
        except Exception as e:
            print("  ! server error:", repr(e)[:200])
            return self._json(500, {"error": "Server error — see the server.py window."})

def _google_tokeninfo(cred):
    req = urllib.request.Request("https://oauth2.googleapis.com/tokeninfo?id_token=" + urllib.parse.quote(cred), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as r:
            return 200, r.read(), "application/json"
    except Exception:
        return 401, b"", ""

def check():
    tests = [
        ("Open Library", "https://openlibrary.org/search.json?q=dracula&fields=key,title&limit=1"),
        ("Gutenberg search", "https://www.gutenberg.org/ebooks/search.opds/?query=dracula"),
        ("Gutendex (backup)", "https://gutendex.com/books/?search=dracula"),
        ("Gutenberg books", "https://www.gutenberg.org/ebooks/345.epub.noimages"),
        ("Google Books" + (" (key)" if GOOGLE_BOOKS_KEY else " (no key)"), "https://www.googleapis.com/books/v1/volumes?q=dracula&maxResults=1"),
        ("Internet Archive", "https://archive.org/metadata/draculabr00stokuoft/metadata"),
        ("Vikikaynak", "https://tr.wikisource.org/w/api.php?action=query&list=search&srsearch=roman&format=json&srlimit=1"),
    ]
    print("Checking the book sources from this computer...\n")
    ok_all = True
    for name, url in tests:
        t = time.time(); code, body, _ = fetch(url, cache=False)
        if code == 200:
            print(f"  OK    {name:18} {time.time()-t:4.1f}s")
        elif name == "Gutenberg search":
            print(f"  BUSY  {name:18} www.gutenberg.org answered {code} - fine, the app searches Gutendex instead")
        else:
            ok_all = False
            print(f"  FAIL  {name:18} {body.decode('utf-8','replace')}")
    print("\nAll good - run  python server.py" if ok_all else "\nSome sources failed. The app falls back to the others; send this output if you need help.")

def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1)); ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "your-IP"

if __name__ == "__main__":
    os.chdir(HERE)
    if "--check" in sys.argv:
        check(); sys.exit(0)
    init_db()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    with socketserver.ThreadingTCPServer((HOST, PORT), Handler) as httpd:
        print(f"CHAPTER / is running ->  http://localhost:{PORT}   (Ctrl+C to stop)")
        if HOST == "0.0.0.0":
            print(f"Classmates on the same Wi-Fi can open ->  http://{lan_ip()}:{PORT}")
        n = sqlite3.connect(DB_PATH).execute("SELECT count(*) FROM users").fetchone()[0]
        print(f"Accounts database: {os.path.basename(DB_PATH)}  ({n} account{'s' if n != 1 else ''})")
        print(f"Google sign-in: {'on' if GOOGLE_CLIENT_ID else 'off - paste your Client ID into google_client_id.txt (see README)'}")
        print(f"Google Books:   {'on, with your API key' if GOOGLE_BOOKS_KEY else 'on, without a key (paste an AIza... key into google_books_key.txt for more searches per day)'}")
        print("Book requests are listed here (ok / x).")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nbye")
