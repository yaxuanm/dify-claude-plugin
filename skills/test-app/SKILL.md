---
name: test-app
description: 'Test a published Dify app through the public Service API: run acceptance cases, read failed runs and workflow logs, and suggest fixes. Works on Dify Cloud and self-hosted, with an app API key. Use when the user runs /dify:test-app, or asks to test, evaluate, debug or regression-check a published Dify app.'
argument-hint: '[key alias] [cases file]'
---

# Test a published Dify app

The helper is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_api.py"` (standard library only). Every command prints JSON. Below it is written as `dify_api`.

If difyctl is signed in to the user's server (see the `setup` skill), prefer its own run and test commands instead: they also reach drafts. This skill is for published apps reachable only by API key, which includes Dify Cloud.

## 1. Key

Run `dify_api key list`. If no alias fits, ask the user to create a key for the app (in Dify: the app's **API Access** page → **API Key**) and save it **in their own terminal**, so the key never enters the chat:

```bash
python3 "<plugin root>/scripts/dify_api.py" key set <alias>                 # Dify Cloud
python3 "<plugin root>/scripts/dify_api.py" key set <alias> --base-url https://<host>/v1   # self-hosted
```

Print the expanded path for them (`echo "${CLAUDE_PLUGIN_ROOT}"`). In Claude Code they can also type it after `!` at the prompt. Never ask them to paste a key into the chat; if they do, do not repeat it, and suggest they rotate it.

## 2. Learn the app

`dify_api app info <alias>` gives the mode and the input form. Chat apps (`chat`, `advanced-chat`, `agent-chat`) need `--query`; workflows take `--inputs`.

## 3. Cases

Use the acceptance cases from the app's `spec.md` when there is one (`dify-apps/<slug>/` or `difyctl/<slug>/`). Otherwise draft 3 to 6 with the user, including one edge case. Write them to `dify-apps/<slug>/cases.json`:

```json
[
  {"id": "A1", "inputs": {"feedback": "The machine leaks"}, "expect": {"check": "exact", "output": "sentiment", "value": "负面"}},
  {"id": "A2", "query": "How long is the refund window?", "expect": {"check": "contains", "value": ["30"]}},
  {"id": "A3", "inputs": {"feedback": "ok I guess"}, "expect": {"check": "judged", "rubric": "neutral, summary under 50 chars"}}
]
```

`output` names a workflow output field; chat apps check the answer text. `judged` cases come back as `needs_judgement`: grade them yourself against the rubric and show your reasoning.

## 4. Run

```bash
dify_api app test <alias> dify-apps/<slug>/cases.json
```

Report a table: case, verdict, and one line on why. Keep token and time figures if the user cares about cost or speed.

## 5. Debug failures

- Workflow: `dify_api app run-detail <alias> <workflow_run_id>` for status, outputs and error; `dify_api app logs <alias> --status failed` for recent failures from any caller.
- Chat: look at `answer`, `error` and `retriever_resources` (which documents the knowledge base returned).
- Find the cause: prompt, missing input, model error, empty retrieval, wrong branch. Propose the smallest fix. If the app was built from a DSL in this folder, change the file, run the `build-dsl` check, and re-import (difyctl, or the console on Cloud), then run the cases again.

Never change or publish the user's app without their yes.
