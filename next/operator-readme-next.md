# Next steps for the operator

M1 is built and tested against the mock backend only. Nothing has run against a real model, your editor or a real `claude` session yet. This is what you do to finish the build and start the ten-day trial. The agent-side backlog is in [agents-readme-next.md](agents-readme-next.md).

## Where you are (checked 2026-11-01)
- Done: clone at `~/code/agent-files`, `./install.sh` run (links in `~/.local/bin`, on `PATH`). Present: `uv`, `git`, Python 3.14, Neovim 0.12.5.
- Not done: `agent-files-run init` (no `~/agent-files` yet), `rg`, `ANTHROPIC_API_KEY` (unset in the shell checked), the hook block in `~/.claude/settings.json`, TUIOS.
- Landed since: agent item 2, the hook verified against the hooks reference (PR #10). Steps 3 and 3a are no longer on hold.
- **Next:** `agent-files-run init`, `brew install ripgrep`, step 2, then steps 3-8 in order.
- **Hold:** agent items 1 and 5 wait until after the trial. Item 1 changes the runner, so if you want it, have it done before S6, not mid-trial. Build nothing new before the day-10 decision ([m1-plan §5](../docs/m1-plan.md#5-decision-criteria)).

## 1. Install (about 10 minutes)
```sh
git clone https://github.com/markreveley/agent-files ~/code/agent-files   # NOT ~/agent-files, that is the data root
cd ~/code/agent-files && ./install.sh                                     # links bin/* into ~/.local/bin
agent-files-run init                                                       # creates ~/agent-files with config.toml, agents/, trial/
```
Requirements: Python 3.11+, `uv`, `git`, `rg`, Neovim (0.10+ per the spec; 0.9.5 passed the tests). `rg` must be a standalone binary (`brew install ripgrep`): the `rg` inside a Claude Code shell is a wrapper around Claude Code's bundled copy and is not on your own `PATH`. `agent-files-grep` and `:AgentsGrep` (S10) need it.

## 2. Configure
- Edit `~/agent-files/config.toml`: set `[prices.<model>]` for every model you will use (unknown models count as $0 and the spend cap then protects nothing) and check `daily_spend_cap_usd`.
- Export `ANTHROPIC_API_KEY` in the shell that runs the runner.
- For local models, make sure Ollama or LM Studio is running at the `base_url` in the config.

## 3. Hook up Claude Code
First `git pull` in `~/code/agent-files` and re-run `./install.sh`: the hook was verified against the Claude Code hooks reference (PR #10) and its block now registers ten events, including `PermissionRequest`, `PostToolUseFailure` and `StopFailure`. If you pasted an older block, replace it.

Paste the block `install.sh` printed into `~/.claude/settings.json` (merge with existing `hooks`). Do this before 3a. S9 below is the end-to-end check.

## 3a. Host Claude Code and Codex in TUIOS
Since 2026-11-01 TUIOS hosts harness sessions and owns attention for them ([docs/host-analysis.md](../docs/host-analysis.md), ARCHITECTURE §5.1).
- Install TUIOS (Homebrew or a release binary, per [tuios.dev](https://tuios.dev/)) and **pin the version** you start the trial with; do not upgrade mid-trial.
- Installing the binary can happen any time; run the next bullet only after step 3, so the `agent-files-hook` entries are already there for it to leave alone.
- `tuios integration install` for Claude Code (and Codex) so its Inbox gets hook-reported state. It adds its own entries to `~/.claude/settings.json`, leaves the `agent-files-hook` entries alone and keeps a `settings.json.tuios.bak`. Check both sets of hooks are present afterwards.
- `[agents.approvals]` **off** is simplest. If you turn it on, TUIOS holds permission prompts for up to 300 s and Claude's own dialog doesn't appear, but the observed status still shows `blocked` (`agent-files-hook` maps `PermissionRequest`).
- Don't pass `--statusline` unless you also pass `--then <your current statusline command>`; it refuses to replace an existing one otherwise.
- Don't use `ask-agent`, agent mail or the delivery queue on Claude sessions: they type agent-written text into the TUI (ARCHITECTURE §5.1 policy rule).
- If TUIOS misbehaves during the trial, note it in the journal and switch to herdr. Known gaps: Esc leaves a pane "working"; Codex hooks can break when its app-server was started from another pane (TUIOS #1391).

## 4. Editor
Add `~/code/agent-files/nvim` to Neovim's `runtimepath` and call:
```lua
require('agents').setup({ root = '~/agent-files', tabline = true })
```
Do view-layer step 0 (a generic markdown renderer, about an hour) and confirm you can read `docs/examples/view-fixture/thread.md` comfortably. A trial that fails on unpleasant reading tests your editor setup, not the idea.

## 5. Start the runner
```sh
agent-files-run watch     # leave running; a second copy exits with code 2
```

## 6. Run the manual smoke tests (spec §10.2)
`sh tests/smoke.sh` already covers S1-S5 with the mock backend. By hand:

| # | Do | Pass when |
|---|---|---|
| S6 | `model: claude-opus-5-5`, send twice within 5 min | real reply; second `steps/*.response.json` has `cache_read_input_tokens > 0` |
| S7 | delete an earlier agent turn, rewrite your first turn, send | reply arrives, no 400 |
| S8 | `model: ollama/<name>`, send | reply, `cost_usd: 0` |
| S9 | start `claude` in a project **inside TUIOS**, trigger a permission prompt | `_observed/...` appears; `:AgentsNext` shows `blocked` as soon as the permission dialog opens (not ~6 s later), then `working`, `done`, gone on exit; the TUIOS Inbox shows the same prompt |
| S10 | `:AgentsGrep <word>` | quickfix hits, one line in `trial/searches.log` |
| S11 | open a smoke thread and the view fixture | headers/`END` highlighted, end mark shows status and `~Nk`, tool fold closed. Also (agent item 3): during a running turn the spinner moves and the buffer is read-only; when the reply lands the buffer reloads with no "file changed" prompt and becomes writable again |

If one fails, note it and hand it to an agent with the exact symptom and the thread's `steps/` files.

## 7. Start the trial
When S1-S11 pass, write the date at the top of `~/agent-files/trial/journal.md`: that is day 1. Each day fill the journal template. Daily commands:
```sh
agent-files-stats          # H1-H3 numbers, plus observed sessions (information only; H4 is dropped) and spend
agent-files-stats --json
```
Keep the data root under git; it records your edits for the H1 measurement.

## 8. Day 10: decide
Use the go and kill thresholds printed by `agent-files-stats` (H1 go at 20% or more, kill under 5%; H2 go at 5 forks or more, kill under 2), plus the journal's "Used instead" and "Read threads in" lines. H4 is not part of the decision. The HTML view is judged separately from the journal, not from H1-H3.

## Things to watch
- `status` shows `?` for a turn working more than 10 minutes with no heartbeat: the runner probably died; restart `watch` and it will close the turn as interrupted.
- Do not edit a thread's `thread.md` from another tool while a turn is running; the runner treats that as a conflict and ends the turn with `END (conflict)` (output saved in `out/`).
- Pull requests from the agent side land on `main` of this repo; the data root is separate and never pushed by these programs.
