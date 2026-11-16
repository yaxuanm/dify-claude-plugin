---
name: setup
description: 'Connect Claude Code to a Dify workspace: install difyctl, sign in to Dify Cloud or a self-hosted Dify server, and pick a workspace. Use when the user runs /dify:setup, asks to connect or log in to Dify, or when any Dify task finds difyctl missing or not logged in.'
argument-hint: '[server-url]'
---

# Connect to Dify

Goal: in a few minutes the user has difyctl installed, is signed in, and has a workspace pinned. Then offer to build their first app.

**Know the limit first.** difyctl talks to the server's `/openapi/v1` API. That API is off by default: the server admin must set `OPENAPI_ENABLED=true` (and the server must be a recent Dify release). Dify Cloud may not have it on. When difyctl cannot sign in, the user still has two paths that need no CLI, so never leave them stuck:

- build an app as a DSL file and import it in the console: the `build-dsl` skill (`/dify:build-dsl`);
- use an app they already have from Claude Code: the `connect-app` skill (`/dify:connect-app`).

Work through the steps in order and skip a step that is already done. Talk to the user in their language. Keep each message short: what you did, what they need to do.

The full difyctl reference is the `difyctl` skill in this plugin. Its `references/setup.md` is the authority on login; this skill is the guided path through it.

## 1. Choose the server and check its API

If the user passed a URL as the argument (`$ARGUMENTS`), use it. Otherwise ask, with these choices:

- **Self-hosted or Enterprise**: the URL they open the Dify console at, for example `https://dify.example.com`
- **Dify Cloud**: `https://cloud.dify.ai`.

Check the API is on before installing anything (no login needed; works for Cloud too):

```bash
curl -s -o /dev/null -w '%{http_code}\n' <url>/openapi/v1/_version
```

`200`: go on. `404` on Dify Cloud: Cloud does not offer this API yet; skip the rest of this skill and offer `build-dsl` and `connect-app`. `404` on a self-hosted server: the API is off or the server is too old. Tell the user their admin must upgrade Dify and set `OPENAPI_ENABLED=true` in the API service's environment, and leave `ENABLE_OAUTH_BEARER` unset or `true` (Docker Compose: add the line to `docker/.env`, then `docker compose up -d`). Meanwhile offer `build-dsl` and `connect-app`.

Never guess a self-hosted URL. `--insecure` (plain `http://`, no TLS check) is for a local dev server only; use it only when the user gives an `http://localhost` style URL and says it is local.

## 2. Check difyctl

Run:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/difyctl-status.sh"
```

- `installed: false`: go to step 3.
- `installed: true` but `on_path: false`: use the printed `path` for every difyctl call in this session, and tell the user once how to add its folder to `PATH`.
- `skill_install_supported: false`: this is a v1 build. Tell the user it is too old for this plugin and go to step 3 to upgrade.

## 3. Install difyctl (only if missing or too old)

Ask before installing. Say that it downloads Dify's official installer from GitHub and puts one binary in `~/.local/bin`. If the user is on a self-hosted Dify, ask for its version first and pass it as `DIFY_VERSION` so the CLI matches the server.

macOS and Linux:

```bash
DIFY_VERSION=<server version, or leave unset for latest> sh "${CLAUDE_PLUGIN_ROOT}/scripts/install-difyctl.sh"
```

Windows: ask the user to run this in PowerShell, since it changes their user profile:

```powershell
irm https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install.ps1 | iex
```

Then run step 2 again. If the download fails (no network, GitHub rate limit), show the error and suggest setting `GITHUB_TOKEN`, or installing on a machine with access.

## 4. Sign in

First check for an existing session:

```bash
difyctl login --resume --json
```

If it prints an `email`, the user is signed in. Skip to step 5.

Otherwise start the device login. It never blocks:

```bash
difyctl login --server <url> --no-browser --no-wait --json
```

Show the user the `verification_uri` and `user_code` from the result, and how long it is valid (`expires_in` seconds). Ask them to open the link, approve the code, and reply "done". **End your turn here.** Do not poll, sleep or start a background job.

When they reply, run `difyctl login --resume --json` once.

- `email` printed: signed in.
- `status: pending`: not approved yet. Tell them and end your turn again.
- Expired or denied: start this step again.

If the token may not survive between sessions (a container, a remote dev box, Linux without a keyring), add `--no-keyring` to the `--no-wait` call. See the `difyctl` skill's `references/setup.md`.

## 5. Pick a workspace

```bash
difyctl get workspace --json
```

One workspace: pin it. Several: show their names and ask which one to use. Then:

```bash
difyctl use workspace <id> --json
difyctl describe workspace --json
```

## 6. Confirm and hand off

Run `difyctl get console_app --limit 5 --json` as a smoke test. Then tell the user in two or three lines:

- which server, account and workspace are connected;
- how many apps they already have (or that the workspace is empty);
- what to do next: "Tell me what app you need, or run `/dify:new-app <what it should do>`."

If the user already said what they want to build, go straight to the `new-app` skill instead of asking.

## When something fails

- Exit code 4 or `not_logged_in`: run step 4 again.
- Exit code 6 (catalog unavailable) or a 404: the server is older than this difyctl, unreachable, or has `OPENAPI_ENABLED` off. Show `difyctl version --json`, explain, and offer `build-dsl` / `connect-app`.
- Any other error: show the error `code` and `message` from the JSON envelope, and do not work around it.
