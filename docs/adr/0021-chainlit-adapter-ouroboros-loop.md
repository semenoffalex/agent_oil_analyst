# 0021. Reviewer opens Chainlit; Ouroboros is the loop

## Status

Superseded for the **click target** by [0026](0026-streamlit-dashboard-is-the-demo.md) (Streamlit on `:8000`). The turn still runs in Ouroboros; LangGraph is still not the conversation path.

## Context

The assignment wants a simple browser UI and one-command run. Current-generation Ouroboros Chat is `:8765`. The customer first considered that URL, then chose the existing Chainlit port so the reviewer clicks a familiar chat. They will **verify Ouroboros in the repository**, not by opening the Ouroboros SPA.

This **narrows** [0010](0010-chainlit-ui.md): Chainlit stays the conversation window; LangGraph is no longer “what runs behind it.” It follows [0001](0001-analyst-lives-inside-ouroboros.md) for the **loop**, not the **window**. Using Ouroboros as a silent judge of Chainlit strings, or leaving LangGraph as the runtime with Ouroboros only as a git dependency, is out.

## Decision

The reviewer opens **`http://localhost:8000`** (Chainlit) after one Docker/compose command. That window is an **adapter**: it sends the question into the Ouroboros agent loop (gateway may listen on `:8765` internally and need not be the demo URL). Desktop `Ouroboros.app` is not required for acceptance.

Proof that this is Ouroboros: **code in this repo** (how Chainlit calls the gateway, domain skills/identity, run composition) — not a requirement to click Skills or Chat on `:8765`.

LangGraph is not the thing the reviewer talks to.

## Consequences

- README demo URL is `:8000`, not `:8765`. Docker must start both the Chainlit adapter and an Ouroboros runtime.
- [0010](0010-chainlit-ui.md) “LangGraph behind Chainlit” is superseded for this rebuild; Chainlit-as-chat-shell remains.
- Grader-facing Ouroboros Skills / Dashboard are optional; whether README must still name them is [Which trust surfaces the grader sees](../../.scratch/ouroboros-analyst/issues/07-which-trust-surfaces-the-grader-sees.md).
