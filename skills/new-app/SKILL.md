---
name: new-app
description: 'Turn a plain-language description into a working, tested Dify app (Workflow or Chatflow) in the user''s workspace, end to end and without opening the Dify console: spec, build, import, draft tests, then publish, web app link and API key on the user''s yes. Works on Dify Cloud and self-hosted. Use when the user runs /dify:new-app, or asks to build, create or prototype an AI app, chatbot, agent, RAG / knowledge-base Q&A, or automation workflow on Dify.'
argument-hint: '<what the app should do>'
---

# Build a new Dify app, end to end

Goal: the user describes what they need and ends up with a Dify app that is built in their workspace, has passed real test cases, and, on their yes, is published with a web link and an API key. The user never has to open the Dify console.

The user's request: $ARGUMENTS

## 0. Connection

Use the path the `setup` skill found in this session. If there is none yet, run the `setup` skill first, then come back. Two paths, same phases:

- **Path A, difyctl** (server has the official `/openapi/v1`).
- **Path B, console** (`dify_console.py`; servers without the official API).

Below, `console` means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_console.py"` and `dify_api` means `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_api.py"`.

## Path A: difyctl

Follow the `difyctl` skill's `references/build-workflow.md` (spec, plan, build, hand over, each with a human gate). For a first app keep it small: at most three questions, 2 to 5 requirements, 3 acceptance cases, the fewest nodes that meet the spec, built in one or two slices. Its rules win over anything here.

## Path B: console

### 1. Spec (one gate)

Restate the request, ask only what is missing (at most three questions, one at a time), pick Workflow or Chatflow with one line on why. Look up real resources first so nothing is guessed:

```bash
console models            # use a row's node_model as the LLM node's model; prefer "default"
console datasets          # only if the app should search a knowledge base
```

If no LLM model is active, stop: the workspace needs a model provider key. Tell the user (this one step needs the console's Settings → Model Provider today).

Write `dify-apps/<app-slug>/spec.md` (goal, mode, requirements R1.., 3 to 5 acceptance cases) and `cases.json` (format in the `test-app` skill). Get a yes.

### 2. Build

Write `dify-apps/<app-slug>/app.yml` following the `build-dsl` skill (its templates and `references/dsl-format.md`), using the real `node_model` and dataset ids from step 1. Check it until it prints OK:

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
