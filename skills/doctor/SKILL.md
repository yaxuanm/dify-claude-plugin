---
name: doctor
description: 'Check the Dify plugin''s health in one report: difyctl install and version, which path the server uses (official API or console sign-in), whether you are signed in, the current workspace, available models, and saved API keys (masked). Read-only. Use when the user runs /dify:doctor, or when a Dify command fails and the cause is unclear.'
argument-hint: '[server-url]'
---

# Dify plugin self-check

Run, with the server URL if the user gave one (`$ARGUMENTS`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" $ARGUMENTS
```

It only reads: it logs in to nothing, installs nothing and never prints a secret.

Report to the user in their language, as a short checklist with ✓ or ✗ per line:

- Plugin version.
- difyctl: installed, version, on PATH. Only matters when `path` is `difyctl`.
- Server and path: `difyctl` (official API) or `console` (browser sign-in fallback), and whether it is Dify Cloud.
- Signed in: account and workspace.
- Models: how many active LLMs, and the first few by name.
- Saved API keys: alias, base URL and the masked key, exactly as printed.

Then list each entry in `problems` with its fix, most important first. Offer to run the fix (usually `/dify:setup`), but do not run it unasked. If `problems` is empty, say everything is ready and suggest `/dify:new-app`.
