#!/usr/bin/env python3
"""model_status.py: does the workspace have an LLM ready to use?

Path A (difyctl) helper. Reads every page of `difyctl get model --model-type llm`
and prints one JSON object: active_count, the active models, and whether every
page was read. Read-only.

usage: model_status.py [--difyctl PATH] [--model-type llm]
"""
import argparse
import json
import shutil
import subprocess
import sys


def call(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout), r.returncode
    except ValueError:
        return None, r.returncode or 1


def rows(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("data", "items", "rows", "models", "result"):
            v = obj.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                inner = rows(v)
                if inner:
                    return inner
    return []


def has_more(obj):
    if isinstance(obj, dict):
        if obj.get("has_more") is True:
            return True
        return any(has_more(v) for v in obj.values() if isinstance(v, dict))
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--difyctl", default=shutil.which("difyctl") or "difyctl")
    p.add_argument("--model-type", default="llm")
    a = p.parse_args()
    base = [a.difyctl, "get", "model", "--model-type", a.model_type, "--json"]

    first, code = call(base + ["--limit", "100"])
    paged = True
    if first is None or code != 0:
        first, code = call(base)
        paged = False
    if first is None:
        print(json.dumps({"error": "difyctl get model failed; is difyctl installed and signed in?"}))
        sys.exit(1)

    all_rows, page, complete, result = rows(first), 1, True, first
    while has_more(result):
        if not paged:
            complete = False
            break
        page += 1
        result, code = call(base + ["--limit", "100", "--page", str(page)])
        if result is None or code != 0 or page > 50:
            complete = False
            break
        all_rows += rows(result)

    active = [r for r in all_rows if isinstance(r, dict) and r.get("status") == "active"]
    statuses = sorted({str(r.get("status")) for r in all_rows if isinstance(r, dict)})
    print(json.dumps({
        "active_count": len(active),
        "total": len(all_rows),
        "complete": complete,
        "statuses_seen": statuses,
        "active": [{"provider": r.get("provider"), "model": r.get("model") or r.get("name"),
                    "node_model": r.get("node_model")} for r in active][:30],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
