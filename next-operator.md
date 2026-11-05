---
type: handoff
audience: operator
updated: 2026-11-04
---

# Next steps for the operator

Read with [next-agents.md](next-agents.md).

**What changed on 2026-11-04** (thread: thread-archive `threads/agent-files/2026-11-04-nvim-sidebar.md`):
- **The trial is gone.** No hypotheses, journal, measurement or day-10 decision, and no freeze: building goes ahead. `init` no longer creates `trial/`, the hook and `agent-files-grep` no longer log there, and `agent-files-stats` now reports threads, turns, spend and live observed sessions.
- **agent-files is Neovim-first** (ARCHITECTURE v0.8). `agents.nvim` will host your `claude` and `codex` sessions in terminal buffers, listed in a sidebar beside agent-files' own threads. Rex hosts Neovim. The separate neovim-agent-sidebar repo is folded in: its design is now [md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md](md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md), which the agent builds next.

M1 is built and tested against the mock backend. Nothing has yet run through the runner against a real model, in your editor, or with a live `claude` session; steps 1-5 below do that.

Already done on this Mac: the install clone at `~/code/agent-files` (pulled to `1a85870` on 2026-11-04; see README), `./install.sh` (links in `~/.local/bin`, on `PATH`), `uv`, `git`, Python 3.14, Neovim 0.12.5, Rex Beta 0.1.0, ripgrep 15.2.0, and `agent-files-run init`. The data root is at `~/dev/repos/agent-files-data`, with `~/agent-files` linking to it. It has a private remote (`markreveley/agent-files-data`, added 2026-11-04); nothing pushes it automatically, so `git -C ~/agent-files push` when you want a backup.

## 0. Tidy up after the change
- Delete the neovim-agent-sidebar repo: its GitHub repo (`markreveley/neovim-agent-sidebar`) and the local checkout `~/dev/repos/neovim-agent-sidebar`. GitHub has no commits; the local checkout has one (the layout and the superseded v1 plan) and uncommitted edits, none of which is needed: the plan lives on here.

## 1. Configure
- Prices are done (2026-11-02): `~/agent-files/config.toml` has blocks for `claude-opus-5-5`, `claude-fable-5-1`, `claude-sonnet-5-5` and `claude-haiku-5-5`. Any other paid model needs its own block, keyed by the exact `model:` name in quotes; without one it counts as $0 and the spend cap doesn't protect it. Local `ollama/...` and `lmstudio/...` models need none.
- Check `daily_spend_cap_usd` (default $5.00 a day, all threads together).
- Export `ANTHROPIC_API_KEY` in the shell that runs the runner.
- For local models, make sure Ollama or LM Studio is running at the `base_url` in the config.

## 2. Hook up Claude Code
The sidebar's status for Claude sessions comes from this hook, so it matters more now. Run `~/code/agent-files/install.sh` to see the hook block it prints, then add that block to `~/.claude/settings.json`. It registers ten events and calls the hook by its absolute path.

Merge it; don't paste it in whole. Your `settings.json` already has a `"hooks"` object with arrays for `SessionStart`, `PreToolUse`, `PostToolUse` and `PostToolUseFailure`. For those four, add the printed `{ "hooks": [ … ] }` entry to the existing array. Add the other six events as new keys in the same `"hooks"` object; a second `"hooks"` key would silently drop one set. Check it with `python3 -m json.tool ~/.claude/settings.json > /dev/null`. S9 below is the end-to-end check.

## 2a. Rex hosts Neovim
- `rex` is linked into `~/.local/bin` from `/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex`. Rex's Claude Code hook (`rex skill setup`, already in `settings.json`) calls `rex` by name; if a Rex update moves the binary, re-link it.
- One Rex session per repo, Neovim in it, agents in Neovim. Quitting the app keeps them all; reopening attaches again.
- The policy rule (ARCHITECTURE §5.1): agents must not `rex send` their own text into a pane running `claude` or `codex`. Inside Neovim, `agent-files-term` refuses it.

## 3. Editor
Add `~/code/agent-files/nvim` to Neovim's `runtimepath` and call:
```lua
require('agents').setup({ root = '~/agent-files', tabline = true })
```
That also defines `:AgentsTerms`, `:AgentsTermSend` and `:AgentsTermCapture` (ARCHITECTURE §11.2); your own layout is in [md/operator-neovim.md](md/operator-neovim.md). The sidebar's commands and your keymaps for it come with its build (plan step 5).
Do view-layer step 0 (a generic markdown renderer, about an hour) and confirm you can read `md/docs/examples/view-fixture/thread.md` comfortably.

## 4. Start the runner
```sh
agent-files-run watch     # leave running; a second copy exits with code 2
```

## 5. Run the manual smoke tests (spec §10.2)
`sh tests/smoke.sh` already covers S1-S5 with the mock backend. By hand:

| # | Do | Pass when |
|---|---|---|
| S6 | `model: claude-opus-5-5`. Make the first message long: paste 2,000+ characters of real text (Opus 5.5 caches nothing under 512 tokens). Send, then send a short second message within 5 min | real reply; second `steps/*.response.json` has `cache_read_input_tokens > 0` |
| S7 | delete an earlier agent turn, rewrite your first turn, send | reply arrives, no 400 |
| S8 | `model: ollama/<name>`, send | reply, `cost_usd: 0` |
| S9 | start `claude` in a project in Neovim's `:terminal`, trigger a permission prompt | a directory `~/agent-files/threads/_observed/<project>-…/` appears. `:AgentsNext` lists it as blocked as soon as the permission dialog opens. Open its `thread.md`: after you answer, the end mark shows the spinner (working), then ✓ (done) when Claude finishes. The directory is gone after you exit `claude` (the sidebar build changes this to `closed`) |
| S10 | `:AgentsGrep <word>` | quickfix hits |
| S11 | copy the view fixture into the root: `cp -R ~/code/agent-files/md/docs/examples/view-fixture ~/agent-files/threads/fixture` (the plugin only attaches to files under `threads/`). Open it, and your S6 thread | headers/`END` highlighted, tool fold closed, end mark shows `~Nk`. A status glyph shows only while a turn is running or its result is unseen. Then send a turn in the S6 thread: while it runs the spinner moves and the buffer is read-only; when the reply lands the buffer reloads with no "file changed" prompt, shows ✓ and becomes writable again. Then `rm -r ~/agent-files/threads/fixture` |

Report each result to the agent; for a failure, include the exact symptom and the thread's `steps/` files.

## Things to watch
- `status` shows `?` for a turn working more than 10 minutes with no heartbeat: the runner probably died; restart `watch` and it will close the turn as interrupted.
- Refusals: the fallback to another model is not built, and `fallbacks = true` in `config.toml` does nothing yet. A refused turn ends as a failed turn with `! error: refusal (<category>)`. Rephrase and send again, or switch `model:` for that thread.
- `model: claude-cli` runs on your plan: the runner keeps `ANTHROPIC_API_KEY` away from `claude -p`. With no `/<model>` suffix it uses Claude Code's default model; write `claude-cli/claude-opus-5-5` to pin one.
- `claude-cli` turns record the API-equivalent `total_cost_usd` that `claude -p` reports, and it counts toward `daily_spend_cap_usd`. Raise the cap if that blocks you.
- Do not edit a thread's `thread.md` from another tool while a turn is running; the runner ends the turn with `END (conflict)` (output saved in `out/`).

## Questions
- None blocking.
- For the sidebar, when its steps come up: [Q1 and Q2 of the plan](md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md#questions) (selection broadcast to every session; whether `--resume` keeps the session id, which the agent checks).
- [md/plans/2026-11-03-nvim-addressing/nvim-addressing.md](md/plans/2026-11-03-nvim-addressing/nvim-addressing.md): Q4 (replace `nvim` or use another name?) is open; Q1 waits on the doorbell analysis (next-agents).
- Before M6: [md/plans/2026-11-03-dag-orchestration/dag-orchestration.md](md/plans/2026-11-03-dag-orchestration/dag-orchestration.md#questions).
