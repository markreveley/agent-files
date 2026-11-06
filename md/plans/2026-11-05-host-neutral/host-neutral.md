# Plan: host-neutral docs, with Rex as the host again

> Status: accepted · 2026-11-05 · operator's decision · adopted as design in ARCHITECTURE v0.10 (§12, and the host wording throughout) · supersedes [tmux-host](../2026-11-05-tmux-host/tmux-host.md) D1 and D3

**Goal.** Say once what agent-files needs from a host, name the current host in one place, and keep the operator's own host, terminal and editor setup out of this repo. The current host is Superlogical Rex again.

**What changed.** Late on 2026-11-05 the operator switched the host from Ghostty, tmux and workmux back to Superlogical Rex. The switch to tmux earlier that day ([tmux-host](../2026-11-05-tmux-host/tmux-host.md), ARCHITECTURE v0.9) rested partly on two wrong facts: that Rex's remote hosts were only planned (they ship), and that Rex had nothing like workmux's worktrees (it has no worktree command, but its Lua actions and layouts can drive the operator's own worktree tooling). Rex is moving fast: 11 preview builds from 2026-10-19 to 2026-11-05. The operator also set a principle: agent-files keeps the operator's own setup out of the repo, except where it applies to agent-files.

## Decisions

- **D1. ARCHITECTURE states what agent-files requires of a host, and names the current host in one place** (§12). A host must give:
  1. panes that keep running when the terminal app quits;
  2. a pane per harness session beside Neovim, grouped per worktree;
  3. send and capture from a script;
  4. status for harness sessions;
  5. remote machines (optional).

  Everywhere else ARCHITECTURE says "the host" or "the next pane". A host switch then changes §12, a plan like this one and the handoff files, not the design.
- **D2. The current host is Superlogical Rex.** Facts, checked 2026-11-05 from the installed CLI and its docs:
  - **Versions.** The app is Rex Beta 0.1.0 (1829); the CLI is `rex 0.0.1793890641-gaf0c20`, API revision 11. Closed source, built on MIT libghostty. It "is and will always be free", with no account and no telemetry beyond a daily update check.
  - **Against D1:**

    | Requirement | Rex |
    |---|---|
    | 1. Panes outlive the app | A server holds every terminal; the app is one client. Sessions survive the app quitting. A server restart ends the programs (layout and working directories come back); a reboot loses the processes |
    | 2. A pane per session, per worktree | Lua config in `~/.config/rex/init.lua`: actions, keybinds, layouts, `rex.session.new_split`, `new_layer` floats. Panes get `REX_SESSION` and `REX_BLOCK`. No worktree support built in: the operator's own tooling (for example Worktrunk) makes the worktrees |
    | 3. Send and capture | `rex send`, `send-key`, `capture` (text, html or vt), `events --json`, `wait`, `run --wait`, `block call`, and `rex api` (about 75 methods) |
    | 4. Status | Claude Code and Codex emit OSC 7501 to Rex natively, with no hook (tmux blocks this signal). An Activity popup filtered by session or priority, macOS notifications, a Dock badge, and sounds per state |
    | 5. Remote machines | `rex hosts add`, built-in Tailscale; Linux and FreeBSD servers are open to testers. The iOS app is not in public testing yet |

  - **Gaps.** No terminal (TUI) client: outside the Mac app, sessions can be scripted but not watched live. No worktree command (above).
  - **The risk, accepted.** Rex is a closed-source beta. It holds no source of truth for agent-files (principle 1), and the adapter rule (ARCHITECTURE §5.1) keeps a switch cheap.
- **D3. The operator's own setup lives outside agent-files.**
  - What applies to agent-files: what it requires of a host (D1), its own hook, and its own Neovim client, `agents.nvim`. agent-files stays Neovim-first (ARCHITECTURE v0.8).
  - What does not: the operator's layout, keybindings and config notes. `md/docs/operator-neovim.md` said so in its own header, and is removed; the operator keeps it in their own repo. Live docs that pointed at it now say "the operator's own config (outside agent-files)". Records that linked it link a copy pinned at `7ccde4e` ([operator-neovim.md @ 7ccde4e](https://github.com/markreveley/agent-files/blob/7ccde4e2d0832097452fbba81cb215d701ec47ec/md/docs/operator-neovim.md)).
  - Its §3.1, the `agents.term` reference, belongs to `agents.nvim`. ARCHITECTURE §11.2 and the comments in `nvim/lua/agents/term.lua` and `bin/agent-files-term` already carry it; §11.2 gains the exit status, the one part it lacked.
- **D4. What stands from tmux-host, and what is superseded.**
  - **Superseded:** its D1 (the host is Ghostty, tmux and workmux), by D2 here. Its D3 (attention and switching are workmux's): attention for harness sessions is now Rex's program status and Activity view, plus agent-files' observed threads. The sidebar stays dropped: the sessions run in their own panes (its D2), and the host lists them.
  - **Stands, host-neutral:**
    - Its D2: harness sessions run in their own pane beside Neovim, not in Neovim's `:terminal`. The reasons hold for Rex: Rex sees Neovim as one block, so it can't tell the sessions in it apart or show each one's status; `rex send` would reach Neovim, not the agent; and quitting Neovim would end the sessions.
    - Its D4 (three ways an agent reaches Neovim), D5 (no send policy) and D6 (`agents.term` for terminals inside Neovim; sessions in Rex panes are read and typed into with `rex capture` and `rex send`).
  - **Its questions:**
    - Q1 (`agents.term`) is unchanged; a host backend would be a Rex backend.
    - Q2 (the hook's status beside the host's) is still open. Under Rex the host's status is native OSC 7501, not a hook. The recommendation stays "record only".
    - Q3: morla's lane would write `rex send …` instead of `workmux send …`.
  - **Its steps:** step 2, the layout check, is redone in Rex (step 4 below). Steps 3–5 stand.

## What it changes elsewhere

- **ARCHITECTURE v0.10.** §12 becomes "Relation to hosts": the requirements (D1), the current host (D2), and the risk. The header, §1, §5, §5.1, §8, §9.2, §10, §11, §11.2–§11.4 and §14 say "the host" or "the next pane".
- **README, AGENTS.md.** The host paragraph is host-neutral and names Rex; the operator's layout is gone.
- **Removed:** `md/docs/operator-neovim.md` (D3).
- **Status lines added:** [tmux-host](../2026-11-05-tmux-host/tmux-host.md), [rex-host](../../docs/rex-host.md), [host-analysis](../../docs/host-analysis.md), [direction-analysis](../../docs/direction-analysis.md), [role-of-neovim](../../docs/role-of-neovim.md), and the plans that named tmux ([morla](../2026-11-05-morla/morla.md), [nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md), [nvim-sidebar](../2026-11-04-nvim-sidebar/nvim-sidebar.md)).
- **Smoke S9** starts `claude` in a Rex pane.
- **No code changes.** No comment in `nvim/`, `bin/` or `lib/` names tmux, workmux or Rex.
- **morla-neovim:** the host line in its `next-agents.md`.

## Steps

1. This plan's PR: the docs above.
2. Operator: answer Q1 (the hooks) and change `~/.claude/settings.json` (and `~/.codex/hooks.json`) in the dotfiles to match.
3. Operator: build the Rex setup, outside agent-files:
   - worktree actions, with the operator's own worktree tooling;
   - pane moves between Neovim and the agent pane;
   - a known Neovim socket per worktree, so the agent beside it can reach it ([nvim-addressing](../2026-11-03-nvim-addressing/nvim-addressing.md); tmux-host step 5).
4. Operator, in a worktree's Rex tab, the check that tmux-host step 2 described:
   - the `claude` pane connects to Neovim (`/ide` shows it);
   - a selection made in Neovim reaches it;
   - a diff it proposes opens in Neovim;
   - the pane moves work between the two panes;
   - Rex shows the `claude` pane's status (Activity view).
5. Operator: tmux-host Q1–Q3, read as in D4. Then tmux-host step 4 acts on the answers.

## Questions

- **Q1. The hooks.** Answered (operator, 2026-11-05): Rex's Claude Code `SessionStart` hook is back as it was before dotfiles `bd9e045`, and workmux's hooks are out of `settings.json` and `~/.codex/hooks.json` (dotfiles `0d3bbd2`). Steps 2 and 3 are done; step 4 is partly checked (next-operator 2a).
- tmux-host Q1–Q3 stay open there, read as in D4.
