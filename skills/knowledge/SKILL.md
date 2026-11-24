---
name: knowledge
description: 'Create and fill a Dify knowledge base from local files (Markdown, text, PDF, Word and more) and test what it retrieves, through Dify''s Knowledge API. Works on Dify Cloud and self-hosted. Use when the user runs /dify:knowledge, or wants to upload docs to Dify, build a RAG knowledge base, or check retrieval quality.'
argument-hint: '[folder or files]'
---

# Build a Dify knowledge base from local files

The helper is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_api.py"`, written below as `dify_api`.

## 1. Key

The Knowledge API uses one workspace-wide key (in Dify: **Knowledge** → **API** → **API Key**; it starts with `dataset-`). It can read and change every knowledge base in the workspace, so say that first. If the session is signed in through the console path (`setup` skill, Path B), create and save it without the console on the user's yes: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_console.py" kb-key --alias kb`. Otherwise have the user save it in their own terminal, never in the chat:

```bash
python3 "<plugin root>/scripts/dify_api.py" key set kb                     # Dify Cloud
python3 "<plugin root>/scripts/dify_api.py" key set kb --base-url https://<host>/v1
```

## 2. Pick or create the knowledge base

`dify_api kb list kb`. Reuse one if the user names it.

Before creating one, check for an embedding model. New knowledge bases use high-quality (embedding) indexing, and Dify refuses to create one when the workspace has no default embedding model, which is the normal state of a new workspace.

- Path A: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/model_status.py" --model-type text-embedding`. It lists active embedding models but not the default.
- Path B: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dify_console.py" models --type text-embedding`. `default` is the workspace default.

If there is no active embedding model, say so and follow `${CLAUDE_PLUGIN_ROOT}/skills/setup/references/models.md` to add a provider that has one (OpenAI's covers both chat and embeddings). Otherwise pick the default, or on Path A the first active one (prefer a `text-embedding-3-small`-class model), name it to the user, and pass it explicitly so a missing default does not matter:

```bash
dify_api kb create kb --name "<name>" --description "<what is in it>" \
  --embedding-model <model> --embedding-provider <provider>
```

## 3. Upload

Gather the files the user means. Show the list and the total size, and confirm before uploading: this sends their content to the Dify server. Skip secrets, `.env` files and anything that looks private unless they confirm.

```bash
dify_api kb add kb <dataset_id> docs/policy.md docs/faq.md docs/handbook.pdf
```

`.txt` and `.md` go up as text, other types as files. Then poll each batch until `indexing_status` is `completed` (or `error`), waiting a few seconds between checks:

```bash
dify_api kb status kb <dataset_id> <batch>
```

## 4. Test retrieval

Write 3 to 5 questions a real user would ask, and run each:

```bash
dify_api kb retrieve kb <dataset_id> --query "<question>" --top-k 4
```

For each, say whether the right document came back and how strong the score is. Weak results usually mean the answer is not in the files, or the documents need splitting into smaller, focused files.

## 5. Use it

- In a new app: give the dataset id to the `new-app` skill (knowledge-retrieval node).
- In an existing app: add it in the app's knowledge-retrieval node or context settings.
