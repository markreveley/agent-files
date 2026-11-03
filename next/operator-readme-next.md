---
type: handoff
audience: operator
updated: 2026-11-02
---

# Next steps for the operator

Read with [agents-readme-next.md](agents-readme-next.md). M1 is built and tested against the mock backend. Nothing has yet run through the runner against a real model, in your editor, or with a live `claude` session. These steps finish the build and start the ten-day trial.

Where this goes after the trial: [docs/direction-analysis.md](../docs/direction-analysis.md) (decided 2026-11-02). It changes nothing below.

Already done on this Mac: the clone at `~/code/agent-files` (pulled to `f627b15` on 2026-11-02), `./install.sh` (links in `~/.local/bin`, on `PATH`), `uv`, `git`, Python 3.14, Neovim 0.12.5, TUIOS 0.12.1 (pinned with `brew pin tuios`), ripgrep 15.2.0, and `agent-files-run init`. The data root is at `~/dev/repos/agent-files-data`, with `~/agent-files` linking to it. It has no remote; add a private one if you want an offsite backup, and push it yourself.

## 1. Configure
- Edit `~/agent-files/config.toml`: set `[prices.<model>]` for every model you will use (unknown models count as $0 and the spend cap then protects nothing) and check `daily_spend_cap_usd`.
- Export `ANTHROPIC_API_KEY` in the shell that runs the runner.
- For local models, make sure Ollama or LM Studio is running at the `base_url` in the config.

## 2. Hook up Claude Code
Re-run `./install.sh` in `~/code/agent-files` and paste the hook block it prints into `~/.claude/settings.json`, merging with the existing `hooks`. The block registers ten events, including `PermissionRequest`, `PostToolUseFailure` and `StopFailure`; it was verified against the Claude Code hooks reference. Do this before 2a. S9 below is the end-to-end check.

## 2a. Host Claude Code and Codex in TUIOS
Since 2026-11-01 TUIOS hosts harness sessions and owns attention for them ([docs/host-analysis.md](../docs/host-analysis.md), ARCHITECTURE §5.1).
- TUIOS is installed and pinned at 0.12.1; do not upgrade it mid-trial.
- Run this after step 2, so the `agent-files-hook` entries are already there for it to leave alone: `tuios integration install` for Claude Code (and Codex) so its Inbox gets hook-reported state. It adds its own entries to `~/.claude/settings.json`, leaves the `agent-files-hook` entries alone and keeps a `settings.json.tuios.bak`. Check both sets of hooks are present afterwards.
- `[agents.approvals]` **off** is simplest. If you turn it on, TUIOS holds permission prompts for up to 300 s and Claude's own dialog doesn't appear, but the observed status still shows `blocked` (`agent-files-hook` maps `PermissionRequest`).
- Don't pass `--statusline` unless you also pass `--then <your current statusline command>`; it refuses to replace an existing one otherwise.
- Don't use `ask-agent`, agent mail or the delivery queue on Claude sessions: they type agent-written text into the TUI (ARCHITECTURE §5.1 policy rule).
- If TUIOS misbehaves during the trial, note it in the journal and switch to herdr. Known gaps: Esc leaves a pane "working"; Codex hooks can break when its app-server was started from another pane (TUIOS #1391).

## 3. Editor
Add `~/code/agent-files/nvim` to Neovim's `runtimepath` and call:
```lua
require('agents').setup({ root = '~/agent-files', tabline = true })
```
Do view-layer step 0 (a generic markdown renderer, about an hour) and confirm you can read `docs/examples/view-fixture/thread.md` comfortably. A trial that fails on unpleasant reading tests your editor setup, not the idea.

## 4. Start the runner
```sh
agent-files-run watch     # leave running; a second copy exits with code 2
```
Tell the agent when `watch` is running, or which of steps 1-4 failed and how.

## 5. Run the manual smoke tests (spec §10.2)
`sh tests/smoke.sh` already covers S1-S5 with the mock backend. By hand:

| # | Do | Pass when |
|---|---|---|
| S6 | `model: claude-opus-5-5`, send twice within 5 min | real reply; second `steps/*.response.json` has `cache_read_input_tokens > 0` |
| S7 | delete an earlier agent turn, rewrite your first turn, send | reply arrives, no 400 |
| S8 | `model: ollama/<name>`, send | reply, `cost_usd: 0` |
| S9 | start `claude` in a project **inside TUIOS**, trigger a permission prompt | `_observed/...` appears; `:AgentsNext` shows `blocked` as soon as the permission dialog opens (not ~6 s later), then `working`, `done`, gone on exit; the TUIOS Inbox shows the same prompt |
| S10 | `:AgentsGrep <word>` | quickfix hits, one line in `trial/searches.log` |
| S11 | open a smoke thread and the view fixture | headers/`END` highlighted, end mark shows status and `~Nk`, tool fold closed. Also (the interactive Neovim check): during a running turn the spinner moves and the buffer is read-only; when the reply lands the buffer reloads with no "file changed" prompt and becomes writable again |

Report the result of each of S6-S11 to the agent. For a failure, include the exact symptom and the thread's `steps/` files.

## 6. Start the trial
When S1-S11 pass, write the date at the top of `~/agent-files/trial/journal.md`: that is day 1. Each day fill the journal template. Daily commands:
```sh
agent-files-stats          # H1-H3 numbers, plus observed sessions (information only; H4 is dropped) and spend
agent-files-stats --json
```
Keep the data root under git; it records your edits for the H1 measurement.

Optional, for the planning harness (ARCHITECTURE §13 Q17). If you run some threads with `model: claude-cli` (your plan, through `claude -p`), note in the journal whether they read as well as threads on the API backend. Their `steps/*.response.json` already records `cache_read_input_tokens`; nothing to do for that.

## 7. Day 10: decide
Use the go and kill thresholds in [m1-plan §5](../docs/m1-plan.md#5-decision-criteria) (H1-H3 and the fallback rate; `agent-files-stats` prints the numbers), plus the journal's "Used instead" and "Read threads in" lines. H4 is not part of the decision. The HTML view is judged separately from the journal, not from H1-H3.

Then, with the agent:
- Confirm or change the order after M1 (ARCHITECTURE §14: the record trial, then the planning harness, then the record viewer).
- Decide whether the record trial (attribution and the DAG on real coding work) still runs if H1-H3 fail. It tests a different thesis ([direction-analysis §8](../docs/direction-analysis.md#8-the-trials)).

## Things to watch
- `status` shows `?` for a turn working more than 10 minutes with no heartbeat: the runner probably died; restart `watch` and it will close the turn as interrupted.
- Refusals: the fallback to another model is built after the trial (your decision, 2026-11-01), and `fallbacks = true` in `config.toml` does nothing yet. A refused turn ends as a failed turn with `! error: refusal (<category>)`. Rephrase and send again, or switch `model:` for that thread.
- `claude-cli` turns carry a small `userEmail`/`Environment` block that Claude Code adds and no flag removes (spec §14.1); leave them out of any cache or request comparison.
- Do not edit a thread's `thread.md` from another tool while a turn is running; the runner treats that as a conflict and ends the turn with `END (conflict)` (output saved in `out/`).
- Pull requests from the agent side land on `main` of this repo; the data root is separate and never pushed by these programs.

## Questions
- None open.
