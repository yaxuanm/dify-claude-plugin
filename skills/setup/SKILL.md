---
name: setup
description: 'Connect Claude Code to a Dify workspace (Dify Cloud or self-hosted). Detects what the server supports and picks the path itself: difyctl when the server has the official /openapi/v1 API, otherwise a console sign-in. Use when the user runs /dify:setup, asks to connect or log in to Dify, or when any Dify task finds no working connection.'
argument-hint: '[server-url]'
---

# Connect to Dify

Goal: the user is signed in and has a workspace selected, without opening the Dify console, and without having to know which path the plugin uses.

Talk to the user in their language. Keep each message short: what you did, what they need to do. Below, `console` means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_console.py"`.

## 1. Server

If the user passed a URL (`$ARGUMENTS`), use it. Otherwise ask: **Dify Cloud** (`https://cloud.dify.ai`) or their own server (the URL they open Dify at). Never guess a self-hosted URL.

## 2. Detect

```bash
console detect <server>
```

Read `path`:

- `difyctl`: the server has the official API. Go to **Path A**.
- `console`: no official API (Dify Cloud today, or self-hosted with `OPENAPI_ENABLED` off). Go to **Path B**.
- `null`: unreachable. Ask the user to check the URL.

Remember the path for the rest of the session and tell the user in one line which one you use and why. Do not ask them to choose.

## Path A: difyctl (official API)

1. `sh "${CLAUDE_PLUGIN_ROOT}/scripts/difyctl-status.sh"`. If `installed` is false or `skill_install_supported` is false, ask to install, then run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/install-difyctl.sh"` (set `DIFY_VERSION` to the server's version when known). On Windows give the user `irm https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install.ps1 | iex` to run.
2. `difyctl login --resume --json`. If it prints an `email`, skip to step 4.
3. `difyctl login --server <server> --no-browser --no-wait --json`. Give the user the `verification_uri` and `user_code`, ask them to approve and reply "done", and **end your turn**. Then run `difyctl login --resume --json` once. `status: pending` means not yet approved: say so and end the turn again. Add `--no-keyring` on machines without a lasting keychain (containers, remote boxes).
4. `difyctl get workspace --json`. Pin one with `difyctl use workspace <id> --json`, asking if there are several.

The `difyctl` skill's `references/setup.md` has the details.

## Path B: console sign-in

1. `login_methods` from detect lists what works from a terminal. On Dify Cloud that is `password` only: Cloud's emailed sign-in codes need a browser human check that a terminal cannot pass.
2. Ask the user to open **their own terminal** (not this chat) and run the command below, typing their email and password there. The password is never stored or shown to you; only the session cookies are saved, in `~/.config/dify-claude-plugin/` with owner-only permissions. Print the full path for them (`echo "${CLAUDE_PLUGIN_ROOT}"`).

   ```bash
   python3 "<plugin root>/scripts/dify_console.py" login <server>
   # self-hosted servers that allow it: add --method email-code
   ```

   Then end your turn and wait for "done". Never ask for a password or code in the chat. If the user pastes one anyway, do not repeat it and suggest they change it.

3. When they reply, run `console whoami`. If it fails, show the error message.
4. `console workspaces`. If the current one is not the one they want, `console use-workspace <id>`.

If `password` is not in `login_methods`, or the account has no password (it signed up with Google, GitHub or an email code): tell the user they can set a password once in Dify (avatar → Account → set password) and then run the login again. Until then offer `build-dsl` (file import by hand) and `connect-app`.

## 3. Confirm and hand off

Tell the user in two or three lines: server, account, workspace, which path, and the next step: "Tell me what app you need, or run `/dify:new-app <what it should do>`." If they already said what to build, go straight to the `new-app` skill.
