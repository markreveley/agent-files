# Host analysis — existing tools graded against the plan

> Status: decision record · 2026-11-01 · companion to [ARCHITECTURE.md](../ARCHITECTURE.md) §5.1, §12
> Rule applied: planned work that an existing tool already does is dropped and the tool used instead; the tool that covers the most planned work goes first.
> Method: TUIOS, herdr and parrot.nvim were shallow-cloned and read (source and docs; nothing built or run). Other tools from their docs and READMEs. Where only a README or a secondary page says so, it is marked *(docs)* or *(unverified)*.

**Decision.** TUIOS hosts harness sessions and owns attention for them; herdr is the fallback. agent-files keeps its own replay runner (`agent-files-run`); parrot.nvim is not adopted. Pi Durable is not a foundation. Dropped as a result: the M2 tier-1 bridge, the doorbell (`agent-files-ring`, registry, `agent-files-notify`), the Elixir supervisor, the proposed worktree workspaces, and H4 as a trial hypothesis.

## 1. Session host and attention — 21 items

Items are the planned capabilities from ARCHITECTURE §4–§9 and the M1 spec. F = does it as specified or better, P = partly, N = not at all.

| # | Planned capability | TUIOS | herdr (TUI + core) |
|---|---|---|---|
| C1 | Host unmodified `claude` / `codex` TUIs, detached; attach any time | F — daemon holds every terminal | F — `hc run --bg`, `hc attach` |
| C2 | Send input, capture output from a script | F — JSON over a unix socket: `send-text`, `send-keys`, `capture-pane`, `agent-transcript`, `subscribe` | F — `hc send/keys/read`, OpenRPC schema |
| C3 | Status working / blocked / done / failed / interrupted for Claude Code and Codex | P — hooks (14 Claude events, 8 Codex) > screen rules > process; no "interrupted": Esc leaves a pane "working" | P — TUI reads the screen; core reads Claude's own OSC 7501 (not under tmux); no Codex status under core |
| C4 | Needs-you list across sessions, jump to next, notify | F — Inbox across sessions and machines, jump to oldest, bell/notification | F — sidebar roll-up, blocked filter, sounds |
| C5 | Answer permission prompts without opening the pane | F — `peek-prompt` / `respond` re-reads the prompt under a lock and checks its id; or hold `PermissionRequest` (opt-in) | P — blind keys only |
| C6 | Seen vs unseen-done | F | F |
| C7 | Interrupt from outside | P — raw `ctrl+c` / `esc` keys | F — `hc interrupt` |
| C8 | State machine-readable to other tools | F — CLI `--json`, socket, MCP, hooks; daemon JSON in `~/.local/state/tuios/` | F — JSON CLI, `hc events`; `terminals.json` |
| C9 | Agent spawns an agent and gets its result | P — `start-agent`, `ask-agent` (scraped screen) | F — child terminals, `hc wait --children` |
| C10 | Worktree per agent, merge back | F — `worktree new/diff`, `ship commit/merge/pr` | P — TUI create/remove, no merge |
| C11 | Remote machines in one view | F — `tuios hosts` | F — `hc machine add` |
| C12 | Survive terminal quit / daemon restart / reboot | P — terminal quit yes; restart or reboot loses processes, offers `claude --resume` | P — core survives restart; TUI resumes sessions |
| C13 | Neovim integration | P — none of its own | P — none |
| C14 | Greppable transcript | P — reads the harness's JSONL | N |
| C15 | Per-turn checkpoints of code | F — `refs/tuios/checkpoints/…` | N |
| C16 | Hooks that can block a turn on failing checks | P — observe only, 60 s cap | P — observe only |
| C17 | Commits linked to the session | N | N |
| C18 | Usage / cost / budgets | P — opt-in statusline wrapper | N |
| C19 | Headless agents | P — ACP and Codex protocol panes | P — `hc exec` one-shots |
| C20 | Fan one prompt to several agents | F — `fan`, `compare`, `judge-fan` | N |
| C21 | Platform, license, maturity | P — macOS ok, MIT, v0.12.1, 16 releases in 5 weeks, the owner has 5,205 commits and the next contributor 295, ~660k lines of Go | F with risk — macOS/Linux/Windows, Apache-2.0 (from AGPL, 2026-08), $6M-seeded company, Cloud accounts coming, desktop app telemetry on by default |
| | **Total** | **10 F · 10 P · 1 N** | **9 F · 7 P · 5 N** |

**What TUIOS replaces:** the M2 bridge's hosting, input, capture and attach; H4's needs-you list, jump and notifications; answering harness permissions; worktree workspaces; fan-out across terminal agents; the multi-machine view; Codex observed status.

**What neither replaces:** threads as editable context, forks with `## carry`, `steps/`, the spend cap, the git record and trailers, the KB, checks that can block a turn.

### Conditions of use (ARCHITECTURE §5.1)

- Pin the version. Reach TUIOS only through its JSON CLI from one adapter module, so a switch to herdr touches one file.
- `[agents.approvals]` off is simplest. When on, TUIOS holds `PermissionRequest` up to 300 s and the dialog never appears, but the observed status still shows `blocked` (`agent-files-hook` maps `PermissionRequest` too).
- Never use features that type agent-written text into a pane: `ask-agent`, `send-agent-message`, agent mail, the delivery queue. herdr's equivalent is `hc` notes into a parent.
- `agent-files-hook` and `tuios integration install` coexist in `~/.claude/settings.json`: the installer removes only entries containing both ` agent-hook ` and ` --integration ` (`internal/integration/jsonedit.go`) and backs the file up as `settings.json.tuios.bak`. `--statusline` refuses an existing `statusLine` unless given `--then`.
- Known gaps: Esc leaves a Claude pane "working"; Codex hooks break when the shared app-server was started from another pane (TUIOS #1391); verb meanings have changed between releases.
- Switch to herdr if TUIOS misbehaves during the trial. Under herdr-core, run `claude` directly under `hc`, not inside tmux, or Claude never emits OSC 7501.

## 2. Others considered

| Tool | Verdict | Why |
|---|---|---|
| **tmux** | Works, without attention | Stable and scriptable; no agent awareness. Fine as a bare host; TUIOS adds the planned attention layer on top and has a tmux shim. |
| **workmux** | Not adopted | Worktree per tmux window, agent status in window names. TUIOS covers the same and more. |
| **cmux** | A terminal app, not a host | macOS app on libghostty; "does not checkpoint arbitrary live process state", so agents die with the app unless its `local-tmux` mode is used. GPL. Fine as a place to run Neovim. |
| **parrot.nvim** | Not adopted | Chats are markdown files and the whole buffer is the context (replay), but it does less than the M1 runner already built: model output is unescaped (a reply line starting `🗨:` becomes a user turn), no end markers or status, requests die with Neovim, no `steps/`, no cost cap, no git, the model is global rather than per chat, stop reasons ignored, ACP built for Grok. It eliminates no planned work. gp.nvim: same parse and forgery problem, dormant since 2025-08. |
| **Pi Durable** | Not a foundation | Earendil's durable execution for Pi (TypeScript, MIT, "experimental, API changes without notice", 1.0→1.4 in three weeks). One process owns an opaque store (JSONL or SQLite) holding the conversation as immutable entries plus task checkpoints, inbox, live and usage documents and permission memos; nothing is shown before it is committed. A markdown file could only be a one-way projection, and history cannot be edited, so replay (H1) is impossible. It runs only its own loop — it cannot drive Claude Code or Codex. Its recovery patterns are adopted ([juggler-analysis §3](juggler-analysis.md#3-what-we-borrow--translated-to-files)). |
| **Pi** (the agent) | Open question | A small multi-provider loop with an RPC mode; a candidate tier-2 harness for non-Claude models, or the M6 loop (ARCHITECTURE §13 Q12). Claude subscriptions reportedly do not cover third-party harnesses since 2026-04, so Claude in Pi bills per token *(unverified)*; ChatGPT, Copilot and open-model plans are the usual subscription routes. |

## Sources

- TUIOS: [tuios.dev](https://tuios.dev/), [github.com/Gaurav-Gosain/tuios](https://github.com/Gaurav-Gosain/tuios) (`docs/AGENT_STATE.md`, `docs/protocol.md`, `docs/SESSIONS.md`, `internal/integration/`)
- herdr: [herdr.dev/docs](https://herdr.dev/docs/), [herdr.dev/core](https://herdr.dev/core/), [github.com/herdrdev](https://github.com/herdrdev)
- cmux: [github.com/manaflow-ai/cmux](https://github.com/manaflow-ai/cmux) · workmux: [github.com/raine/workmux](https://github.com/raine/workmux)
- parrot.nvim: [github.com/frankroeder/parrot.nvim](https://github.com/frankroeder/parrot.nvim) (v3.0.0, `lua/parrot/chat_handler.lua`, `conversation.lua`) · gp.nvim: [github.com/Robitx/gp.nvim](https://github.com/Robitx/gp.nvim)
- Pi / Pi Durable: [earendil.com/posts/pi-durable](https://earendil.com/posts/pi-durable/), [github.com/earendil-works/pi](https://github.com/earendil-works/pi), npm `@earendil-works/pi-durable@1.4.0`, [Cloudflare Pi harness](https://developers.cloudflare.com/agents/harnesses/pi/), [Vercel Pi harness](https://vercel.com/docs/agent-harnesses/pi)
