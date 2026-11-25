---
name: connect-app
description: 'Use a published Dify app (Workflow, Chatflow or Agent) as a tool inside Claude Code, through the MCP server Dify gives every app. Works on Dify Cloud and self-hosted. Use when the user runs /dify:connect-app, or wants Claude Code to call, run or query one of their Dify apps, workflows, agents or knowledge-base Q&A bots.'
argument-hint: '[app name]'
---

# Connect a Dify app to Claude Code

Goal: one of the user's Dify apps becomes a tool Claude can call in this and later sessions. Typical uses: ask the company knowledge-base bot, run a review or extraction workflow on files in the repo, trigger an internal automation.

Every Dify app can be published as an MCP server (streamable HTTP). Its URL looks like `https://<dify-api-host>/mcp/server/<code>/mcp`. The URL itself grants access to the app, so treat it like a password.

## 1. Get the URL

The URL never goes through the chat. If the user pastes one anyway, do not repeat it, use it once for step 2, and suggest they regenerate it on the MCP Server card afterwards, because chat history keeps it.

Tell them how to get one:

1. Open the app in Dify. It must be **published**.
2. On the app's **Overview** page (Monitoring), find the **MCP Server** card (中文界面：「MCP 服务」).
3. Click to enable it. Dify asks for a description of the tool and of each input; write one that says when to use the app. Claude reads it to decide when to call the tool.
4. Copy the **Server URL**. Do not paste it here; step 2 reads it in their terminal.

**Name the tool in English.** Claude Code builds tool names from the app's MCP tool name, and non-Latin characters become underscores: a Chinese app name turns into `mcp__dify-<slug>__________`, which nobody can recognise in permission prompts or allow lists. If the app name is not in English, ask the user to give the app an English name in Dify (the tool name follows it) before enabling the card, and keep the Chinese name in the description.

## 2. Add it to Claude Code

Pick a short server name from the app name: `dify-<app-slug>` (lowercase, hyphens).

Ask where it should be available:

- **All my projects** (default): `--scope user`. The URL stays in the user's own Claude Code settings.
- **This project only, just me**: `--scope local`.
- Do not use `--scope project` unless the user insists: it writes the URL into `.mcp.json`, which is usually committed and would leak access to the app.

Give the user this to run in **their own terminal** (bash or zsh). It asks for the URL without echoing it and never shows it to Claude:

```bash
printf 'Dify MCP Server URL: '; read -rs U; echo; case "$U" in */mcp/server/*/mcp) claude mcp add --transport http --scope user dify-<app-slug> "$U" ;; *) echo "That does not look like a Dify MCP Server URL (…/mcp/server/<code>/mcp)" ;; esac; unset U
```

Swap `--scope user` for `--scope local` if they chose this project only. Wait for them to say it is done.

In a cloud sandbox (`console where` says `remote`), the user's own terminal is on their computer, so this command adds the tool to Claude Code there, not to this sandbox. That is usually what they want. The sandbox also needs the Dify API host in its allowed domains to call the app.

## 3. Load and test

Tell the user to run `/mcp` (or restart Claude Code) so the new server loads, then check that `dify-<app-slug>` shows as connected.

Then make one real call with an input that matches the app's purpose, and show the result. If the call fails:

- `Server Not Found`: the MCP Server is off, the app is unpublished, or the URL was regenerated. Get a fresh URL from the card.
- Input errors: the tool's input schema comes from the app's start variables (Chatflow also takes `query`). Re-read the tool description and try again.
- The app's own run failed (model or tool error): fix it in the Dify console; the connection is fine.

## 4. Close

Summarize: which app is connected, under what name, in which scope, and one example prompt the user can use, for example "Ask dify-policy-bot what the refund window is for annual plans."

To remove it later: `claude mcp remove dify-<app-slug> --scope <scope>`.
