---
type: handoff
audience: operator
updated: 2026-11-03
---

# Next steps for the operator

Read with [next-agents.md](next-agents.md). M1 is built and tested against the mock backend, and the bugs an audit found on 2026-11-02 are fixed (PR #24). Nothing has yet run through the runner against a real model, in your editor, or with a live `claude` session. These steps finish the build and start the ten-day trial.

Where this goes after the trial: [md/docs/direction-analysis.md](md/docs/direction-analysis.md) (decided 2026-11-02). It changes nothing below.

Already done on this Mac: the clone at `~/code/agent-files` (at `f627b15`; step 2 pulls the audit fixes and the `md/` layout), `./install.sh` (links in `~/.local/bin`, on `PATH`), `uv`, `git`, Python 3.14, Neovim 0.12.5, Rex Beta 0.1.0 (the host, step 2a), TUIOS 0.12.1 (the fallback, pinned with `brew pin tuios`), ripgrep 15.2.0, and `agent-files-run init`. The data root is at `~/dev/repos/agent-files-data`, with `~/agent-files` linking to it. It has no remote; add a private one if you want an offsite backup, and push it yourself.

## 1. Configure
- Prices are done (agent, at your request, 2026-11-02): `~/agent-files/config.toml` has blocks for `claude-opus-5-5`, `claude-fable-5-1`, `claude-sonnet-5-5` and `claude-haiku-5-5`, checked against Anthropic's pricing page that day. The edit is not committed in the data root; commit it if you want it in history. Any other paid model needs its own block, keyed by the exact `model:` name in quotes; without one it counts as $0 and the spend cap doesn't protect it. Local `ollama/...` and `lmstudio/...` models need none.
- Check `daily_spend_cap_usd` (default $5.00 a day, all threads together).
- Export `ANTHROPIC_API_KEY` in the shell that runs the runner.
- For local models, make sure Ollama or LM Studio is running at the `base_url` in the config.

## 2. Hook up Claude Code
First run `git -C ~/code/agent-files pull`; the audit fixes (2026-11-02) must be in the install clone. Then run `./install.sh` in `~/code/agent-files` and add the hook block it prints to `~/.claude/settings.json`. The block registers ten events, including `PermissionRequest`, `PostToolUseFailure` and `StopFailure`, and calls the hook by its absolute path. It was verified against the Claude Code hooks reference.

Merge it; don't paste it in whole. Your `settings.json` already has a `"hooks"` object with arrays for `SessionStart`, `PreToolUse`, `PostToolUse` and `PostToolUseFailure`. For those four events, add the printed `{ "hooks": [ … ] }` entry to the existing array. Add the other six events as new keys in the same `"hooks"` object. A second `"hooks"` key would silently drop one set. Afterwards check it with `python3 -m json.tool ~/.claude/settings.json > /dev/null`.

Do this before 2a. S9 below is the end-to-end check.

## 2a. Host in Rex
Since 2026-11-03 Rex hosts harness sessions and your editor; TUIOS is the fallback ([md/docs/rex-host.md](md/docs/rex-host.md), ARCHITECTURE §5.1).
- Done by the agent on 2026-11-03: `rex` is linked into `~/.local/bin` from `/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex`. Rex's Claude Code hook (added by `rex skill setup`, already in `~/.claude/settings.json`) calls `rex` by name and failed silently before that. If a Rex update moves the binary, `which rex` stops finding it; re-link it.
- One Rex session per repo, Neovim in it, harnesses in Neovim's `:terminal` as you do now. Quitting the app keeps them all; reopening attaches again.
- Don't run `tuios integration install`; TUIOS stays installed and pinned at 0.12.1 as the fallback. If Rex misbehaves during the trial, note it in the journal and switch.
- The policy rule (ARCHITECTURE §5.1): agents must not `rex send` their own text into a pane running `claude` or `codex`. The Rex skill teaches agents `rex send` for any pane, and nothing stops it there. Inside Neovim, `agent-files-term` refuses it.
- Remote hosts (`rex hosts add LABEL ENDPOINT`) are optional and not part of the trial.

## 3. Editor
Add `~/code/agent-files/nvim` to Neovim's `runtimepath` and call:
```lua
require('agents').setup({ root = '~/agent-files', tabline = true })
```
That also defines `:AgentsTerms`, `:AgentsTermSend` and `:AgentsTermCapture` (ARCHITECTURE §11.2); your own layout is in [md/operator-neovim.md](md/operator-neovim.md). They are outside the trial's measurement.
Do view-layer step 0 (a generic markdown renderer, about an hour) and confirm you can read `md/docs/examples/view-fixture/thread.md` comfortably. A trial that fails on unpleasant reading tests your editor setup, not the idea.

## 4. Start the runner
```sh
agent-files-run watch     # leave running; a second copy exits with code 2
```
Tell the agent when `watch` is running, or which of steps 1-4 failed and how.

## 5. Run the manual smoke tests (spec §10.2)
`sh tests/smoke.sh` already covers S1-S5 with the mock backend. By hand:

| # | Do | Pass when |
|---|---|---|
| S6 | `model: claude-opus-5-5`. Make the first message long: paste 2,000+ characters of real text (Opus 5.5 caches nothing under 512 tokens, and a short exchange reads 0 even when caching works). Send, then send a short second message within 5 min | real reply; second `steps/*.response.json` has `cache_read_input_tokens > 0` |
| S7 | delete an earlier agent turn, rewrite your first turn, send | reply arrives, no 400 |
| S8 | `model: ollama/<name>`, send | reply, `cost_usd: 0` |
| S9 | start `claude` in a project **inside Rex** (in Neovim's `:terminal`, as you work), trigger a permission prompt | a directory `~/agent-files/threads/_observed/<project>-…/` appears. `:AgentsNext` lists it as blocked as soon as the permission dialog opens (not ~6 s later). Open its `thread.md`: after you answer, the end mark shows the spinner (working), then ✓ (done) when Claude finishes. The directory is gone after you exit `claude`. Note in the journal what Rex's Activity sidebar shows for it (ARCHITECTURE §13 Q14). (`:AgentsNext` lists only threads that need you, never working ones.) |
| S10 | `:AgentsGrep <word>` | quickfix hits, one line in `trial/searches.log` |
| S11 | first copy the view fixture into the root: `cp -R ~/code/agent-files/md/docs/examples/view-fixture ~/agent-files/threads/fixture` (the plugin only attaches to files under `threads/`). Open it, and your S6 thread | headers/`END` highlighted, tool fold closed, end mark shows `~Nk`. A status glyph shows only while a turn is running or its result is unseen: once you have viewed a finished thread the glyph goes away. Also (the interactive Neovim check): send a turn in the S6 thread; while it runs the spinner moves and the buffer is read-only; when the reply lands the buffer reloads with no "file changed" prompt, shows ✓ and becomes writable again. Then `rm -r ~/agent-files/threads/fixture` so it isn't counted in the trial |

Report the result of each of S6-S11 to the agent. For a failure, include the exact symptom and the thread's `steps/` files.

## 6. Start the trial
When S1-S11 pass, change the first heading of `~/agent-files/trial/journal.md` (`init` wrote `## 2026-11-02`) to today's date: that is day 1. Each day fill the journal template. Daily commands:
```sh
agent-files-stats          # H1-H3 numbers, plus observed sessions (information only; H4 is dropped) and spend
agent-files-stats --json
```
Keep the data root under git; it records your edits for the H1 measurement.

Optional, for the planning harness (ARCHITECTURE §13 Q17). If you run some threads with `model: claude-cli` (your plan, through `claude -p`), note in the journal whether they read as well as threads on the API backend. Their `steps/*.response.json` already records `cache_read_input_tokens`; nothing to do for that.

## 7. Day 10: decide
Use the go and kill thresholds in [m1-plan §5](md/docs/m1-plan.md#5-decision-criteria). `agent-files-stats` prints the H1 percentage, the fork count and the search count. The H2 helped/hurt tally, the H3 count of searches whose result you used, and the fallback rate come from the journal ("Forks today", "Searches whose result I used", "Used instead"). Also use the journal's "Read threads in" lines. H4 is not part of the decision. The HTML view is judged separately from the journal, not from H1-H3.

Then, with the agent:
- Confirm or change the order after M1 (ARCHITECTURE §14: the record trial, then the planning harness, then the record viewer).
- Decide whether the record trial (attribution and the DAG on real coding work) still runs if H1-H3 fail. It tests a different thesis ([direction-analysis §8](md/docs/direction-analysis.md#8-the-trials)).

## Things to watch
- `status` shows `?` for a turn working more than 10 minutes with no heartbeat: the runner probably died; restart `watch` and it will close the turn as interrupted.
- Refusals: the fallback to another model is built after the trial (your decision, 2026-11-01), and `fallbacks = true` in `config.toml` does nothing yet. A refused turn ends as a failed turn with `! error: refusal (<category>)`. Rephrase and send again, or switch `model:` for that thread.
- `model: claude-cli` runs on your plan: the runner keeps `ANTHROPIC_API_KEY` away from `claude -p` (fixed 2026-11-02). With no `/<model>` suffix it uses Claude Code's default model, which was Fable 5.1 on this Mac; write `claude-cli/claude-opus-5-5` to pin one.
- `claude-cli` turns record the `total_cost_usd` that `claude -p` reports, which is an API-equivalent figure even on your plan, and it counts toward `daily_spend_cap_usd`. Several `claude-cli` threads in a day can hit the cap though you paid nothing extra; raise the cap if that blocks you.
- `claude-cli` turns carry a small `userEmail`/`Environment` block that Claude Code adds and no flag removes (spec §14.1); leave them out of any cache or request comparison.
- Do not edit a thread's `thread.md` from another tool while a turn is running; the runner treats that as a conflict and ends the turn with `END (conflict)` (output saved in `out/`).
- Pull requests from the agent side land on `main` of this repo; the data root is separate and never pushed by these programs.

## Questions
- None blocking.
- To answer eventually: [md/plans/dag-orchestration.md](md/plans/dag-orchestration.md#questions) (DAG-grounded orchestration, five questions, needed before M6).
- After day 10: [md/plans/nvim-addressing.md](md/plans/nvim-addressing.md) (Neovims addressable by repo name). Q4 (replace `nvim` or use another name?) is open; Q1 waits on the agent's doorbell revisit (next-agents step 7).
