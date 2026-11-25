#!/usr/bin/env python3
"""doctor.py: one read-only health report for the Dify plugin.

Combines the server check (dify_console.py detect), the difyctl install check
(difyctl-status.sh), sign-in state, current workspace, available LLMs and the
saved API keys (masked). It changes nothing, logs in to nothing and never
prints a secret. Prints one JSON object.

usage: doctor.py [server-url]
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    text = (r.stdout or "").strip()
    try:
        return json.loads(text), None if r.returncode == 0 else (r.stderr or text)[:500]
    except ValueError:
        return None, (r.stderr or text or f"exit {r.returncode}")[:500]


def py(script, *args):
    return run([sys.executable, "-I", str(HERE / script), *args])


def find(obj, key):
    """First value for key anywhere in a JSON tree."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = find(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find(v, key)
            if found is not None:
                return found
    return None


def rows(obj):
    """Rows of a difyctl list result, whatever the envelope."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("data", "items", "rows", "models", "result"):
            if isinstance(obj.get(k), list):
                return obj[k]
            if isinstance(obj.get(k), dict):
                inner = rows(obj[k])
                if inner:
                    return inner
    return []


def version_tuple(v):
    """'v1.20.0' or '1.20.0-rc1' -> (1, 20, 0); unknown -> ()."""
    import re
    m = re.match(r"v?(\d+)\.(\d+)(?:\.(\d+))?", str(v).strip())
    return tuple(int(x or 0) for x in m.groups()) if m else ()


def main():
    server_arg = sys.argv[1] if len(sys.argv) > 1 else None
    report = {"plugin_version": None, "difyctl": None, "server": None, "path": None,
              "signed_in": False, "account": None, "workspace": None,
              "models": {"active_count": None, "active": []}, "keys": [], "problems": [], "runtime": None}
    problems = report["problems"]

    # First: is this the user's own computer? In a cloud sandbox nothing on their computer is reachable,
    # so "not installed / not signed in" would be misleading.
    where, _ = py("dify_console.py", "where")
    report["runtime"] = where
    remote = bool((where or {}).get("remote"))
    if remote:
        # The plugin is not meant for cloud sessions: say so and stop.
        problems.append(where["note"])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    try:
        report["plugin_version"] = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text()).get("version")
    except (OSError, ValueError):
        pass

    status, err = run(["sh", str(HERE / "difyctl-status.sh")])
    report["difyctl"] = status or {"error": err}
    difyctl = (status or {}).get("path") if (status or {}).get("installed") else None

    # Which server: argument, else the console session, else ask.
    state_file = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "dify-claude-plugin" / "console.json"
    try:
        console_server = json.loads(state_file.read_text()).get("current")
    except (OSError, ValueError):
        console_server = None
    server = server_arg or os.environ.get("DIFY_SERVER") or console_server

    resume = None
    if difyctl:
        resume, _ = run([difyctl, "login", "--resume", "--json"])
        if not server and resume:
            server = find(resume, "server") or find(resume, "host")

    if not server:
        if remote:
            problems.append("no Dify is set up in this cloud session. That is expected: the user's own setup "
                            "lives on their computer. Only connect here if they want to use Dify Cloud or a Dify "
                            "with a public URL (/dify:setup)")
        else:
            problems.append("no server known: run /dify:setup, or pass the server URL")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    detect, err = py("dify_console.py", "detect", server)
    if not detect:
        problems.append(f"server check failed: {err}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    report["server"] = detect.get("server")
    report["path"] = detect.get("path")
    report["detect"] = {k: detect.get(k) for k in ("cloud", "edition", "openapi", "openapi_version", "env_token", "console_reachable")}

    if detect.get("network_blocked"):
        problems.append(detect.get("next"))
    elif detect.get("path") is None:
        if remote:
            problems.append(f"{report['server']} cannot be reached from this cloud sandbox. If it is on the user's "
                            "computer or network, that is expected; use Claude Code on their computer for it")
        else:
            problems.append("no Dify answered at this URL: check the address and that the server is running")
    elif detect.get("path") == "difyctl":
        if not difyctl:
            problems.append("difyctl is not installed in this cloud sandbox (the one on the user's computer is not "
                            "visible here): /dify:setup can install a separate copy here if they want to use this server "
                            "from this session" if remote else "difyctl is not installed: run /dify:setup to install it")
        else:
            email = find(resume, "email") if resume else None
            if email or detect.get("env_token"):
                report["signed_in"] = True
                report["account"] = email or "DIFY_TOKEN"
                ws, _ = run([difyctl, "describe", "workspace", "--json"])
                if ws:
                    report["workspace"] = {"id": find(ws, "id"), "name": find(ws, "name")}
                models, err = py("model_status.py", "--difyctl", difyctl)
                if models and "active_count" in models:
                    report["models"] = {"active_count": models["active_count"], "complete": models.get("complete"),
                                        "active": [f"{m.get('provider')}/{m.get('model')}" for m in models.get("active") or []][:20]}
                else:
                    problems.append(f"could not list models: {err}")
            else:
                problems.append("difyctl is not signed in to this server: run /dify:setup")
    else:  # console path
        who, err = py("dify_console.py", "whoami")
        if who and not who.get("error") and (who.get("server") or "").rstrip("/") == report["server"]:
            report["signed_in"] = True
            report["account"] = who.get("email")
            report["workspace"] = who.get("workspace")
            models, err = py("dify_console.py", "models")
            if models and not models.get("error"):
                report["models"] = {"active_count": models.get("active_count"),
                                    "active": [f"{m.get('provider')}/{m.get('model')}" for m in models.get("models") or []
                                               if m.get("status") == "active"][:20],
                                    "default": models.get("default")}
        else:
            problems.append("not signed in to this server: run /dify:setup (opens a sign-in window)")

    # difyctl reads commands from the server, but an older client can miss newer flags and fixes.
    cver, sver = (report["difyctl"] or {}).get("version"), (report.get("detect") or {}).get("openapi_version")
    if isinstance(sver, dict):  # detect returns the whole /_version body: {"version": "1.20.0", ...}
        sver = sver.get("version")
    if difyctl and version_tuple(cver or "") and version_tuple(sver or "") and version_tuple(cver) < version_tuple(sver):
        problems.append(f"difyctl {cver} is older than the server ({sver}): re-run "
                        "scripts/install-difyctl.sh, or /dify:setup, to upgrade")

    if report["signed_in"] and report["models"].get("active_count") == 0:
        problems.append("the workspace has no active LLM: run /dify:setup to add a model provider")

    keys, _ = py("dify_api.py", "key", "list")
    report["keys"] = (keys or {}).get("keys", [])

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
