---
name: new-app
description: 'Turn a plain-language description into a working, tested Dify app (Workflow or Chatflow) in the user''s workspace, end to end and without opening the Dify console: spec, build, import, draft tests, then publish, web app link and API key on the user''s yes. Works on Dify Cloud and self-hosted. Use when the user runs /dify:new-app, or asks to build, create or prototype an AI app, chatbot, agent, RAG / knowledge-base Q&A, or automation workflow on Dify.'
argument-hint: '<what the app should do>'
---

# Build a new Dify app, end to end

Goal: the user describes what they need and ends up with a Dify app that is built in their workspace, has passed real test cases, and, on their yes, is published with a web link and an API key. The user never has to open the Dify console.

The user's request: $ARGUMENTS

## 0. Connection

Use the path the `setup` skill found in this session. If there is none yet, run the `setup` skill first, then come back; if the user has no Dify at all, it explains how to get one. Before writing the spec, check that the workspace has an active LLM as in `${CLAUDE_PLUGIN_ROOT}/skills/setup/references/models.md`; if it has none, say so and help the user add one first. Building without a connection gives a worse app, because only a signed-in session can see the workspace's models, plugins and knowledge bases. Two paths, same phases:

- **Path A, difyctl** (server has the official `/openapi/v1`).
- **Path B, console** (`dify_console.py`; servers without the official API).

If the user will not sign in at all, follow Path B steps 1 and 2 without the `console` lookups and hand over only the checked `app.yml`. Use the template's default model and only the node types in the reference, and tell them plainly: import it in Dify (Studio → Create app → Import DSL file), pick a model in each LLM node, then run the cases from `spec.md`. Offer to finish the job once they sign in.

**App name:** propose a short English name (for example `feedback-sentiment`) even when the user writes in another language, and put the native-language title in the description. Dify turns the app name into the tool name when the app is later connected through MCP (`/dify:connect-app`), and non-Latin characters become underscores there.

Below, `console` means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_console.py"` and `dify_api` means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_api.py"`.

## Path A: difyctl

Follow the `difyctl` skill's `references/build-workflow.md` (spec, plan, build, hand over, each with a human gate). For a first app keep it small: at most three questions, 2 to 5 requirements, 3 acceptance cases, the fewest nodes that meet the spec, built in one or two slices. Its rules win over anything here.

After hand over, on the user's yes to go live: publish and turn on the web app with the operations `difyctl help publish` and `difyctl help web app` find. For an API key, look for one with `difyctl help api key`. If it finds one and it would print the key, give the user that command to run in their own terminal, piped into `dify_api key set <app-slug> --base-url <server>/v1`, so the key never reaches the chat. If the catalog has none, say so plainly, then give the user the console path (app → **API Access** → **API Key** → create) and have them save it in their own terminal with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_api.py" key set <app-slug> --base-url <server>/v1`. Never ask for the key in the chat. Then smoke test with `dify_api app test <app-slug> <cases.json>`.

## Path B: console

### 1. Spec (one gate)

Restate the request, ask only what is missing (at most three questions, one at a time), pick Workflow or Chatflow with one line on why. Look up real resources first so nothing is guessed:

```bash
console models            # use a row's node_model as the LLM node's model; prefer "default"
console datasets          # only if the app should search a knowledge base
```

If `active_count` is 0, stop and follow `${CLAUDE_PLUGIN_ROOT}/skills/setup/references/models.md`.

Write `dify-apps/<app-slug>/spec.md` (goal, mode, requirements R1.., 3 to 5 acceptance cases) and `cases.json` (format in the `test-app` skill). Get a yes.

### 2. Build

Copy the matching template from this skill's `templates/` (`workflow-llm.yml` or `chatflow-llm.yml`) to `dify-apps/<app-slug>/app.yml` and build on it with the node recipes in [`references/dsl-format.md`](references/dsl-format.md), using the real `node_model` and dataset ids from step 1. Use only node types the reference covers; list anything else (tool, HTTP request, classifier, iteration) as a follow-up for the user. Check it until it prints OK (it needs PyYAML; ask before `python3 -m pip install --user pyyaml`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_dsl.py" dify-apps/<app-slug>/app.yml
```

Import it as a new app and note the `app_id` in `spec.md`:

```bash
console import dify-apps/<app-slug>/app.yml
```

- `status: pending` (exit 3): the file's DSL version differs from the server's. Tell the user, and on a yes run again with `--yes`.
- `missing_dependencies` not empty: list them; the app will fail where it uses them.
- Later changes: edit `app.yml`, check it, and import over the same app with `--app-id <app_id>`. Never create a second copy.

### 3. Test the draft

```bash
console test-draft <app_id> dify-apps/<app-slug>/cases.json
```

Grade `needs_judgement` cases yourself and show your reasoning. On a failure, read the failing node in the result, or `console run-detail <app_id> <workflow_run_id>`. Fix the smallest thing (usually a prompt), re-import with `--app-id`, and test again. Any change to the agreed spec needs the user's yes first.

### 4. Release (only on the user's yes)

Show the results per case and ask before going live. Then:

```bash
console publish <app_id> --name v1
console webapp <app_id>                        # public link, if the user wants one
console api-key <app_id> --alias <app-slug>    # saved for dify_api; the key is never printed
dify_api app test <app-slug> dify-apps/<app-slug>/cases.json   # smoke test the published app through the API
```

Ask before turning the web app on or off (`--enable` / `--disable`).

## Close

Summarize in the user's language: app name, mode, app id, the web link and API alias if made, the test results, and how to change it later ("tell me what to change; I will update the draft, test it, and ask before publishing again"). Offer `/dify:connect-app` to call the app from Claude Code.

Never publish, delete, or change access without the user's explicit yes.
