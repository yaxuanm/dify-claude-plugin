---
name: new-app
description: 'Turn a plain-language description into a working Dify app (Workflow or Chatflow): agree a short spec, build it in the connected workspace with difyctl, test it, and publish it on the user''s yes. Use when the user runs /dify:new-app, or asks to build, create or prototype an AI app, chatbot, agent, RAG / knowledge-base Q&A, or automation workflow on Dify.'
argument-hint: '<what the app should do>'
---

# Build a new Dify app

Goal: the user describes what they need and ends up with a Dify app that runs, has passed a few real test cases, and (if they say yes) is published with a link they can open.

The user's request: $ARGUMENTS

## 0. Make sure Dify is connected

Run `difyctl login --resume --json`. If difyctl is missing or there is no `email` in the result, follow the `setup` skill first, then come back here.

## 1. Follow difyctl's build method, sized for a first app

The `difyctl` skill in this plugin holds Dify's official build method: read its `references/build-workflow.md` now and follow it. It has four phases (spec, plan, build, hand over), each with a human gate. Do not skip a gate. Its rules win over anything below.

For a first app, keep each phase small so the user gets a running app quickly:

- **Spec.** If the request is clear, draft the spec yourself from it and ask only what is missing, one question at a time, at most three. Aim for 2 to 5 requirements and 3 acceptance cases. Pick the mode and say why in one line: Workflow for one input to one output, Chatflow for a conversation.
- **Resources.** Search the workspace first, as the method says: `difyctl get model --model-type llm --json`, `difyctl get tool --query <service> --json`, `difyctl get knowledge_base --query <words> --json`. Prefer what is already installed and configured. If the app needs a model and none is `active`, stop and help the user add a provider credential (see the `difyctl` skill's `references/plugins.md`); never paste a key into a file.
- **Plan.** Keep the first version to the fewest nodes that meet the spec. Offer extras (more tools, branches, a knowledge base) as a later version, not now.
- **Build.** Build it yourself in one or two slices. Keep the working files in `difyctl/<app-slug>/` in the current folder, as the method says.
- **Hand over.** Run the acceptance cases, show pass or fail, then ask before publishing. After publishing, give the user the web app `url` and the app id.

## 2. If the user is not sure what to build

Offer three starting points that fit what you know about them, for example:

1. **Support assistant (Chatflow):** answers questions in the customer's language, from a knowledge base if they have one.
2. **Document summarizer (Workflow):** takes a file or text, returns a structured summary.
3. **Content generator (Workflow):** takes a topic and audience, returns a draft in a fixed format.

Let them pick or describe their own, then go to step 1.

## 3. Close

End with a short summary in the user's language:

- app name, mode, app id, and the web app link if published;
- the acceptance results;
- how to change it later: "Tell me what to change and I will update the draft, test it, and ask before publishing again."
- open the app in the Dify console at `<server>/app/<app_id>/workflow` to view or edit it visually.

Never publish, delete, or change access settings without the user's explicit yes.
