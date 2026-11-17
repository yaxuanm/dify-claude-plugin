# Dify app DSL, offline cheat sheet

Use this when no Dify server is reachable from here. When difyctl works, the server's own node schemas (`difyctl describe node_type --node-type <type>`) win over this sheet.

## Contents

- File skeleton
- Nodes and edges
- Variable references
- Node recipes: start, llm, end, answer, if-else, code, template-transform, knowledge-retrieval
- Models
- What not to do

## File skeleton

Start from `templates/workflow-llm.yml` (mode `workflow`) or `templates/chatflow-llm.yml` (mode `advanced-chat`). Keep `kind: app`, `version`, `dependencies: []`, `features`, `environment_variables` and `conversation_variables` as they are unless the spec needs them.

`version: 0.4.0` imports on current Dify Cloud and self-hosted servers; a server newer than the file migrates it. Do not raise it.

## Nodes and edges

Node: `{id, type: custom, position: {x, y}, sourcePosition: right, targetPosition: left, data: {type, title, desc, ...}}`. Ids are short unique strings (`start`, `llm`, `classify`, `reply_refund`). Lay nodes out left to right, about 320 px apart; put parallel branches 160 px apart vertically.

Edge: `{id, type: custom, source, sourceHandle, target, targetHandle: target, data: {sourceType, targetType, isInIteration: false, isInLoop: false}}`. `sourceHandle` is `source`, except:

- if-else: each case's `case_id`, plus `false` for the else branch;
- question-classifier: each class's `id`.

Every branch needs an edge.

## Variable references

- In text (prompts, answers, templates): `{{#<node_id>.<var>#}}`, for example `{{#start.question#}}`, `{{#llm.text#}}`.
- In selectors: `[<node_id>, <var>]`, for example `value_selector: [llm, text]`.
- System values: `{{#sys.query#}}` (Chatflow user message), `{{#sys.files#}}`, `{{#sys.user_id#}}`, `{{#sys.conversation_id#}}`.
- Outputs: llm → `text`; code → each key in its `outputs`; template-transform → `output`; knowledge-retrieval → `result`; question-classifier → `class_name`.

## Node recipes

**start**: `variables` is a list of `{variable, label, type, required, max_length?, options}`. `type`: `text-input` (short), `paragraph` (long), `select` (with `options`), `number`, `file`, `file-list`. A Chatflow usually has no variables; the user message is `sys.query`.

**llm**:

```yaml
type: llm
title: Draft reply
model: {provider: langgenius/openai/openai, name: gpt-4o-mini, mode: chat, completion_params: {temperature: 0.7}}
prompt_template:
  - {role: system, text: "You are ... Rules: ..."}
  - {role: user, text: "{{#start.input_text#}}"}     # Workflow only; a Chatflow takes the user turn from memory
context: {enabled: false, variable_selector: []}       # set enabled + selector [kb, result] to feed retrieved chunks; then put {{#context#}} in the system prompt
vision: {enabled: false}
variables: []
# Chatflow only:
memory: {query_prompt_template: "{{#sys.query#}}", window: {enabled: false, size: 10}}
```

**end** (Workflow): `outputs: [{variable: result, value_type: string, value_selector: [llm, text]}]`. Output names are unique across end nodes.

**answer** (Chatflow): `answer: "{{#llm.text#}}"`, `variables: []`.

**if-else**:

```yaml
type: if-else
title: Is it urgent?
cases:
  - case_id: urgent
    id: urgent
    logical_operator: and
    conditions:
      - {id: c1, variable_selector: [start, priority], comparison_operator: is, value: high, varType: string}
```

Operators for strings: `contains`, `not contains`, `start with`, `end with`, `is`, `is not`, `empty`, `not empty`. Numbers: `=`, `≠`, `>`, `<`, `≥`, `≤`. Edges leave by `urgent` and `false`.

**code**:

```yaml
type: code
title: Parse
code_language: python3
code: |
  def main(text: str) -> dict:
      return {"length": len(text)}
variables: [{variable: text, value_selector: [start, input_text]}]
outputs: {length: {type: number, children: null}}
```

Output types: `string`, `number`, `object`, `array[string]`, `array[number]`, `array[object]`. Use code only for logic no other node can do.

**template-transform**: `template: "Summary:\n{{ summary }}"` (Jinja2), `variables: [{variable: summary, value_selector: [llm, text], value_type: string}]`.

**knowledge-retrieval**: needs a knowledge base id from the user's workspace. The user copies it from the console URL (`/datasets/<id>/documents`). Minimal data:

```yaml
type: knowledge-retrieval
title: Search policy docs
query_variable_selector: [sys, query]    # Workflow: [start, question]
dataset_ids: ["<id from the user>"]
retrieval_mode: multiple
multiple_retrieval_config: {top_k: 4, reranking_enable: false}
```

Never invent a dataset id. If the user has none yet, build without retrieval and tell them how to add it in the console.

Other node types (question-classifier, parameter-extractor, http-request, tool, iteration, loop, agent): build them in the console after import, or with difyctl where it works. Their data shapes vary by version and an offline guess often fails the import.

## Models

`model.provider` is the plugin provider id: `langgenius/<plugin>/<provider>`, for example `langgenius/openai/openai`, `langgenius/anthropic/anthropic`. Ask the user which provider and model their workspace has set up (Settings → Model Provider). If they do not know, leave the template's model in place and tell them to pick a model on the LLM node after import.

## What not to do

- No API keys, tokens or passwords anywhere in the file.
- No `datasource` or `knowledge-index` nodes (knowledge pipelines only).
- No `answer` node in a Workflow, no `end` node in a Chatflow.
- Never change the id of a node the user already has.
