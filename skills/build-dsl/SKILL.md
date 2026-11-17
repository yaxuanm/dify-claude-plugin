---
name: build-dsl
description: 'Write a Dify app as a DSL (YAML) file from a plain-language description, check it offline, and hand it over for import into Dify Cloud or any Dify server. Use when the user wants a Dify Workflow or Chatflow but difyctl cannot reach their server (for example on Dify Cloud), or asks for a Dify DSL / YAML / importable app file.'
argument-hint: '<what the app should do>'
---

# Build a Dify app as a DSL file

Goal: a `.yml` file the user imports into Dify (Studio → Create app → Import DSL file) and that runs on the first try. This path needs no CLI and no login, so it works on Dify Cloud today.

The user's request: $ARGUMENTS

Read [`references/dsl-format.md`](references/dsl-format.md) before writing any YAML.

## 1. Agree a short spec (one message)

Restate in a few lines and ask only what is missing, at most three questions, one at a time:

- what goes in and what should come out;
- mode: **Workflow** (one input to one result) or **Chatflow** (a conversation), with one line on why;
- which model provider their workspace has set up (OpenAI, Anthropic, ...), or "don't know";
- whether it should search a knowledge base they already have, and if so its id.

Write 2 to 5 requirements (`R1`...) and 3 test cases (input, what a good output looks like). Get a yes before building.

## 2. Write the file

1. Copy the matching template from `templates/` (`workflow-llm.yml` or `chatflow-llm.yml`, in this skill's folder) to `dify-apps/<app-slug>/app.yml` in the current folder. Save the spec next to it as `spec.md`.
2. Set `app.name`, `app.description`, and an emoji `app.icon`.
3. Add nodes from the recipes in the reference. Keep the first version to the fewest nodes that meet the spec. Write prompts carefully: they are most of the app's quality.
4. Use only the node types the reference gives recipes for. If the spec needs another type (tool, HTTP request, classifier, iteration), build the rest and list that step as "add in the console" in the hand-over.

## 3. Check it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_dsl.py" dify-apps/<app-slug>/app.yml
```

Fix every `error` and run it again until it prints `OK`. Read each `warning` and fix it or tell the user about it. If the script says PyYAML is missing, ask before installing it with `python3 -m pip install --user pyyaml`.

Then walk each test case through the graph yourself and check that every requirement maps to a node.

## 4. Hand over

- **Signed in** (either path of the `setup` skill): offer to import, test and publish it for the user, following the `new-app` skill from its build step. No console needed.
- **Not signed in and the user does not want to sign in**: give them these manual steps:
  1. Open Dify → **Studio** → **Create app** → **Import DSL file**, and choose `dify-apps/<app-slug>/app.yml`.
  2. If Dify asks to confirm a version difference, confirm.
  3. Open the LLM node and check the model. Pick one if it shows as unavailable.
  4. Click **Run** (Workflow) or **Preview** (Chatflow) and try the test cases from `spec.md`.
  5. **Publish** when it looks right. To use the app from Claude Code afterwards, run `/dify:connect-app`.

End with: the file path, the mode, the requirements and test cases, and anything the user still has to add in the console. Ask them to paste any import error back to you; fix the file and check it again.
