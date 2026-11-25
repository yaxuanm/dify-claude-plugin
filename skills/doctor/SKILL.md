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

If `runtime.remote` is true, open the report with that, in one or two plain sentences: this session runs in a cloud sandbox, so the difyctl, sign-in and local Dify on their computer cannot be seen from here, and that is expected. Do not report those as failures or push them to sign in again; recommend running `/dify:doctor` in Claude Code on their own computer, and offer `/dify:setup` here only for Dify Cloud or a Dify with a public URL.

Report to the user in their language, as a short checklist with ✓ or ✗ per line:

- Plugin version.
- difyctl: installed, version, on PATH. Only matters when `path` is `difyctl`.
- Server and path: `difyctl` (official API) or `console` (browser sign-in fallback), and whether it is Dify Cloud.
- Signed in: account and workspace.
- Models: how many active LLMs, and the first few by name.
- Saved API keys: alias, base URL and the masked key, exactly as printed.

Then list each entry in `problems` with its fix, most important first. Offer to run the fix (usually `/dify:setup`), but do not run it unasked. If `problems` is empty, say everything is ready and suggest `/dify:new-app`.
