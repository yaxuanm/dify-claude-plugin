#!/usr/bin/env python3
"""browser_login.py: sign in to Dify in a real browser window and keep the session.

Used by `dify_console.py login --method browser`. It opens a temporary Chrome
(or Edge, Brave, Chromium) window with a throwaway profile on the Dify sign-in
page. The user signs in there with any method Dify offers: email code, Google,
GitHub, SSO. Human checks run in the real browser, done by the user. Once the
session cookies appear, they are copied into the plugin's cookie file and the
window closes. The user's normal browser profile is never touched.

Standard library only: it speaks the Chrome DevTools Protocol over a minimal
WebSocket client.
"""
import base64
import json
import os
import pathlib
import platform
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

SESSION_COOKIES = ("access_token", "refresh_token", "csrf_token")


def find_browser():
    env = os.environ.get("DIFY_BROWSER")
    if env:
        return env
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Arc.app/Contents/MacOS/Arc",
        ]
        candidates += [str(pathlib.Path.home() / c.lstrip("/")) for c in candidates]
    elif system == "Windows":
        roots = [os.environ.get(k, "") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        rel = [r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe",
               r"BraveSoftware\Brave-Browser\Application\brave.exe"]
        candidates = [os.path.join(r, p) for r in roots if r for p in rel]
    else:
        candidates = [shutil.which(n) or "" for n in
                      ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser")]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


# ---------- minimal WebSocket client (RFC 6455, client side) ----------

class WebSocket:
    def __init__(self, url, timeout=30):
        u = urllib.parse.urlsplit(url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        path = u.path + ("?" + u.query if u.query else "")
        req = (f"GET {path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake failed")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError("websocket handshake refused")
        self.buf = head.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _recv_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buf += chunk
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def send_text(self, text):
        payload = text.encode()
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126); header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127); header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def recv_text(self):
        message = b""
        while True:
            b1, b2 = self._recv_exact(2)
            fin, opcode, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv_exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if b2 & 0x80 else None
            data = self._recv_exact(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x8:
                raise ConnectionError("websocket closed by browser")
            if opcode in (0x9, 0xA):  # ping/pong: ignore
                continue
            message += data
            if fin:
                return message.decode("utf-8", "replace")

    def call(self, method, params=None):
        self.next_id += 1
        my_id = self.next_id
        self.send_text(json.dumps({"id": my_id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.recv_text())
            if msg.get("id") == my_id:
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message"))
                return msg.get("result") or {}

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ---------- login ----------

def _devtools_port(profile_dir, proc, deadline):
    port_file = pathlib.Path(profile_dir) / "DevToolsActivePort"
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("the browser exited before it was ready")
        if port_file.exists():
            lines = port_file.read_text().splitlines()
            if lines and lines[0].strip().isdigit():
                return int(lines[0])
        time.sleep(0.2)
    raise TimeoutError("the browser did not start its DevTools endpoint")


def _session_cookies(cookies, host):
    found = {}
    for c in cookies:
        name = c.get("name", "")
        base = name[len("__Host-"):] if name.startswith("__Host-") else name
        domain = c.get("domain", "").lstrip(".")
        if base in SESSION_COOKIES and (host == domain or host.endswith("." + domain)):
            found[base] = c
    return found


def browser_login(server, timeout=600, log=print):
    """Open the sign-in page, wait for the user to sign in, return the session cookies (CDP dicts)."""
    browser = find_browser()
    if not browser:
        raise RuntimeError("no Chrome, Edge, Brave or Chromium found; set DIFY_BROWSER to the browser's executable")
    host = urllib.parse.urlsplit(server).hostname
    profile = tempfile.mkdtemp(prefix="dify-login-")
    args = [browser, f"--user-data-dir={profile}", "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1",
            "--no-first-run", "--no-default-browser-check", "--disable-sync", "--new-window"]
    if os.environ.get("DIFY_BROWSER_HEADLESS"):  # tests only
        args += ["--headless=new", "--no-sandbox"]
    args.append(server.rstrip("/") + "/signin")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    try:
        deadline = time.time() + timeout
        port = _devtools_port(profile, proc, time.time() + 30)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=10) as r:
            ws_url = json.loads(r.read())["webSocketDebuggerUrl"]
        ws = WebSocket(ws_url)
        log("Sign in to Dify in the browser window that just opened. Waiting...")
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("the browser window was closed before sign-in finished")
            cookies = ws.call("Storage.getCookies").get("cookies", [])
            found = _session_cookies(cookies, host)
            if "access_token" in found and "csrf_token" in found:
                time.sleep(1.5)  # let the console finish its first requests
                cookies = ws.call("Storage.getCookies").get("cookies", [])
                return list(_session_cookies(cookies, host).values()) or list(found.values())
            time.sleep(2)
        raise TimeoutError("timed out waiting for sign-in")
    finally:
        if ws:
            try:
                ws.call("Browser.close")
            except Exception:
                pass
            ws.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        for _ in range(10):  # the browser may still be flushing its profile
            shutil.rmtree(profile, ignore_errors=True)
            if not os.path.exists(profile):
                break
            time.sleep(0.5)


def to_cookiejar(cdp_cookies, jar):
    """Copy CDP cookie dicts into an http.cookiejar.CookieJar."""
    import http.cookiejar
    for c in cdp_cookies:
        domain = c.get("domain", "")
        host_only = not domain.startswith(".")
        expires = int(c["expires"]) if c.get("expires", -1) and c.get("expires", -1) > 0 else None
        jar.set_cookie(http.cookiejar.Cookie(
            version=0, name=c["name"], value=c["value"], port=None, port_specified=False,
            domain=domain, domain_specified=not host_only, domain_initial_dot=domain.startswith("."),
            path=c.get("path", "/"), path_specified=True, secure=bool(c.get("secure")), expires=expires,
            discard=expires is None, comment=None, comment_url=None, rest={"HttpOnly": None} if c.get("httpOnly") else {},
        ))
