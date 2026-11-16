# Dify for Claude Code

Build, test and publish [Dify](https://dify.ai) apps without leaving Claude Code.

Connect your Dify workspace (Dify Cloud or self-hosted), describe the app you need in plain words, and Claude builds a working Workflow or Chatflow app in your workspace, runs test cases against it, and publishes it when you say yes.

> Status: prototype (v0.1.0). Not yet listed in any official plugin directory.

## What you get

| Component | What it does |
| --- | --- |
| `/dify:setup` | Guided connection: installs `difyctl` if needed, signs you in with a browser device code, and pins a workspace. |
| `/dify:new-app <description>` | From a description to a tested app: short spec, plan, build, acceptance tests, then publish on your yes. |
| `difyctl` skill | Dify's official agent skill for the `difyctl` CLI. Teaches Claude to discover and run every operation your Dify server publishes: apps, runs, DSL import/export, plugins, models, knowledge bases, workspace skills. |

Claude also uses these skills on its own when you mention Dify or ask to build an AI app, chatbot, RAG Q&A or workflow.

## Requirements

- Claude Code (CLI, desktop or IDE extension).
- A Dify account: [Dify Cloud](https://cloud.dify.ai) or a self-hosted / Enterprise server whose version ships `difyctl`.
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

The plugin drives Dify through [`difyctl`](https://github.com/langgenius/dify/tree/main/cli), Dify's official CLI. `difyctl` has no hard-coded business commands: the server publishes a catalog of operations and each one becomes a command, so the plugin stays current as Dify adds features.

- Sign-in uses the OAuth device flow. Tokens are stored by `difyctl` in your OS keychain (or a `0600` file where there is none), never in the plugin or your project.
- Working files for each app (`spec.md`, `plan.md`, `app.yml`) are kept in `difyctl/<app-slug>/` in your current folder.
- Nothing is published, deleted or opened to the public without your explicit yes.

## Privacy

The plugin itself collects no data and sends nothing anywhere. `difyctl` talks only to the Dify server you sign in to; that server's privacy policy applies (Dify Cloud: <https://dify.ai/privacy>). The installer downloads `difyctl` from GitHub releases of `langgenius/dify`.

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
skills/difyctl/                   official difyctl skill (synced from upstream)
scripts/                          status check, installer wrapper, upstream sync
assets/icon.png                   directory icon
```

## License

Apache-2.0 for this repository's own files. `skills/difyctl/` is copied from [langgenius/dify](https://github.com/langgenius/dify); see [NOTICE](NOTICE).
