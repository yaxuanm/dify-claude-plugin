# No model in the workspace

Every Dify app needs at least one active LLM. A new self-hosted server has none, and a Cloud workspace can run out of trial credits. Check before building, and if there is none, tell the user plainly instead of continuing.

## Check

- Path A: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/model_status.py"`. It reads every page of `difyctl get model` (a workspace can list dozens of models; one page is not enough) and prints `active_count`. Ready means `active_count` > 0. If `complete` is false, say the check may be incomplete instead of claiming there is no model.
- Path B: `console models`. Ready means `active_count` > 0.

## Tell the user

Say in two or three lines: the workspace has no model set up yet, so apps can't run; Dify needs a model provider and that provider's API key; the key is entered once and stays in their Dify. Then ask which provider they have a key for, and list the common ones: OpenAI, Anthropic, Google Gemini, DeepSeek, Tongyi (Qwen), Zhipu, Moonshot, Azure OpenAI, or a self-hosted / OpenAI-compatible endpoint (Ollama, vLLM). Cloud users who still have trial credits can skip this.

**Never ask for the key in the chat**, and never put it in a file in the working folder.

## Set it up, Path A (difyctl)

1. Find the provider plugin: `difyctl get marketplace plugin --query <provider> --category model --json`. Search results are ranked loosely ("openai" returns OpenAI-API-compatible before the official OpenAI plugin), so pick the row whose `plugin_id` is exactly the provider's official one, normally `langgenius/<provider>` (for example `langgenius/openai`, `langgenius/anthropic`, `langgenius/deepseek`). Show the user that plugin (name, author, `plugin_id`) and say it will be installed into their workspace. Install only on their yes: `difyctl install plugin --identifiers <identifier> --json`, then follow the `describe.plugin.task` hint until `status` is `success`. Skip this if `installed` is already true.
2. `difyctl describe model_provider --provider <provider id> --json` to read `credential_form`.
3. Give the user this command to run **in their own terminal**. It asks for each field without showing what they type and sends it straight to difyctl:

   ```bash
   python3 "<plugin root>/scripts/set_model_key.py" --provider <provider id> --secret <secret field> [--secret <field>] [--plain <non-secret field>]
   ```

   Use `--secret` for fields of type `secret-input` and `--plain` for the rest (for example a base URL). Only required fields are needed. Write out the full command with the real plugin path. Ask them to reply "done".
4. Check again with `model_status.py`. If the key was rejected, the script printed the server's message; ask them to run it again.

## Set it up, Path B (console sign-in) or if the script fails

Give the user the page to open: `<server>/integrations/model-provider` (older Dify versions: avatar menu → **Settings** → **Model Provider**). There they install the provider and paste the key. The key never passes through Claude. Ask them to reply "done", then check again.

Then continue where you were.
