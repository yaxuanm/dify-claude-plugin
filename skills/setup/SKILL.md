---
name: setup
description: 'Connect Claude Code to a Dify workspace (Dify Cloud or self-hosted). Detects what the server supports and picks the path itself: difyctl when the server has the official /openapi/v1 API, otherwise a console sign-in. Use when the user runs /dify:setup, asks to connect or log in to Dify, or when any Dify task finds no working connection.'
argument-hint: '[server-url]'
---

# Connect to Dify

Goal: the user is signed in and has a workspace selected, without opening the Dify console, and without having to know which path the plugin uses.

Talk to the user in their language. Keep each message short: what you did, what they need to do. Below, `console` means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_console.py"`.

## 1. Server

If the user passed a URL (`$ARGUMENTS`), use it. Otherwise ask which Dify they use: **Dify Cloud** (`https://cloud.dify.ai`), their own server (the URL they open Dify at), or **none yet**. Never guess a self-hosted URL.

If they have no Dify yet, say so plainly and offer three ways forward, then wait for their pick:

1. **Dify Cloud** (quickest): sign up free at <https://cloud.dify.ai>, with any email or a Google / GitHub account, then come back and continue here with `https://cloud.dify.ai`. New accounts include trial model credits.
2. **Self-host with Docker**: follow <https://docs.dify.ai/getting-started/install-self-hosted> (needs Docker; about 10 minutes): clone `langgenius/dify`, then in `docker/` run `cp .env.example .env` and `docker compose up -d`. They open `http://localhost/install` to create the admin account and add a model provider key, then come back with that URL. To use the official API there, add `OPENAPI_ENABLED=true` to `docker/.env` and restart.
3. **No account for now**: the `new-app` skill can still write a checked `app.yml` to import later; it cannot test or publish it.

## 2. Detect

```bash
console detect <server>
```

Read `path`:

- `difyctl`: the server has the official API (Dify Cloud, and self-hosted or Enterprise servers with `OPENAPI_ENABLED` on). Go to **Path A**.
- `console`: no official API (self-hosted with `OPENAPI_ENABLED` off, or an older version). Go to **Path B**: browser sign-in.
- `null`: nothing answered as Dify at that URL. Tell the user what you tried, ask them to check the address (open it in the browser: it should show the Dify sign-in page; for self-hosted, make sure the server or Docker is running), and offer the three options above if they turn out not to have a Dify yet.

Remember the path for the rest of the session and tell the user in one line which one you use and why. Do not ask them to choose.

## Path A: difyctl (official API)

1. `sh "${CLAUDE_PLUGIN_ROOT}/scripts/difyctl-status.sh"`. If `installed` is false or `skill_install_supported` is false, ask to install, then run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/install-difyctl.sh"`. It installs the latest release; difyctl reads its commands from the server's catalog, so the latest works with any server that has the official API. Re-run it to upgrade. On Windows give the user `irm https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install.ps1 | iex` to run.

   Do not run `difyctl install skills`: this plugin already ships the same skill as `dify:difyctl`, and a second copy in `~/.claude/skills` would load twice.
2. If `env_token` from `detect` is true, the user has set `DIFY_SERVER` and `DIFY_TOKEN` in their shell (for CI or a headless machine). difyctl uses them and needs no login: run `difyctl describe workspace --json` to confirm, then go to step 4. Never ask the user to paste a token into the chat; they set it in their own shell before starting Claude Code.

   Otherwise run `difyctl login --resume --json`. If it prints an `email`, skip to step 4.
3. `difyctl login --server <server> --no-browser --no-wait --json`. Pass the printed `verification_uri` through `console device-url <server> <verification_uri>` and give the user its `url` (never the raw one: under Docker the server often prints an internal address such as `http://127.0.0.1:3000/device`) and the `user_code`. If `rewritten` is true, add one line: the server's `CONSOLE_WEB_URL` should be set to the address they open Dify at. Then ask them to approve and reply "done", and **end your turn**. Then run `difyctl login --resume --json` once. `status: pending` means not yet approved: say so and end the turn again. Add `--no-keyring` on machines without a lasting keychain (containers, remote boxes).
4. `difyctl get workspace --json`. Pin one with `difyctl use workspace <id> --json`, asking if there are several.

The `difyctl` skill's `references/setup.md` has the details.

## Path B: console sign-in

The user signs in on Dify's own sign-in page, in a temporary browser window the plugin opens. Every sign-in method works there (email code, Google, GitHub, SSO, password), and any human check is done by the user in a real browser. The plugin then keeps only the session cookies, in `~/.config/dify-claude-plugin/` with owner-only permissions. The window uses a throwaway profile, so the user's normal browser and its sign-ins are not touched.

1. Tell the user in one line: "A browser window will open on the Dify sign-in page. Sign in there as usual; it closes by itself when you are done."
2. Run, with a Bash timeout of 10 minutes (600000 ms), since it waits for the user:

   ```bash
   console login <server>
   ```

   It needs Chrome, Edge, Brave or Chromium installed. If none is found, ask the user for the browser's path and pass it as `DIFY_BROWSER=<path>`.
3. On `logged_in: true`, run `console whoami`. On a timeout or a closed window, offer to try again.
4. `console workspaces`. If the current one is not the one they want, `console use-workspace <id>`.

Fallbacks, only if the browser path cannot work (no desktop, remote machine): `password` or, on self-hosted servers that allow it, `email-code`, when `login_methods` lists them. These ask for secrets, so the user must run them in **their own terminal**, never in the chat:

```bash
python3 "<plugin root>/scripts/dify_console.py" login <server> --method password
```

## 3. Check for a model

Check that the workspace has at least one active LLM, following [`references/models.md`](references/models.md). If it has none, tell the user and help them add one before handing off; do not leave them to find out when the first app fails.

## 4. Confirm and hand off

Tell the user in two or three lines: server, account, workspace, which path, and the next step: "Tell me what app you need, or run `/dify:new-app <what it should do>`." If they already said what to build, go straight to the `new-app` skill.
