# agent-files

The logbook for human–agent work: every exchange a file you can edit as context, every settled conclusion a node that records who or what accepted it, every change linked to the turns and decisions behind it — in Neovim, beside the harnesses.

Direction: [md/docs/direction-analysis.md](md/docs/direction-analysis.md). Design: [ARCHITECTURE.md](md/governance/ARCHITECTURE.md). This build (M1, threads as plain-text files): [md/docs/m1-build-spec.md](md/docs/m1-build-spec.md).

| Piece | What |
|---|---|
| `bin/agent-files-run` | replay runtime: `init`, `watch`, `once <thread>`, `check <thread>` |
| `bin/agent-files-hook` | Claude Code hook → observed status for hand-started sessions |
| `bin/agent-files-stats` | threads, turns, spend per day and per thread, live observed sessions |
| `bin/agent-files-grep` | `rg` over all threads |
| `bin/agent-files-term` | list, read and type into Neovim's terminal buffers (ARCHITECTURE §11.2) |
| `nvim/` | `agents.nvim`: marks, read-only while working, `:AgentsNew/Send/Stop/Fork/Next/Blocked/Grep`; `:AgentsTerms`, `:AgentsTermSend`, `:AgentsTermCapture` |

## What is where

| path | holds |
|---|---|
| `bin/`, `lib/agent_files/`, `nvim/`, `install.sh` | the tools above, their shared Python, the Neovim plugin, the installer |
| `tests/` | unit, Neovim and smoke tests; `tests/fixtures/` is Markdown the tests read (in `.layoutignore`) |
| [`md/`](md/README.md) | the prose: [ARCHITECTURE](md/governance/ARCHITECTURE.md), docs, plans, analyses, issues |
| `AGENTS.md` | working rules for agents and people; `CLAUDE.md` imports it |
| `next-agents.md`, `next-operator.md` | handoff: where the last thread stopped |

**The data root is `~/agent-files/` (or `$AGENT_FILES_ROOT`) — do not clone this repo there.**

agent-files is built around Neovim, where you read and write threads. The host is Ghostty, tmux and [workmux](https://github.com/raine/workmux): Claude Code and Codex sessions run in tmux panes beside Neovim, one tmux window per git worktree, and workmux tracks their status and switches between them. tmux keeps everything running when Ghostty quits. agent-files observes the sessions through Claude Code hooks. Why, and how agents reach Neovim: [md/plans/2026-11-05-tmux-host/tmux-host.md](md/plans/2026-11-05-tmux-host/tmux-host.md), ARCHITECTURE §11.4.

Install from a clone of its own, not the one you develop in: `install.sh` links `~/.local/bin/agent-files-*` into whichever clone it runs from, so the tools you run would change with every branch you check out. The operator's install clone is `~/code/agent-files`. To update it after a merge: `git -C ~/code/agent-files pull --ff-only`, then run its `./install.sh` again (needed only when a new executable is added).

```sh
./install.sh                 # symlinks bin/*, prints the hook block for ~/.claude/settings.json
agent-files-run init
agent-files-run watch        # leave running
```
Neovim (0.9+; spec says 0.10+): add `nvim/` to `runtimepath`, then `require('agents').setup({ root = '~/agent-files', tabline = true })`.

## Tests
```sh
python3 -W ignore -m unittest discover -s tests -t .      # parser, assembly, runner, hook, stats
nvim --headless -u NONE -l tests/nvim/test_agents.lua     # plugin (run from repo root)
sh tests/smoke.sh                                         # smoke S1–S5 with the mock backend
```
Smoke S6–S11 (real model, local model, real `claude`, editor) are by hand — spec §10.2.
