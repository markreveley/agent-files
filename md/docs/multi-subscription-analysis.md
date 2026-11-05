# Multi-subscription tools: CLIProxyAPI and T3 Code

> Status: research spike · 2026-11-04 · companion to [host-analysis.md](host-analysis.md) and [ARCHITECTURE.md](../../ARCHITECTURE.md) §5.1, §13 Q6, Q15
> Method: READMEs, project sites, T3 Code's `docs/internals/overview.md` and `providers.md`, and Anthropic's Claude Code legal and compliance page. Nothing was cloned, built or run. The video "T3 Code broke me" (youtube.com/watch?v=uLGxb4F3SyI) could not be read; only its title was available.
> **Superseded in part (2026-11-04):** agent-files is now Neovim-first: harness sessions run in Neovim terminal buffers under `agents.nvim`, so T3 Code is no longer a host candidate. §2 on CLIProxyAPI stands.

**Decision.** CLIProxyAPI is not used for Claude. T3 Code doesn't change M1. T3 Code may later be graded as a harness host next to TUIOS, but only if a session it starts fires `agent-files-hook` (§3).

## 1. Both put several subscriptions behind one interface, at different levels

| | CLIProxyAPI | T3 Code |
|---|---|---|
| What it is | Go proxy server, MIT, ~57k stars | Desktop/web "control plane for coding agents", MIT, ~31k stars |
| Unifies at | **API level.** Signs in to Claude Code, Codex, Gemini CLI, Grok and others with OAuth, then serves those subscriptions as OpenAI-, Anthropic- and Gemini-compatible endpoints, round-robin across accounts | **UI level.** Drives the official harnesses you have already signed in to (`claude auth login`, `codex login`, Cursor, OpenCode, Grok, Antigravity) from one GUI. "T3 Code doesn't resell tokens" |
| Mechanism | Takes subscription tokens and re-serves them | Server-side provider processes behind one adapter per provider. Claude runs in "SDK mode" (`providers.md`), so probably the Agent SDK *(unverified)* |
| Overlaps in agent-files | The runner's backends (`openai_compat` would take it as a `base_url` with no code change) | TUIOS's role: hosting harness sessions and owning attention |

## 2. CLIProxyAPI: rejected for Claude

- Anthropic's Claude Code legal and compliance page (code.claude.com/docs/en/legal-and-compliance, read 2026-11-01) says developers may not "route requests through Free, Pro, Max, or Ultra plan credentials" or "collect, store, or intermediate Claude.ai credentials or session tokens". Proxying those tokens is what CLIProxyAPI does.
- Anthropic enforces this server-side. Press reports date it from January 2026, with a written clarification in February and wider blocking in April (The Register, 2026-02-20; Winbuzzer, 2026-02-19). Using it risks the operator's account.
- It also breaks ARCHITECTURE: "We do not modify, wrap or proxy them."
- The permitted route already exists: the `claude_cli` backend runs the unmodified `claude -p` on the operator's own subscription, which the same page allows.
- **Codex, Gemini and Grok through the proxy:** this depends on each vendor's terms, which is open question Q6.

## 3. T3 Code: which parts of agent-files work with it

T3 Code does not run agent-files, just as TUIOS doesn't. Like TUIOS, it could only sit beside agent-files, linked by `agent-files-hook`.

| agent-files part | With T3 Code |
|---|---|
| Runner + `thread.md` threads | No. T3 Code has its own chat UI and history and doesn't know about `thread.md`. The two are competing front ends. |
| agents.nvim | No, it's a GUI. Running `nvim` in a T3 Code terminal is untested. |
| `agent-files-hook` (observed sessions) | **Unverified, and it decides the question.** The hook fires only if T3 Code's Claude sessions load `~/.claude/settings.json`. If they use the Agent SDK without user settings, they never fire, and agent-files sees nothing. |
| agent-files as a T3 Code provider | Only by writing a new driver in T3 Code's code (`providers.md`). The runner isn't a coding harness, so it doesn't fit their model. |

**The test that decides it:** run smoke test S9 with T3 Code as the host. Start a Claude session in T3 Code, trigger a permission prompt, and check that `_observed/...` appears in the data root and that `:AgentsNext` shows `blocked`. If it fails, T3 Code can't host sessions for agent-files and isn't a candidate.

**If S9 passes:** grade T3 Code against the 21 items in [host-analysis §1](host-analysis.md#1-session-host-and-attention--21-items) before switching anything.

## Sources
- github.com/router-for-me/CLIProxyAPI
- t3.codes; github.com/pingdotgg/t3code (README, `docs/internals/overview.md`, `docs/internals/providers.md`)
- code.claude.com/docs/en/legal-and-compliance
- theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access; winbuzzer.com/2026/02/19/anthropic-bans-claude-subscription-oauth-in-third-party-apps-xcxwbn
