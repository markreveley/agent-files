# Next steps for the operator

M1 is built and tested against the mock backend only. Nothing has run against a real model, your editor or a real `claude` session yet. This is what you do to finish the build and start the ten-day trial. The agent-side backlog is in [readme-agents-next.md](readme-agents-next.md).

## 1. Install (about 10 minutes)
```sh
git clone https://github.com/markreveley/agent-files ~/code/agent-files   # NOT ~/agent-files, that is the data root
cd ~/code/agent-files && ./install.sh                                     # links bin/* into ~/.local/bin
agent-files-run init                                                       # creates ~/agent-files with config.toml, agents/, trial/
```
Requirements: Python 3.11+, `uv`, `git`, `rg`, Neovim (0.10+ per the spec; 0.9.5 passed the tests).

## 2. Configure
- Edit `~/agent-files/config.toml`: set `[prices.<model>]` for every model you will use (unknown models count as $0 and the spend cap then protects nothing) and check `daily_spend_cap_usd`.
- Export `ANTHROPIC_API_KEY` in the shell that runs the runner.
- For local models, make sure Ollama or LM Studio is running at the `base_url` in the config.

## 3. Hook up Claude Code
Paste the block `install.sh` printed into `~/.claude/settings.json` (merge with existing `hooks`). The hook's event names and `Notification` fields have not been verified against current docs; S9 below is the check.

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
| S9 | start `claude` in a project, trigger a permission prompt | `_observed/...` appears, `:AgentsNext` shows `blocked`, then `working`, `done`, gone on exit |
| S10 | `:AgentsGrep <word>` | quickfix hits, one line in `trial/searches.log` |
| S11 | open a smoke thread and the view fixture | headers/`END` highlighted, end mark shows status and `~Nk`, tool fold closed |

If one fails, note it and hand it to an agent with the exact symptom and the thread's `steps/` files.

## 7. Start the trial
When S1-S11 pass, write the date at the top of `~/agent-files/trial/journal.md`: that is day 1. Each day fill the journal template. Daily commands:
```sh
agent-files-stats          # H1-H4 numbers: context edits, forks, searches, observed sessions, spend
agent-files-stats --json
```
Keep the data root under git; it records your edits for the H1 measurement.

## 8. Day 10: decide
Use the go and kill thresholds printed by `agent-files-stats` (H1 go at 20% or more, kill under 5%; H2 go at 5 forks or more, kill under 2), plus the journal's "Used instead" and "Read threads in" lines. The HTML view is judged separately from the journal, not from H1-H4.

## Things to watch
- `status` shows `?` for a turn working more than 10 minutes with no heartbeat: the runner probably died; restart `watch` and it will close the turn as interrupted.
- Do not edit a thread's `thread.md` from another tool while a turn is running; the runner treats that as a conflict and ends the turn with `END (conflict)` (output saved in `out/`).
- Pull requests from the agent side land on `main` of this repo; the data root is separate and never pushed by these programs.
