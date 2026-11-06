# Plan: Ghostty, tmux and workmux host the agents

> Status: accepted · 2026-11-05 · from a conversation with the operator on how Neovim and agents fit together under tmux · adopted as design in ARCHITECTURE v0.9 (§5.1, §11.4, §12)

**Goal.** Say where the harness sessions run and how they reach Neovim, now that the operator works in Ghostty, tmux and workmux, and drop what that makes redundant. Rex is not used.

**What changed.** On 2026-11-05 the operator set up tmux and workmux in `~/.dotfiles` (`tmux/`, `workmux/`, the workmux hooks in `claude/.claude/settings.json`). tmux holds the panes and shares the Option+n/h/e/u pane moves with Neovim. workmux gives each git worktree a tmux window and tracks its agent's status. Until now agent-files' docs had Rex hosting Neovim, Neovim hosting the sessions in its terminals, and a sidebar in `agents.nvim` to list and switch them. workmux was graded on 2026-11-01 and not adopted because TUIOS covered more ([host-analysis](../../docs/host-analysis.md)). TUIOS and Rex are both out of use now, and workmux is the operator's.

## Decisions

- **D1. Host: Ghostty, tmux, workmux.** Ghostty renders. tmux keeps every pane running when Ghostty quits. workmux makes one tmux window per worktree (`workmux add`, `merge`, `remove`) and reopens them after a crash (`workmux resurrect`). Rex is not used, and its `SessionStart` hook is out of `settings.json` (dotfiles, 2026-11-05). TUIOS and herdr stay unused.
- **D2. Harness sessions run in tmux panes, beside Neovim.** Each worktree window holds Neovim and the harness side by side. The operator's layout is `nvim`, then `claude --ide` to its right (`~/.config/workmux/config.yaml`, kept in dotfiles). Sessions don't run in Neovim's `:terminal`, for three reasons:
  - workmux's status for the window would be shared by every session in that Neovim.
  - `workmux send` and `capture` would reach Neovim, not the agent.
  - Quitting Neovim would end the sessions.
- **D3. Attention and switching are workmux's.** It shows status icons in the tmux window list (working, waiting, done) and has `workmux sidebar`, `workmux dashboard`, `last-done` and `last-agent`, all fed by workmux's own Claude Code hooks. The `agents.nvim` sidebar ([nvim-sidebar](../2026-11-04-nvim-sidebar/nvim-sidebar.md)) is dropped: its steps 1–3 and 5 (start, list, switch, status, keymaps) are what workmux does. Its D4, joining each session to claudecode.nvim, carries on as the IDE link in D4 below. Its D6 resume is `claude --resume` in the pane.
- **D4. Three ways an agent reaches Neovim. None depends on where the agent runs.**

  | Way | What the agent gets | Used by |
  |---|---|---|
  | **In-process.** Lua inside Neovim makes one model call and acts on the reply | Everything Neovim knows at the moment of the request: buffer lines, cursor, selection, buffer list, `:` history. Nothing runs until the operator says so (morla: Enter) | [morla-neovim](https://github.com/markreveley/morla-neovim); [inline questions](../2026-11-04-inline-ask/inline-ask.md) |
  | **IDE link.** claudecode.nvim runs a WebSocket server inside Neovim and writes `~/.claude/ide/<port>.lock` with Neovim's workspace folders. A `claude --ide` (or `/ide`) started in one of those folders connects. With two Neovims on the same folder it can't choose, and `/ide` picks | The selection and cursor as they change; files sent from Neovim (`:ClaudeCodeSend`, `:ClaudeCodeAdd`); open buffers; diagnostics. Its edits open in Neovim as diffs to accept or reject | the `claude` in the next pane |
  | **RPC socket.** Neovim's msgpack-RPC server (`v:servername`; `$NVIM` inside its `:terminal`) | Anything: read and write buffers, run Ex commands, evaluate Lua (`nvim --server <addr> --remote-expr`, or a client library) | `agents.term`, `agent-files-term`. An agent in a tmux pane needs the address; [nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md) is how it would find it |

  The first suits short requests about the editor's state that the operator runs. The second suits a coding session working beside the editor. The third suits tools. Running an agent in Neovim's `:terminal` instead of a tmux pane adds one thing, `$NVIM` set for free; everything else is the same. All three sit outside the thread system, where threads still talk only through files (principle 8).
- **D5. No send policy.** Text typed into a session is the operator's own message relayed, whether the operator types it or a tool the operator runs does (`:AgentsTermSend`, `agent-files-term send`, `workmux send`, a morla command). agent-files does not automate interactive sessions or orchestrate agents through them, so it refuses nothing, whatever the harness.
  - Removed: ARCHITECTURE §5.1's per-harness policy rule and its "Intent decides" exception, the clause in principle 10, `agents.term`'s refusal (`policy`, `b:agents_send`, the `origin` argument) and the AGENTS.md rule.
  - Superseded: [morla](../2026-11-05-morla/morla.md) D1, and the send-policy lines in [nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md).
- **D6. `agents.term` stays, for terminals inside Neovim.** It reaches what tmux can't: to tmux, a `:terminal` in Neovim is part of Neovim's pane. Sessions in tmux panes are read and typed into with `workmux capture` and `workmux send`, or `tmux capture-pane` and `send-keys`. Whether `agents.term` grows a tmux backend or is retired: Q1.

## What it changes elsewhere

- **The observed threads.** `agent-files-hook` still writes them. They are the record of each hand-started session and the status behind `agents.nvim`'s tabline and `:AgentsNext`. workmux's hooks report status too, to tmux, and both sets run side by side in `settings.json`. Whether agent-files keeps observed status, or only the record: Q2. `SessionEnd` still removes the directory; the sidebar's `closed` state (its D6) is not built.
- **The morla command lane** ([morla](../2026-11-05-morla/morla.md), M1.6).
  - Its thread commands (`:AgentsNew`, `:AgentsFork`, `:AgentsStop`, `:AgentsNext`) are unchanged.
  - "Tell the claude in the docs worktree to run the tests" now names a session in a tmux pane, which `:AgentsTermSend` doesn't reach. morla would write `:!workmux send docs '…'`, which it already flags `⚠ shell`.
  - Its D1 is superseded by D5. Whether `command_reference()` lists workmux's targets: Q3.
- **The doorbell revisit** (next-agents, formerly step 5) is answered, and nothing is reinstated. Attention for harness sessions is workmux's (D3), and for agent-files' own threads the file watcher is still enough.
- **[nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md)** no longer waits on the doorbell revisit; the point above answers its Q1, and its Q4 stays open. It becomes how an agent in a tmux pane finds its worktree's Neovim (D4, RPC socket).
- **Smoke S9** starts `claude` in a tmux pane instead of Neovim's `:terminal`.
- **Docs.**
  - Edited in place: ARCHITECTURE v0.9 (header, principle 10, §5, §5.1, §10, §11, §12, §14), README, AGENTS.md, and [operator-neovim](../../docs/operator-neovim.md), rewritten for tmux.
  - Given a superseded line: [rex-host](../../docs/rex-host.md), [host-analysis](../../docs/host-analysis.md), [direction-analysis](../../docs/direction-analysis.md) and [role-of-neovim](../../docs/role-of-neovim.md).

## Steps

1. This plan's PR: the docs above, and `agents.term` and `agent-files-term` without the policy (D5), with their tests.
2. Operator, in a new worktree window (`workmux add <branch>`), checks four things:
   - the `claude` pane connects to Neovim (`/ide` shows it);
   - a selection made in Neovim reaches it;
   - a diff it proposes opens in Neovim;
   - Option+n/h/e/u move between the two panes.
3. Operator: answer Q1–Q3.
4. From the answers:
   - Q1: give `agents.term` a tmux backend, or retire it.
   - Q2: change the hook's status.
   - Q3: the morla lane's targets, at that plan's step 3.
5. Revisit [nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md) for D4: a known socket for each worktree's Neovim, so the agent beside it can reach it. For example, the workmux layout could start `nvim --listen <path>`.

## Questions

- **Q1.** What becomes of `agents.term`?
  - Keep it for terminals inside Neovim only.
  - Give it a tmux backend, so one `:AgentsTerms` covers both.
  - Retire it in favour of `workmux capture` and `send`.

  Recommendation: keep it as it is until a need shows. workmux already covers the panes.
- **Q2.** Should `agent-files-hook` keep writing status (`working`, `blocked`…) beside workmux's? Or should it keep only the record of each session (its directory, `session:`, `transcript_path`) and leave status to workmux? Recommendation: keep only the record. Two status sources for one session can disagree, and `:AgentsNext` would then list only agent-files' own threads.
- **Q3.** Should `command_reference()` ([morla](../2026-11-05-morla/morla.md) D3) list workmux's worktrees and agents, so morla can write `workmux send` commands? Or should harness sessions stay out of the lane? Waits on the morla plan's step 3.
