# Dify for Claude Code

Build, test and publish [Dify](https://dify.ai) apps without leaving Claude Code.

Connect your Dify workspace (Dify Cloud or self-hosted), describe the app you need in plain words, and Claude builds a working Workflow or Chatflow app in your workspace, runs test cases against it, and publishes it when you say yes.

> Status: prototype (v0.3.0). Not yet listed in any official plugin directory.

## What you get

| Component | What it does | Works on |
| --- | --- | --- |
| `/dify:setup` | Detects what your server supports, picks the path, signs you in, selects a workspace. | Any Dify, including Cloud |
| `/dify:new-app <description>` | Description to tested, published app with no trip to the console: spec, build, import, draft tests, then publish, web link and API key on your yes. | Any Dify, including Cloud |
| `/dify:build-dsl <description>` | Writes the app as a Dify DSL file and checks it offline; you import it in one click. | Any Dify, including Cloud |
| `/dify:test-app` | Runs acceptance cases against a published app through the Service API, reads failed runs and logs, suggests fixes. | Any Dify, including Cloud |
| `/dify:knowledge` | Creates a knowledge base from local files and tests retrieval through the Knowledge API. | Any Dify, including Cloud |
| `/dify:connect-app` | Turns a published Dify app into a tool Claude Code can call, through the app's built-in MCP server. | Any Dify, including Cloud |
| `difyctl` skill | Dify's official agent skill for the `difyctl` CLI: every operation the server publishes. | Self-hosted with `OPENAPI_ENABLED=true` |

Claude also uses these skills on its own when you mention Dify or ask to build an AI app, chatbot, RAG Q&A or workflow.

## Requirements

- Claude Code (CLI, desktop or IDE extension).
- A Dify account: [Dify Cloud](https://cloud.dify.ai) or a self-hosted / Enterprise server.
- On Dify Cloud (and self-hosted servers without the official API): an account with a password, since sign-in happens in your terminal. Accounts created with an email code or Google/GitHub can set one under Account settings.
- Python 3 for the offline DSL check and the API helper (`build-dsl` needs PyYAML).
- macOS, Linux or Windows. `difyctl` is installed for you on first use (one binary in `~/.local/bin`).

## Install

Inside Claude Code:

```text
/plugin marketplace add yaxuanm/dify-claude-plugin
/plugin install dify@dify-plugins
/reload-plugins
```

Or from a shell:

```bash
claude plugin marketplace add yaxuanm/dify-claude-plugin
claude plugin install dify@dify-plugins
```

## Quick start

```text
/dify:setup
/dify:new-app A support bot that answers questions about our refund policy, in the customer's language
```

1. `/dify:setup` asks for your server (Dify Cloud or your own URL), shows a link and a code, and waits while you approve it in the browser.
2. `/dify:new-app` drafts a spec, asks only what is missing, then builds the app in your workspace and tests it.
3. You review the results and say yes to publish. Claude returns the web app link.

## How it works

`/dify:setup` checks two public endpoints on your server and picks a path for you:

- **Official API** (`/openapi/v1`, on when the server sets `OPENAPI_ENABLED=true`): the plugin uses [`difyctl`](https://github.com/langgenius/dify/tree/main/cli), Dify's official CLI. You approve a device code in the browser once. Tokens live in your OS keychain.
- **Console sign-in** (Dify Cloud today, and self-hosted servers without the official API): you run one login command in your own terminal and type your email and password there. The password is never stored or shown to Claude; only the session cookies are saved, in `~/.config/dify-claude-plugin/` (owner-only). The plugin then uses the same web API the Dify console uses. That API is internal to Dify and can change between versions.

Either way:

- Working files for each app (`spec.md`, `cases.json`, `app.yml`) are kept in `dify-apps/<app-slug>/` (or `difyctl/<app-slug>/`) in your current folder.
- App and Knowledge API keys are created for you and stored in `~/.config/dify-claude-plugin/keys.json` (mode `0600`); they are never printed.
- Nothing is published, deleted or opened to the public without your explicit yes.

## Privacy

The plugin collects no data of its own. `difyctl` and the plugin's scripts talk only to the Dify server you sign in to or configure (files you upload with `/dify:knowledge` go to that server's knowledge base); that server's privacy policy applies (Dify Cloud: <https://dify.ai/privacy>). The installer downloads `difyctl` from GitHub releases of `langgenius/dify`.

## Development

```bash
claude --plugin-dir .                         # try the plugin without installing
claude plugin validate . --profile directory  # the checks the plugin directory runs
sh scripts/sync-difyctl-skill.sh              # refresh skills/difyctl from langgenius/dify
```

Layout:

```text
.claude-plugin/plugin.json        plugin manifest
.claude-plugin/marketplace.json   makes this repo installable as a marketplace
skills/setup/                     /dify:setup
skills/new-app/                   /dify:new-app
skills/build-dsl/                 /dify:build-dsl (templates + offline DSL reference)
skills/test-app/                  /dify:test-app
skills/knowledge/                 /dify:knowledge
skills/connect-app/               /dify:connect-app
skills/difyctl/                   official difyctl skill (synced from upstream)
scripts/                          difyctl status/installer, console client, DSL validator, Service/Knowledge API helper, upstream sync
assets/icon.png                   directory icon
```

## License

Apache-2.0 for this repository's own files. `skills/difyctl/` is copied from [langgenius/dify](https://github.com/langgenius/dify); see [NOTICE](NOTICE).
