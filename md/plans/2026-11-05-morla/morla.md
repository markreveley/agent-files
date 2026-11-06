# Plan: morla as the command lane for agents.nvim

> Status: accepted · 2026-11-05 · from a conversation with the operator on agent orchestration in Neovim · milestone M1.6 (ARCHITECTURE §14) · 2026-11-05: D1 superseded, there is no send policy ([tmux-host](../2026-11-05-tmux-host/tmux-host.md) D5); sessions now run in tmux panes, so "tell the claude in the docs worktree…" is a `workmux send` (tmux-host Q3) · 2026-11-05, later: the host is Rex again, so that send is a `rex send` ([host-neutral](../2026-11-05-host-neutral/host-neutral.md) D4)

**Goal.** Let the operator drive `agents.nvim` in plain English through [morla-neovim](https://github.com/markreveley/morla-neovim) (locally `~/dev/repos/morla-neovim`). For example, "fork this thread from t4 with the selection as carry", "stop the api agent", "tell the claude in the docs worktree to run the tests". morla turns each request into an Ex command in `q:`, explains it, and runs nothing until the operator presses Enter.

**Why.** The two cover different needs, and fit together without either depending on the other:

| | morla | agent-files' own agents |
|---|---|---|
| Duration | 3 to 5 s, request and reply | minutes to hours |
| Needs live editor state | yes: buffer lines, selection, buffer list, `:` history (morla D12) | little; files are the truth (principles 1, 8) |
| If Neovim dies | nothing is lost; ask again | runs outside Neovim, unaffected (tier 2, 3) |
| Where it runs | inside Neovim (`vim.system`) | outside, through files |

In agent-files' terms morla is a direct call (tier 3) made inside the editor: one `claude -p` request with tools, settings and MCP off (morla D2), one JSON reply (morla D8), no tool loop, and a human who runs the result (morla D1). Short, human-gated calls that need editor state belong in Neovim. Long-running agents stay outside it.

**Adopt before building.** morla exists and is the operator's. `agents.nvim` already works through Ex commands (`:AgentsNew`, `:AgentsFork`, `:AgentsStop`, `:AgentsNext`, `:AgentsTermSend`…), so morla can drive it today. Its prompt just doesn't know these commands. Nothing below adds a runtime or a protocol.

## Decisions

- **D1. Intent decides: a send the operator asks for is a human send.** Decided by the operator, 2026-11-05, and adopted as design in [ARCHITECTURE §5.1](../../governance/ARCHITECTURE.md#51-tier-1--harness-tuis-in-the-hosts-panes) ("Intent decides"). The rule guards against automated communication between agents, not against a model carrying out the operator's request. Whatever morla writes to carry out a request, including text it composes, is the operator's when the operator asked for it and runs it. `agents.term` needs no change: it already counts every command the operator runs as `human`.
- **D2. Neither plugin depends on the other.** morla keeps its no-dependency rule (morla D7) and knows nothing about agent-files. `agents.nvim` doesn't require morla. They meet only through Ex commands and the operator's config.
- **D3. morla takes extra context from the operator's config.** A new morla option, a function or a string, adds text to each request. It's generic: any plugin's command reference can go through it. `agents.nvim` provides `require('agents').command_reference()`: each `:Agents*` command, its arguments, what it does, and the current terminal and thread names that its targets match. The operator wires the two together in their config.
- **D4. morla flags sends to a terminal.** A command that types into a terminal (`:AgentsTermSend`, `chansend(`) gets a `⚠ sends to terminal` flag, a warning that blocks nothing (morla D5). It points at the commands whose effect reaches a running agent, so the operator reads those before Enter. It is a warning, not a policy check (D1).

## Steps

1. **morla:** the extra-context option (D3), with tests. In the morla repo, under its own plan.
2. **morla:** the `sends to terminal` flag in `lua/morla/risk.lua` (D4), with tests. In the morla repo.
3. **agents.nvim:** `command_reference()` (D3), with a test in `tests/nvim/test_agents.lua`. It reads the commands' own definitions, so it can't drift from them.
4. **Operator config:** wire the two together in the operator's own config (outside agent-files).
5. **Live run** against `claude -p`: about ten requests covering new, fork, stop, next, term send and term capture. Report in `md/tested/`, the way morla's `md/tested/` reports do.

## Questions

- **Q1.** Should morla's history (`~/.local/share/nvim/morla/history.jsonl`) become part of the record, so that a command that touched a thread links to the instruction behind it? It overlaps with operator authorship in [provenance](../2026-11-05-provenance/provenance.md). Decide when that plan's steps come up.
- **Q2.** Should `agents.term` record which sends came through morla (for example, morla sets a flag while its command runs), so a send's origin can be told apart later? The policy (D1) doesn't need it; it would only add to the record. Waits on Q1.
