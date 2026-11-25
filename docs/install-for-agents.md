# Install the Dify plugin (instructions for an AI agent)

A user can tell their coding agent: "Install the Dify plugin by following <URL of this file>". If you are that agent, follow these steps in order. Talk to the user in their language and keep each message short.

## Rules

- Ask the user before running any installer that downloads from the internet, and say what it installs.
- Never ask for a password, API key or token in the chat. Sign-in happens in the user's browser; keys are typed in the user's own terminal.
- Do not publish, delete or change anything in the user's Dify workspace during installation.

## 1. Check Claude Code

Run `claude --version`. If it is missing, stop and point the user to <https://docs.claude.com/en/docs/claude-code/setup>. This plugin is for Claude Code.

If `CLAUDE_CODE_REMOTE` is `true`, you are in a cloud session, not on the user's computer. Say so before installing: the plugin will work here only with Dify Cloud or a Dify with a public URL, and anything on their computer (difyctl, its sign-in, a local Dify) cannot be reached. Recommend installing it in Claude Code on their own computer, and continue here only if they want it.

## 2. Add the marketplace and install the plugin

```bash
claude plugin marketplace add yaxuanm/dify-claude-plugin
claude plugin install dify@dify-plugins
```

If the user has a local copy instead, use its folder path in place of `yaxuanm/dify-claude-plugin`. Confirm with `claude plugin list` that `dify` is listed and enabled.

Already installed? Update it instead:

```bash
claude plugin marketplace update dify-plugins
claude plugin update dify@dify-plugins
```

## 3. Install difyctl (Dify's official CLI)

Needed for Dify Cloud and for any server with the official API. Ask first, then:

- macOS / Linux: `curl -fsSL https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install-cli.sh | sh`
- Windows (PowerShell): `irm https://raw.githubusercontent.com/langgenius/dify/main/cli/scripts/install.ps1 | iex`

It installs the latest release to `~/.local/bin` (Windows: `%LOCALAPPDATA%\difyctl\bin`). If that folder is not on PATH, tell the user how to add it. Check with `difyctl version`.

If the user only uses a self-hosted Dify without the official API, this step can be skipped; `/dify:setup` will tell them.

## 4. Hand over

Plugins load when Claude Code starts. Tell the user:

1. Run `/reload-plugins`, or restart Claude Code (exit and run `claude` again).
2. Run `/dify:setup`. It asks which Dify they use (Dify Cloud, their own server, or none yet), signs them in through the browser and checks the workspace has a model.
3. Run `/dify:doctor` any time to check everything is ready.
4. Then describe an app: `/dify:new-app <what it should do>`.

If you are running inside Claude Code yourself, you cannot use the new commands until the restart; say so instead of trying them.
