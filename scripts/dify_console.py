#!/usr/bin/env python3
"""dify_console.py: drive a Dify workspace through its console API.

The fallback path for servers where difyctl's /openapi/v1 is off (self-hosted
servers with OPENAPI_ENABLED unset, older versions). It does what the Dify web console does (import a DSL, run the draft,
publish, create an API key, read runs) so the user never has to open it.
Standard library only. Every command prints one JSON object on stdout.

The console API is Dify's internal web API, not a public contract. It can
change between Dify versions; errors carry the server's message so they are
easy to read.

Setup
  detect <server-url>              which path works: openapi (difyctl) or console, and which logins
  login [<server-url>] [--method browser|password|email-code]
                                   browser (default): opens a temporary browser window on the Dify
                                   sign-in page; any sign-in method works. password/email-code:
                                   interactive, run in your own terminal. Stores session cookies only.
  logout | whoami
  workspaces | use-workspace <id>

Build
  models [--type llm|text-embedding]   model rows ready to paste into an LLM node
  datasets                         knowledge bases (ids for knowledge-retrieval nodes)
  apps [--name TEXT]
  import <app.yml> [--app-id ID] [--yes]   create (or overwrite) an app from DSL; --yes confirms a version prompt
  check-deps <app_id>              plugins the app needs and the workspace lacks

Test
  run-draft <app_id> [--inputs JSON|@file] [--query TEXT]
  test-draft <app_id> <cases.json> same cases format as dify_api.py app test
  runs <app_id> [--limit N] | run-detail <app_id> <run_id>

Release
  publish <app_id> [--name TEXT] [--comment TEXT]
  api-key <app_id> --alias NAME    create or reuse an app API key and save it for dify_api.py (never printed)
  kb-key [--alias kb]              create a workspace Knowledge API key and save it for dify_api.py
  webapp <app_id> [--enable|--disable]   public web app URL
"""
import argparse
import base64
import getpass
import http.cookiejar
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dify_api  # noqa: E402  (key store and case checks are shared)

CONF = dify_api.CONF_DIR
STATE = CONF / "console.json"
CLOUD_HOSTS = {"cloud.dify.ai"}
TIMEOUT = 600


def out(obj, code=0):
    dify_api.out(obj, code)


def fail(message, **extra):
    dify_api.fail(message, **extra)


# ---------- state ----------

def load_state():
    try:
        return json.loads(STATE.read_text())
    except FileNotFoundError:
        return {}


def save_state(state):
    CONF.mkdir(parents=True, exist_ok=True)
    os.chmod(CONF, 0o700)
    fd = os.open(STATE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2)


def norm_server(url):
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    for suffix in ("/console/api", "/apps", "/signin"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


def cookie_path(server):
    host = urllib.parse.urlsplit(server).netloc.replace(":", "_")
    return CONF / f"session-{host}.cookies"


def default_service_base(server):
    host = urllib.parse.urlsplit(server).hostname or ""
    return "https://api.dify.ai/v1" if host in CLOUD_HOSTS else server + "/v1"


# ---------- http ----------

class Console:
    def __init__(self, server, need_login=True):
        self.server = server
        self.base = server + "/console/api"
        CONF.mkdir(parents=True, exist_ok=True)
        os.chmod(CONF, 0o700)
        self.jar = http.cookiejar.LWPCookieJar(str(cookie_path(server)))
        try:
            self.jar.load(ignore_discard=True, ignore_expires=True)
        except (FileNotFoundError, http.cookiejar.LoadError):
            pass
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.workspace = load_state().get("servers", {}).get(server, {}).get("workspace_id")
        if need_login and not self.cookie("access_token"):
            fail("not logged in to this server", hint="run the login command in your own terminal", server=server)

    def cookie(self, name):
        for c in self.jar:
            if c.name in (name, "__Host-" + name):
                return c.value
        return None

    def save(self):
        self.jar.save(ignore_discard=True, ignore_expires=True)
        os.chmod(self.jar.filename, 0o600)

    def call(self, method, path, body=None, query=None, stream=False, retry=True):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        headers = {"User-Agent": "dify-claude-plugin", "Accept": "application/json"}
        csrf = self.cookie("csrf_token")
        if csrf:
            headers["X-CSRF-Token"] = csrf
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            resp = self.opener.open(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code == 401 and retry and path != "/refresh-token" and self.refresh():
                return self.call(method, path, body, query, stream, retry=False)
            try:
                detail = json.loads(raw)
            except ValueError:
                detail = raw[:2000]
            if e.code == 401:
                fail("session expired or not logged in", hint="run the login command again in your own terminal", server=detail)
            fail(f"HTTP {e.code} from {method} {path}", http_status=e.code, server=detail)
        except urllib.error.URLError as e:
            fail(f"cannot reach {self.server}: {e.reason}")
        self.save()
        if stream:
            return resp
        raw = resp.read().decode("utf-8", "replace")
        return json.loads(raw) if raw.strip() else {}

    def refresh(self):
        try:
            req = urllib.request.Request(self.base + "/refresh-token", data=b"{}", method="POST",
                                         headers={"Content-Type": "application/json", "User-Agent": "dify-claude-plugin"})
            self.opener.open(req, timeout=60).read()
            self.save()
            return True
        except urllib.error.URLError:
            return False


def probe(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "dify-claude-plugin"}), timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip().startswith("{") else None)
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, ValueError, OSError):
        return None, None


# ---------- commands: setup ----------

def cmd_detect(a):
    server = norm_server(a.server)
    oa_status, oa = probe(server + "/openapi/v1/_version")
    fs_status, fs = probe(server + "/console/api/system-features")
    fs = fs or {}
    host = urllib.parse.urlsplit(server).hostname or ""
    result = {
        "server": server,
        "cloud": host in CLOUD_HOSTS or fs.get("deployment_edition") == "CLOUD",
        "edition": fs.get("deployment_edition"),
        "openapi": oa_status == 200,
        "openapi_version": oa,
        "env_token": bool(os.environ.get("DIFY_SERVER") and os.environ.get("DIFY_TOKEN")),
        "console_reachable": fs_status == 200,
        "login": {
            "password": fs.get("enable_email_password_login"),
            "email_code": fs.get("enable_email_code_login"),
            "social_oauth": fs.get("enable_social_oauth_login"),
            "sso_enforced": (fs.get("sso_enforced_for_signin") or False),
        },
    }
    if result["openapi"]:
        result["path"] = "difyctl"
        result["next"] = "use the difyctl skill: difyctl login --server <server> --no-browser --no-wait"
    elif result["console_reachable"]:
        result["path"] = "console"
        methods = ["browser"] + [m for m in ("password", "email_code") if result["login"][m]]
        if result["cloud"]:
            methods = [m for m in methods if m != "email_code"]  # Cloud email codes need a browser human check
        result["login_methods"] = methods
        result["next"] = "run: login <server> (opens a temporary browser window for the user to sign in)"
    else:
        result["path"] = None
        result["next"] = "no Dify answered at this URL: check the address and that the server is running; if the user has no Dify, offer Dify Cloud (https://cloud.dify.ai) or self-hosting"
    out(result)


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}


def cmd_device_url(a):
    """Fix a difyctl device link that points at an address the user cannot open.

    The server builds verification_uri from CONSOLE_WEB_URL, or from the address
    the request came in on. Under Docker that is often an internal one such as
    http://127.0.0.1:3000. When the link is a loopback address with a different
    origin from the server the user entered, rebuild it on that server.
    """
    server = norm_server(a.server)
    v = urllib.parse.urlsplit(a.verification_uri)
    srv = urllib.parse.urlsplit(server)
    same_origin = (v.scheme, v.netloc) == (srv.scheme, srv.netloc)
    if not same_origin and (v.hostname or "") in LOOPBACK_HOSTS:
        fixed = urllib.parse.urlunsplit((srv.scheme, srv.netloc, v.path or "/device", v.query, ""))
        out({"url": fixed, "rewritten": True, "original": a.verification_uri,
             "note": "the server's CONSOLE_WEB_URL points at an internal address; set it to the URL you open Dify at"})
    else:
        out({"url": a.verification_uri, "rewritten": False})


def cmd_login(a):
    state = load_state()
    server = norm_server(a.server or state.get("current") or "")
    if not server or server == "https://":
        fail("pass the server URL, for example https://cloud.dify.ai")
    method = a.method
    c = Console(server, need_login=False)
    if method == "browser":
        import browser_login
        try:
            cookies = browser_login.browser_login(server, timeout=a.timeout, log=lambda m: print(m, file=sys.stderr))
        except (RuntimeError, TimeoutError, OSError) as e:
            fail(f"browser sign-in failed: {e}")
        c.jar.clear()
        browser_login.to_cookiejar(cookies, c.jar)
        return finish_login(c, server, state)
    if not sys.stdin.isatty():
        fail("run this in your own terminal: it asks for your password or email code, which must not go through the chat")
    c.jar.clear()
    email = input(f"Dify account email for {server}: ").strip()
    if method == "email-code":
        r = c.call("POST", "/email-code-login", {"email": email, "language": "en-US"}, retry=False)
        token = r.get("data")
        code = getpass.getpass("Code from the email (input hidden): ").strip()
        c.call("POST", "/email-code-login/validity", {"email": email, "code": code, "token": token}, retry=False)
    else:
        pw = getpass.getpass("Dify password (input hidden, not stored): ")
        c.call("POST", "/login", {"email": email, "password": base64.b64encode(pw.encode()).decode(),
                                  "remember_me": True}, retry=False)
        del pw
    return finish_login(c, server, state)


def finish_login(c, server, state):
    if not c.cookie("access_token"):
        fail("login returned no session; this server may not support CLI login with this method")
    c.save()
    profile = c.call("GET", "/account/profile")
    state.setdefault("servers", {})[server] = {"email": profile.get("email")}
    state["current"] = server
    save_state(state)
    out({"logged_in": True, "server": server, "email": profile.get("email"), "session_file": str(cookie_path(server))})


def current(a):
    state = load_state()
    server = norm_server(getattr(a, "server", None) or state.get("current") or "")
    if server == "https://":
        fail("not logged in to any server", hint="run the login command in your own terminal")
    return Console(server)


def cmd_logout(a):
    state = load_state()
    server = state.get("current")
    if server:
        p = cookie_path(server)
        if p.exists():
            p.unlink()
        state.get("servers", {}).pop(server, None)
        state.pop("current", None)
        save_state(state)
    out({"logged_out": server})


def cmd_whoami(a):
    c = current(a)
    p = c.call("GET", "/account/profile")
    ws = c.call("GET", "/workspaces")
    cur = next((w for w in ws.get("workspaces", []) if w.get("current")), {})
    out({"server": c.server, "email": p.get("email"), "name": p.get("name"),
         "workspace": {"id": cur.get("id"), "name": cur.get("name"), "role": cur.get("role")}})


def cmd_workspaces(a):
    c = current(a)
    ws = c.call("GET", "/workspaces")
    out({"workspaces": [{k: w.get(k) for k in ("id", "name", "plan", "current", "role")} for w in ws.get("workspaces", [])]})


def cmd_use_workspace(a):
    c = current(a)
    c.call("POST", "/workspaces/switch", {"tenant_id": a.workspace_id})
    out({"switched_to": a.workspace_id})


# ---------- commands: build ----------

def cmd_models(a):
    c = current(a)
    r = c.call("GET", f"/workspaces/current/models/model-types/{a.type}")
    rows = []
    for prov in r.get("data") or []:
        for m in prov.get("models") or []:
            rows.append({"provider": prov.get("provider"), "model": m.get("model"), "status": m.get("status"),
                         "mode": (m.get("model_properties") or {}).get("mode"),
                         "node_model": {"provider": prov.get("provider"), "name": m.get("model"),
                                        "mode": (m.get("model_properties") or {}).get("mode") or "chat",
                                        "completion_params": {"temperature": 0.7}}})
    default = c.call("GET", "/workspaces/current/default-model", query={"model_type": a.type}).get("data")
    out({"default": default and {"provider": (default.get("provider") or {}).get("provider"), "model": default.get("model")},
         "models": [r for r in rows if r["status"] == "active"] or rows})


def cmd_datasets(a):
    c = current(a)
    r = c.call("GET", "/datasets", query={"page": 1, "limit": 100})
    out({"datasets": [{k: d.get(k) for k in ("id", "name", "description", "document_count", "indexing_technique")}
                      for d in r.get("data") or []]})


def cmd_apps(a):
    c = current(a)
    r = c.call("GET", "/apps", query={"page": 1, "limit": 50, "name": a.name})
    out({"apps": [{k: x.get(k) for k in ("id", "name", "mode", "updated_at")} for x in r.get("data") or []]})


def cmd_import(a):
    c = current(a)
    path = pathlib.Path(a.file)
    body = {"mode": "yaml-content", "yaml_content": path.read_text(encoding="utf-8")}
    if a.app_id:
        body["app_id"] = a.app_id
    r = c.call("POST", "/apps/imports", body)
    if r.get("status") == "pending":
        if not a.yes:
            out({"status": "pending", "import_id": r.get("id"), "imported_dsl_version": r.get("imported_dsl_version"),
                 "current_dsl_version": r.get("current_dsl_version"),
                 "next": "show the user the version difference; on a yes, re-run with --yes"}, 3)
        r = c.call("POST", f"/apps/imports/{r.get('id')}/confirm", {})
    ok = r.get("status") in ("completed", "completed-with-warnings")
    result = {"status": r.get("status"), "app_id": r.get("app_id"), "app_mode": r.get("app_mode"),
              "warnings": r.get("warnings") or [], "error": r.get("error") or None}
    if ok and r.get("app_id"):
        deps = c.call("GET", f"/apps/imports/{r['app_id']}/check-dependencies")
        result["missing_dependencies"] = deps.get("leaked_dependencies") or []
        result["console_url"] = f"{c.server}/app/{r['app_id']}/workflow"
    out(result, 0 if ok else 1)


def cmd_check_deps(a):
    c = current(a)
    out(c.call("GET", f"/apps/imports/{a.app_id}/check-dependencies"))


# ---------- commands: test ----------

def app_detail(c, app_id):
    return c.call("GET", f"/apps/{app_id}")


def draft_run(c, app_id, mode, inputs, query=None):
    if mode == "advanced-chat":
        path, body = f"/apps/{app_id}/advanced-chat/workflows/draft/run", {"query": query or "", "inputs": inputs, "files": []}
    elif mode == "workflow":
        path, body = f"/apps/{app_id}/workflows/draft/run", {"inputs": inputs, "files": []}
    else:
        fail(f"draft runs are for workflow and advanced-chat apps, this app is {mode}")
    resp = c.call("POST", path, body, stream=True)
    final, nodes, answer, errors = {}, [], [], []
    for ev in dify_api.read_sse(resp):
        d = ev.get("data") or {}
        kind = ev.get("event")
        if kind == "workflow_finished":
            final = d
        elif kind == "node_finished":
            nodes.append({"node_id": d.get("node_id"), "title": d.get("title"), "type": d.get("node_type"),
                          "status": d.get("status"), "error": d.get("error"), "elapsed_time": d.get("elapsed_time"),
                          "outputs": d.get("outputs")})
            if d.get("error"):
                errors.append({"node": d.get("title"), "error": d.get("error")})
        elif kind in ("message", "agent_message"):
            answer.append(ev.get("answer") or "")
        elif kind == "error":
            errors.append({"error": ev.get("message"), "code": ev.get("code")})
    return {"mode": mode, "status": final.get("status") or ("failed" if errors else None),
            "outputs": final.get("outputs"), "answer": "".join(answer) or None, "error": final.get("error"),
            "workflow_run_id": final.get("id"), "elapsed_time": final.get("elapsed_time"),
            "total_tokens": final.get("total_tokens"), "nodes": nodes, "errors": errors}


def cmd_run_draft(a):
    c = current(a)
    mode = app_detail(c, a.app_id).get("mode")
    r = draft_run(c, a.app_id, mode, dify_api.parse_json_arg(a.inputs), a.query)
    out(r, 0 if r["status"] == "succeeded" else 1)


def cmd_test_draft(a):
    c = current(a)
    mode = app_detail(c, a.app_id).get("mode")
    cases = dify_api.parse_json_arg("@" + a.cases)
    cases = cases.get("cases", cases) if isinstance(cases, dict) else cases
    results = []
    for case in cases:
        r = draft_run(c, a.app_id, mode, case.get("inputs") or {}, case.get("query"))
        if r.get("answer") is None:
            r.pop("answer")
        verdict, note = dify_api.check_case(case, r)
        r["nodes"] = [n for n in r["nodes"] if n["status"] != "succeeded"] or len(r["nodes"])
        results.append({"id": case.get("id"), "verdict": verdict, "note": note, "result": r})
    summary = {v: sum(1 for x in results if x["verdict"] == v) for v in ("pass", "fail", "needs_judgement")}
    out({"mode": mode, "summary": summary, "results": results}, 0 if summary["fail"] == 0 else 1)


def runs_path(mode, app_id):
    return f"/apps/{app_id}/advanced-chat/workflow-runs" if mode == "advanced-chat" else f"/apps/{app_id}/workflow-runs"


def cmd_runs(a):
    c = current(a)
    mode = app_detail(c, a.app_id).get("mode")
    r = c.call("GET", runs_path(mode, a.app_id), query={"limit": a.limit})
    out({"runs": [{k: x.get(k) for k in ("id", "status", "error", "elapsed_time", "total_tokens", "triggered_from", "created_at")}
                  for x in r.get("data") or []]})


def cmd_run_detail(a):
    c = current(a)
    run = c.call("GET", f"/apps/{a.app_id}/workflow-runs/{a.run_id}")
    nodes = c.call("GET", f"/apps/{a.app_id}/workflow-runs/{a.run_id}/node-executions")
    out({"run": {k: run.get(k) for k in ("id", "status", "error", "inputs", "outputs", "elapsed_time", "total_tokens")},
         "nodes": [{k: n.get(k) for k in ("node_id", "title", "node_type", "status", "error", "inputs", "outputs", "elapsed_time")}
                   for n in nodes.get("data") or []]})


# ---------- commands: release ----------

def cmd_publish(a):
    c = current(a)
    r = c.call("POST", f"/apps/{a.app_id}/workflows/publish", {"marked_name": a.name, "marked_comment": a.comment})
    out({"published": True, "created_at": r.get("created_at"), "result": r.get("result")})


def cmd_api_key(a):
    c = current(a)
    detail = app_detail(c, a.app_id)
    if not detail.get("enable_api"):
        c.call("POST", f"/apps/{a.app_id}/api-enable", {"enable_api": True})
    store = dify_api.load_keys()
    prev = store.get(a.alias) or {}
    if prev.get("app_id") == a.app_id and prev.get("key"):
        out({"alias": a.alias, "source": "existing", "key": dify_api.mask(prev["key"]), "base_url": prev.get("base_url")})
    # Listed keys come back masked, so a usable key must be created here.
    keys = [c.call("POST", f"/apps/{a.app_id}/api-keys", {})]
    source = "created"
    token = keys[0].get("token")
    base = detail.get("api_base_url") or default_service_base(c.server)
    store[a.alias] = {"key": token, "base_url": base.rstrip("/"), "app_id": a.app_id}
    dify_api.save_keys(store)
    out({"alias": a.alias, "source": source, "key": dify_api.mask(token), "base_url": base,
         "next": f"dify_api.py app test {a.alias} <cases.json>"})


def cmd_kb_key(a):
    c = current(a)
    r = c.call("POST", "/datasets/api-keys", {})
    token = r.get("token")
    if not token:
        fail("the server returned no key")
    store = dify_api.load_keys()
    store[a.alias] = {"key": token, "base_url": default_service_base(c.server)}
    dify_api.save_keys(store)
    out({"alias": a.alias, "key": dify_api.mask(token), "base_url": store[a.alias]["base_url"],
         "note": "workspace-wide Knowledge API key"})


def cmd_webapp(a):
    c = current(a)
    if a.enable or a.disable:
        c.call("POST", f"/apps/{a.app_id}/site-enable", {"enable_site": bool(a.enable)})
    d = app_detail(c, a.app_id)
    site = d.get("site") or {}
    kind = "workflow" if d.get("mode") == "workflow" else ("completion" if d.get("mode") == "completion" else "chat")
    url = f"{site.get('app_base_url', '').rstrip('/')}/{kind}/{site.get('access_token') or site.get('code')}" if site else None
    out({"enabled": d.get("enable_site"), "url": url if d.get("enable_site") else None, "mode": d.get("mode")})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("detect"); x.add_argument("server")
    x = s.add_parser("device-url"); x.add_argument("server"); x.add_argument("verification_uri")
    x = s.add_parser("login"); x.add_argument("server", nargs="?"); x.add_argument("--method", choices=["browser", "password", "email-code"], default="browser"); x.add_argument("--timeout", type=int, default=600)
    s.add_parser("logout"); s.add_parser("whoami"); s.add_parser("workspaces")
    x = s.add_parser("use-workspace"); x.add_argument("workspace_id")
    x = s.add_parser("models"); x.add_argument("--type", default="llm")
    s.add_parser("datasets")
    x = s.add_parser("apps"); x.add_argument("--name")
    x = s.add_parser("import"); x.add_argument("file"); x.add_argument("--app-id"); x.add_argument("--yes", action="store_true")
    x = s.add_parser("check-deps"); x.add_argument("app_id")
    x = s.add_parser("run-draft"); x.add_argument("app_id"); x.add_argument("--inputs"); x.add_argument("--query")
    x = s.add_parser("test-draft"); x.add_argument("app_id"); x.add_argument("cases")
    x = s.add_parser("runs"); x.add_argument("app_id"); x.add_argument("--limit", type=int, default=10)
    x = s.add_parser("run-detail"); x.add_argument("app_id"); x.add_argument("run_id")
    x = s.add_parser("publish"); x.add_argument("app_id"); x.add_argument("--name"); x.add_argument("--comment")
    x = s.add_parser("api-key"); x.add_argument("app_id"); x.add_argument("--alias", required=True)
    x = s.add_parser("kb-key"); x.add_argument("--alias", default="kb")
    x = s.add_parser("webapp"); x.add_argument("app_id"); g = x.add_mutually_exclusive_group(); g.add_argument("--enable", action="store_true"); g.add_argument("--disable", action="store_true")
    a = p.parse_args()
    handlers = {"detect": cmd_detect, "device-url": cmd_device_url, "login": cmd_login, "logout": cmd_logout, "whoami": cmd_whoami,
                "workspaces": cmd_workspaces, "use-workspace": cmd_use_workspace, "models": cmd_models,
                "datasets": cmd_datasets, "apps": cmd_apps, "import": cmd_import, "check-deps": cmd_check_deps,
                "run-draft": cmd_run_draft, "test-draft": cmd_test_draft, "runs": cmd_runs, "run-detail": cmd_run_detail,
                "publish": cmd_publish, "api-key": cmd_api_key, "kb-key": cmd_kb_key, "webapp": cmd_webapp}
    handlers[a.cmd](a)


if __name__ == "__main__":
    main()
