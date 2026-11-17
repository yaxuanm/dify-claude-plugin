#!/usr/bin/env python3
"""set_model_key.py: save a model provider's API key in Dify through difyctl.

Run this in your own terminal. It asks for each field without echoing what you
type and passes the values to difyctl on stdin, so the key never appears in the
chat, the shell history, a file, or this script's output.

  python3 set_model_key.py --provider langgenius/openai/openai --secret openai_api_key

Needs difyctl, signed in (or DIFY_SERVER and DIFY_TOKEN set).
"""
import argparse
import getpass
import json
import shutil
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", required=True, help="provider id from `difyctl describe model_provider`")
    p.add_argument("--secret", action="append", default=[], help="a secret field (asked without echo); repeatable")
    p.add_argument("--plain", action="append", default=[], help="a non-secret field (asked with echo); repeatable")
    p.add_argument("--difyctl", default=shutil.which("difyctl") or "difyctl")
    a = p.parse_args()
    if not a.secret and not a.plain:
        p.error("name at least one --secret or --plain field")
    if not sys.stdin.isatty():
        sys.exit("run this in an interactive terminal, so the key can be typed without echo")

    creds = {}
    for name in a.secret:
        value = getpass.getpass(f"{name} (hidden): ").strip()
        if not value:
            sys.exit(f"{name} is empty; nothing saved")
        creds[name] = value
    for name in a.plain:
        value = input(f"{name}: ").strip()
        if value:
            creds[name] = value

    cmd = [a.difyctl, "create", "model_provider", "credential", "--provider", a.provider, "--credentials", "@-", "--json"]
    try:
        r = subprocess.run(cmd, input=json.dumps(creds), capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("difyctl not found; install it first (see /dify:setup)")
    finally:
        creds.clear()
    text = (r.stdout or r.stderr or "").strip()
    if r.returncode == 0:
        print("Saved. Go back to Claude Code and reply \"done\".")
    else:
        print("Dify did not accept it; nothing was saved. Server message:")
        print(text[:2000])
        sys.exit(r.returncode or 1)


if __name__ == "__main__":
    main()
