#!/usr/bin/env python3
"""validate_dsl.py: offline structural check for a Dify app DSL file.

Catches the mistakes that make an import fail or a run break, before the file
reaches a Dify server. It does not replace the server's own check (difyctl
`check console_app dsl`, or the console's import), which also knows node schemas,
installed models and plugins.

usage: python3 validate_dsl.py app.yml [--json]
exit:  0 no errors (warnings allowed), 1 errors found, 2 cannot read the file
"""
import json
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    print(json.dumps({"valid": False, "errors": [{"loc": "", "message": "PyYAML is not installed. Run: python3 -m pip install --user pyyaml"}], "warnings": []}))
    sys.exit(2)

MODES = {"workflow", "advanced-chat"}
BRANCH_TYPES = {"if-else", "question-classifier"}
SYSTEM_ROOTS = {"sys", "env", "conversation"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"app-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]
REF_TEXT = re.compile(r"\{\{#([A-Za-z0-9_\-]+)\.([A-Za-z0-9_\-.]+)#\}\}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path, as_json = argv[1], "--json" in argv
    errors, warnings = [], []

    def err(loc, msg):
        errors.append({"loc": loc, "message": msg})

    def warn(loc, msg):
        warnings.append({"loc": loc, "message": msg})

    try:
        raw = open(path, encoding="utf-8").read()
        doc = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as e:
        print(json.dumps({"valid": False, "errors": [{"loc": "", "message": f"cannot read YAML: {e}"}], "warnings": []}))
        return 2

    for pat in SECRET_PATTERNS:
        if pat.search(raw):
            err("", "looks like a secret (API key or token) is in the file; remove it, set credentials in Dify instead")

    if not isinstance(doc, dict):
        err("", "top level must be a mapping")
        return report(path, errors, warnings, as_json)

    if doc.get("kind") != "app":
        err("kind", "must be 'app'")
    if not isinstance(doc.get("version"), str):
        err("version", "must be a quoted string such as '0.4.0'")
    app = doc.get("app") or {}
    mode = app.get("mode")
    if mode not in MODES:
        err("app.mode", f"must be one of {sorted(MODES)} for a Workflow or Chatflow app, got {mode!r}")
    if not app.get("name"):
        err("app.name", "is required")

    graph = ((doc.get("workflow") or {}).get("graph")) or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes:
        err("workflow.graph.nodes", "no nodes")
        return report(path, errors, warnings, as_json)

    by_id, types = {}, {}
    for i, n in enumerate(nodes):
        loc = f"workflow.graph.nodes[{i}]"
        nid = str(n.get("id", ""))
        data = n.get("data") or {}
        t = data.get("type")
        if not nid:
            err(loc, "node has no id")
            continue
        if nid in by_id:
            err(loc, f"duplicate node id {nid!r}")
        by_id[nid] = n
        types[nid] = t
        if not t:
            err(loc + ".data.type", "missing node type")
        if not data.get("title") and not str(t).endswith("-start"):
            warn(loc + ".data.title", f"node {nid} has no title")
        if "position" not in n:
            warn(loc + ".position", f"node {nid} has no position; the canvas may stack nodes")
        if t == "llm":
            model = data.get("model") or {}
            if not model.get("provider") or not model.get("name"):
                warn(loc + ".data.model", f"LLM node {nid} has no model; pick one in the console after import, or runs fail")
            if not data.get("prompt_template"):
                err(loc + ".data.prompt_template", f"LLM node {nid} has no prompt")
        if t == "code" and not data.get("code"):
            err(loc + ".data.code", f"code node {nid} has no code")
        if t == "answer" and mode == "workflow":
            err(loc, "answer nodes belong to Chatflow (advanced-chat); a Workflow ends with an end node")
        if t == "end" and mode == "advanced-chat":
            err(loc, "end nodes belong to Workflow; a Chatflow replies with an answer node")

    starts = [i for i, t in types.items() if t == "start"]
    if len(starts) != 1:
        err("workflow.graph.nodes", f"need exactly one start node, found {len(starts)}")
    terminal = "end" if mode == "workflow" else "answer"
    if not any(t == terminal for t in types.values()):
        err("workflow.graph.nodes", f"a {mode} app needs at least one {terminal} node")

    out_handles = {}
    adj = {i: [] for i in by_id}
    for j, e in enumerate(edges):
        loc = f"workflow.graph.edges[{j}]"
        s, t = str(e.get("source", "")), str(e.get("target", ""))
        if s not in by_id:
            err(loc + ".source", f"unknown node {s!r}")
            continue
        if t not in by_id:
            err(loc + ".target", f"unknown node {t!r}")
            continue
        adj[s].append(t)
        out_handles.setdefault(s, set()).add(str(e.get("sourceHandle", "source")))

    # Every branch needs an edge.
    for nid, n in by_id.items():
        data = n.get("data") or {}
        if types[nid] == "if-else":
            want = {str(c.get("case_id")) for c in data.get("cases") or []} | {"false"}
        elif types[nid] == "question-classifier":
            want = {str(c.get("id")) for c in data.get("classes") or []}
        else:
            continue
        missing = want - out_handles.get(nid, set())
        if missing:
            warn(f"node {nid}", f"branch(es) {sorted(missing)} have no edge; a run that takes them stops there")

    # Reachability from start.
    if len(starts) == 1:
        seen, stack = set(), [starts[0]]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(adj.get(cur, []))
        for nid in by_id:
            if nid not in seen and not (by_id[nid].get("parentId") or (by_id[nid].get("data") or {}).get("isInIteration") or (by_id[nid].get("data") or {}).get("isInLoop")):
                warn(f"node {nid}", "not reachable from the start node")

    # Variable references.
    def check_ref(root, loc):
        if root in SYSTEM_ROOTS or root in by_id:
            return
        err(loc, f"refers to unknown node {root!r}")

    def walk(obj, loc):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("value_selector", "variable_selector") and isinstance(v, list) and v:
                    check_ref(str(v[0]), f"{loc}.{k}")
                else:
                    walk(v, f"{loc}.{k}")
        elif isinstance(obj, list):
            for idx, v in enumerate(obj):
                walk(v, f"{loc}[{idx}]")
        elif isinstance(obj, str):
            for m in REF_TEXT.finditer(obj):
                check_ref(m.group(1), loc)

    for nid, n in by_id.items():
        walk(n.get("data") or {}, f"node {nid}.data")

    return report(path, errors, warnings, as_json)


def report(path, errors, warnings, as_json):
    result = {"file": path, "valid": not errors, "errors": errors, "warnings": warnings}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{path}: {'OK' if not errors else 'FAILED'} ({len(errors)} errors, {len(warnings)} warnings)")
        for e in errors:
            print(f"  error   {e['loc']}: {e['message']}")
        for w in warnings:
            print(f"  warning {w['loc']}: {w['message']}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
