#!/usr/bin/env python3
"""dify_api.py: call Dify's public Service API and Knowledge API.

Works with Dify Cloud and self-hosted Dify. Standard library only.
Every command prints one JSON object on stdout. API keys never appear in output.

Keys
  An app API key (app-...) belongs to one published app; a Knowledge API key
  (dataset-...) covers the workspace's knowledge bases. Keys are stored under an
  alias in ~/.config/dify-claude-plugin/keys.json (mode 0600), or passed in the
  DIFY_API_KEY environment variable with --alias env.

  key set <alias> [--base-url URL]   prompt for the key without echo and save it
  key list                           aliases, base URLs and key prefixes
  key remove <alias>

Apps (app key)
  app info <alias>                   name, mode, input form
  app run <alias> [--inputs JSON|@file] [--query TEXT] [--conversation-id ID]
  app test <alias> <cases.json>      run every case and apply exact/contains checks
  app run-detail <alias> <run_id>    a workflow run's status, outputs, error, timing
  app logs <alias> [--status failed|succeeded|stopped] [--limit N]

Knowledge (dataset key)
  kb list <alias>
  kb create <alias> --name NAME [--description TEXT]
  kb add <alias> <dataset_id> <path> [<path> ...]   .txt/.md as text, others as file upload
  kb status <alias> <dataset_id> <batch>
  kb retrieve <alias> <dataset_id> --query TEXT [--top-k N]

Base URL: Dify Cloud is https://api.dify.ai/v1 (default). Self-hosted is
https://<your-dify-host>/v1.
"""
import argparse
import getpass
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

CLOUD_BASE = "https://api.dify.ai/v1"
USER = "dify-claude-plugin"
CONF_DIR = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "dify-claude-plugin"
KEYS_FILE = CONF_DIR / "keys.json"
TEXT_EXT = {".txt", ".md", ".markdown"}


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def fail(message, **extra):
    out({"error": {"message": message, **extra}}, 1)


# ---------- key store ----------

def load_keys():
    try:
        return json.loads(KEYS_FILE.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        fail(f"cannot read {KEYS_FILE}: {e}")


def save_keys(keys):
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONF_DIR, 0o700)
    tmp = KEYS_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(keys, f, indent=2)
    os.replace(tmp, KEYS_FILE)


def resolve(alias):
    if alias == "env":
        key = os.environ.get("DIFY_API_KEY")
        if not key:
            fail("DIFY_API_KEY is not set")
        return {"key": key, "base_url": os.environ.get("DIFY_API_BASE", CLOUD_BASE).rstrip("/")}
    keys = load_keys()
    if alias not in keys:
        fail(f"no key saved as {alias!r}", hint=f"ask the user to run: python3 {pathlib.Path(__file__).resolve()} key set {alias}")
    return keys[alias]


def mask(key):
    prefix = key.split("-", 1)[0] + "-" if "-" in key[:9] else ""
    return prefix + "…" + key[-4:] if len(key) > 12 else "…"


# ---------- http ----------

def request(cfg, method, path, body=None, query=None, stream=False, multipart=None, timeout=300):
    url = cfg["base_url"] + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    headers = {"Authorization": f"Bearer {cfg['key']}", "User-Agent": "dify-claude-plugin"}
    data = None
    if multipart is not None:
        boundary = uuid.uuid4().hex
        data = encode_multipart(multipart, boundary)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(raw)
        except ValueError:
            detail = raw[:2000]
        fail(f"HTTP {e.code} from {method} {path}", http_status=e.code, server=detail)
    except urllib.error.URLError as e:
        fail(f"cannot reach {cfg['base_url']}: {e.reason}")
    if stream:
        return resp
    raw = resp.read().decode("utf-8", "replace")
    return json.loads(raw) if raw else {}


def encode_multipart(parts, boundary):
    buf = bytearray()
    for name, value in parts:
        buf += f"--{boundary}\r\n".encode()
        if isinstance(value, pathlib.Path):
            ctype = mimetypes.guess_type(value.name)[0] or "application/octet-stream"
            buf += f'Content-Disposition: form-data; name="{name}"; filename="{value.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode()
            buf += value.read_bytes()
        else:
            buf += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode() + str(value).encode()
        buf += b"\r\n"
    buf += f"--{boundary}--\r\n".encode()
    return bytes(buf)


def read_sse(resp):
    for line in resp:
        line = line.decode("utf-8", "replace").strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload:
                try:
                    yield json.loads(payload)
                except ValueError:
                    continue


# ---------- apps ----------

def parse_json_arg(value):
    if value is None:
        return {}
    if value.startswith("@"):
        value = pathlib.Path(value[1:]).read_text()
    try:
        return json.loads(value)
    except ValueError as e:
        fail(f"not valid JSON: {e}")


def app_mode(cfg):
    return request(cfg, "GET", "/info").get("mode")


def run_app(cfg, mode, inputs, query=None, conversation_id=None):
    started = time.time()
    if mode == "workflow":
        r = request(cfg, "POST", "/workflows/run", {"inputs": inputs, "response_mode": "blocking", "user": USER})
        d = r.get("data") or {}
        return {"mode": mode, "status": d.get("status"), "outputs": d.get("outputs"), "error": d.get("error"),
                "workflow_run_id": r.get("workflow_run_id") or d.get("id"), "elapsed_time": d.get("elapsed_time"),
                "total_tokens": d.get("total_tokens")}
    if mode == "completion":
        r = request(cfg, "POST", "/completion-messages", {"inputs": inputs, "response_mode": "blocking", "user": USER})
        return {"mode": mode, "status": "succeeded", "answer": r.get("answer"), "message_id": r.get("message_id")}
    # chat, advanced-chat, agent-chat: stream and fold (agent apps only stream).
    if not query:
        fail("this is a chat app: pass --query")
    body = {"inputs": inputs, "query": query, "response_mode": "streaming", "user": USER}
    if conversation_id:
        body["conversation_id"] = conversation_id
    resp = request(cfg, "POST", "/chat-messages", body, stream=True)
    answer, result = [], {"mode": mode, "status": "succeeded"}
    for ev in read_sse(resp):
        kind = ev.get("event")
        if kind in ("message", "agent_message"):
            answer.append(ev.get("answer", ""))
        elif kind == "message_replace":
            answer = [ev.get("answer", "")]
        elif kind == "workflow_finished":
            d = ev.get("data") or {}
            result.update(status=d.get("status"), outputs=d.get("outputs"), error=d.get("error"),
                          workflow_run_id=ev.get("workflow_run_id") or d.get("id"))
        elif kind == "message_end":
            meta = ev.get("metadata") or {}
            result["usage"] = meta.get("usage")
            result["retriever_resources"] = [
                {k: r.get(k) for k in ("dataset_name", "document_name", "score")} for r in meta.get("retriever_resources") or []
            ]
        elif kind == "error":
            result.update(status="failed", error=ev.get("message"), code=ev.get("code"))
        if ev.get("conversation_id"):
            result["conversation_id"] = ev["conversation_id"]
        if ev.get("message_id"):
            result["message_id"] = ev["message_id"]
    result["answer"] = "".join(answer)
    result["elapsed_time"] = round(time.time() - started, 2)
    return result


def check_case(case, result):
    """Apply exact/contains checks. 'judged' cases are left for the agent to grade."""
    expect = case.get("expect") or {}
    text = result.get("answer")
    if text is None:
        outputs = result.get("outputs") or {}
        field = expect.get("output")
        text = outputs.get(field) if field else json.dumps(outputs, ensure_ascii=False)
    text = "" if text is None else str(text)
    if result.get("status") not in ("succeeded", None):
        return "fail", f"run status {result.get('status')}: {result.get('error')}"
    kind = expect.get("check", "judged")
    if kind == "exact":
        ok = text.strip() == str(expect.get("value", "")).strip()
        return ("pass" if ok else "fail"), None if ok else f"expected exactly {expect.get('value')!r}"
    if kind == "contains":
        values = expect.get("value")
        values = values if isinstance(values, list) else [values]
        missing = [v for v in values if str(v) not in text]
        return ("pass" if not missing else "fail"), None if not missing else f"missing {missing}"
    return "needs_judgement", expect.get("rubric")


def cmd_app(a):
    cfg = resolve(a.alias)
    if a.action == "info":
        info = request(cfg, "GET", "/info")
        params = request(cfg, "GET", "/parameters")
        form = []
        for item in params.get("user_input_form") or []:
            for ftype, spec in item.items():
                form.append({"variable": spec.get("variable"), "type": ftype, "label": spec.get("label"),
                             "required": spec.get("required"), "options": spec.get("options") or None})
        out({"name": info.get("name"), "mode": info.get("mode"), "description": info.get("description"),
             "inputs": form, "opening_statement": params.get("opening_statement") or None})
    if a.action == "run":
        mode = app_mode(cfg)
        out(run_app(cfg, mode, parse_json_arg(a.inputs), a.query, a.conversation_id))
    if a.action == "test":
        cases = parse_json_arg("@" + a.cases)
        cases = cases.get("cases", cases) if isinstance(cases, dict) else cases
        mode = app_mode(cfg)
        results = []
        for c in cases:
            r = run_app(cfg, mode, c.get("inputs") or {}, c.get("query"))
            verdict, note = check_case(c, r)
            results.append({"id": c.get("id"), "verdict": verdict, "note": note, "result": r})
        summary = {v: sum(1 for r in results if r["verdict"] == v) for v in ("pass", "fail", "needs_judgement")}
        out({"mode": mode, "summary": summary, "results": results}, 0 if summary["fail"] == 0 else 1)
    if a.action == "run-detail":
        out(request(cfg, "GET", f"/workflows/run/{a.run_id}"))
    if a.action == "logs":
        r = request(cfg, "GET", "/workflows/logs", query={"status": a.status, "limit": a.limit, "page": 1})
        rows = []
        for row in r.get("data") or []:
            run = row.get("workflow_run") or {}
            rows.append({"workflow_run_id": run.get("id"), "status": run.get("status"), "error": run.get("error"),
                         "elapsed_time": run.get("elapsed_time"), "total_tokens": run.get("total_tokens"),
                         "created_at": row.get("created_at"), "created_from": row.get("created_from")})
        out({"total": r.get("total"), "logs": rows})


# ---------- knowledge ----------

def cmd_kb(a):
    cfg = resolve(a.alias)
    if a.action == "list":
        r = request(cfg, "GET", "/datasets", query={"page": 1, "limit": 100})
        out({"datasets": [{k: d.get(k) for k in ("id", "name", "description", "document_count", "indexing_technique")}
                          for d in r.get("data") or []]})
    if a.action == "create":
        r = request(cfg, "POST", "/datasets", {"name": a.name, "description": a.description or "",
                                               "indexing_technique": "high_quality", "permission": "only_me"})
        out({"id": r.get("id"), "name": r.get("name"), "indexing_technique": r.get("indexing_technique")})
    if a.action == "add":
        added = []
        for p in a.paths:
            path = pathlib.Path(p)
            if not path.is_file():
                fail(f"not a file: {p}")
            settings = {"indexing_technique": "high_quality", "process_rule": {"mode": "automatic"}}
            if path.suffix.lower() in TEXT_EXT:
                r = request(cfg, "POST", f"/datasets/{a.dataset_id}/document/create-by-text",
                            {"name": path.name, "text": path.read_text(encoding="utf-8"), **settings})
            else:
                r = request(cfg, "POST", f"/datasets/{a.dataset_id}/document/create-by-file",
                            multipart=[("data", json.dumps(settings)), ("file", path)])
            doc = r.get("document") or {}
            added.append({"file": p, "document_id": doc.get("id"), "batch": r.get("batch"),
                          "indexing_status": doc.get("indexing_status")})
        out({"added": added})
    if a.action == "status":
        r = request(cfg, "GET", f"/datasets/{a.dataset_id}/documents/{a.batch}/indexing-status")
        out({"documents": [{k: d.get(k) for k in ("id", "indexing_status", "completed_segments", "total_segments", "error")}
                           for d in r.get("data") or []]})
    if a.action == "retrieve":
        body = {"query": a.query}
        if a.top_k:
            body["retrieval_model"] = {"search_method": "semantic_search", "reranking_enable": False,
                                       "top_k": a.top_k, "score_threshold_enabled": False}
        r = request(cfg, "POST", f"/datasets/{a.dataset_id}/retrieve", body)
        out({"query": a.query, "records": [
            {"score": rec.get("score"), "document": ((rec.get("segment") or {}).get("document") or {}).get("name"),
             "content": ((rec.get("segment") or {}).get("content") or "")[:500]}
            for rec in r.get("records") or []]})


# ---------- keys ----------

def cmd_key(a):
    keys = load_keys()
    if a.action == "set":
        if not sys.stdin.isatty():
            fail("run this in your own terminal so the key is typed, not pasted into the chat")
        key = getpass.getpass(f"Dify API key for {a.alias} (input hidden): ").strip()
        if not key:
            fail("no key entered")
        keys[a.alias] = {"key": key, "base_url": (a.base_url or CLOUD_BASE).rstrip("/")}
        save_keys(keys)
        out({"saved": a.alias, "base_url": keys[a.alias]["base_url"], "key": mask(key), "file": str(KEYS_FILE)})
    if a.action == "list":
        out({"keys": [{"alias": k, "base_url": v["base_url"], "key": mask(v["key"])} for k, v in sorted(keys.items())]})
    if a.action == "remove":
        existed = keys.pop(a.alias, None) is not None
        save_keys(keys)
        out({"removed": a.alias if existed else None})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="group", required=True)

    k = sub.add_parser("key").add_subparsers(dest="action", required=True)
    s = k.add_parser("set"); s.add_argument("alias"); s.add_argument("--base-url")
    k.add_parser("list")
    r = k.add_parser("remove"); r.add_argument("alias")

    ap = sub.add_parser("app").add_subparsers(dest="action", required=True)
    x = ap.add_parser("info"); x.add_argument("alias")
    x = ap.add_parser("run"); x.add_argument("alias"); x.add_argument("--inputs"); x.add_argument("--query"); x.add_argument("--conversation-id")
    x = ap.add_parser("test"); x.add_argument("alias"); x.add_argument("cases")
    x = ap.add_parser("run-detail"); x.add_argument("alias"); x.add_argument("run_id")
    x = ap.add_parser("logs"); x.add_argument("alias"); x.add_argument("--status", choices=["failed", "succeeded", "stopped"]); x.add_argument("--limit", type=int, default=20)

    kb = sub.add_parser("kb").add_subparsers(dest="action", required=True)
    x = kb.add_parser("list"); x.add_argument("alias")
    x = kb.add_parser("create"); x.add_argument("alias"); x.add_argument("--name", required=True); x.add_argument("--description")
    x = kb.add_parser("add"); x.add_argument("alias"); x.add_argument("dataset_id"); x.add_argument("paths", nargs="+")
    x = kb.add_parser("status"); x.add_argument("alias"); x.add_argument("dataset_id"); x.add_argument("batch")
    x = kb.add_parser("retrieve"); x.add_argument("alias"); x.add_argument("dataset_id"); x.add_argument("--query", required=True); x.add_argument("--top-k", type=int)

    a = p.parse_args()
    {"key": cmd_key, "app": cmd_app, "kb": cmd_kb}[a.group](a)


if __name__ == "__main__":
    main()
