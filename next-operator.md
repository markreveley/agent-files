---
type: handoff
audience: operator
updated: 2026-11-05
---

# Next steps for the operator

Read with [next-agents.md](next-agents.md).

**What changed on 2026-11-05** ([md/plans/2026-11-05-tmux-host/tmux-host.md](md/plans/2026-11-05-tmux-host/tmux-host.md), ARCHITECTURE v0.9):
- **Ghostty, tmux and workmux are the host; Rex is not used.** Your agents run in tmux panes beside Neovim, one window per worktree. Your dotfiles now have the workmux layout (`~/.config/workmux/config.yaml`: `nvim`, then `claude --ide`), claudecode.nvim set to `provider = "none"` (Claude connects from its pane), and Option+n/h/e/u (and `tn`/`th`/`te`/`tu`) crossing from Neovim into the next tmux pane. Rex's hook is out of `settings.json`. Layout and keys: [md/docs/operator-neovim.md](md/docs/operator-neovim.md).
- **The sidebar is dropped.** workmux's window icons, sidebar and dashboard do its job.
- **There is no send policy.** Nothing refuses a send into `claude` or `codex`, and `b:agents_send` is gone.

**What changed on 2026-11-04** (thread: thread-archive `threads/agent-files/2026-11-04-nvim-sidebar.md`):
- **The trial is gone.** No hypotheses, journal, measurement or day-10 decision, and no freeze: building goes ahead. `init` no longer creates `trial/`, the hook and `agent-files-grep` no longer log there, and `agent-files-stats` now reports threads, turns, spend and live observed sessions.
- **agent-files is Neovim-first** (ARCHITECTURE v0.8): threads are read and written in Neovim. Its hosting half was replaced on 2026-11-05 (above).

M1 is built and tested against the mock backend. Nothing has yet run through the runner against a real model, in your editor, or with a live `claude` session; steps 1-5 below do that.

**Also 2026-11-04:** the repo now follows repo-template's layout (PR #35). ARCHITECTURE is at `md/governance/ARCHITECTURE.md`, and other docs moved; old paths in open Neovim buffers point at files that are gone.

Already done on this Mac: the install clone at `~/code/agent-files` (at `1a85870`, behind `main`: PR #41 changed `agents.term` and `agent-files-term`, so pull it before step 3; see README), `./install.sh` (links in `~/.local/bin`, on `PATH`), `uv`, `git`, Python 3.14, Neovim 0.12.5, tmux 3.7b, workmux 0.1.278, ripgrep 15.2.0, and `agent-files-run init`. The data root is at `~/dev/repos/agent-files-data`, with `~/agent-files` linking to it. It has a private remote (`markreveley/agent-files-data`, added 2026-11-04); nothing pushes it automatically, so `git -C ~/agent-files push` when you want a backup.

## 0. Tidy up after the change
- Delete the neovim-agent-sidebar repo: its GitHub repo (`markreveley/neovim-agent-sidebar`) and the local checkout `~/dev/repos/neovim-agent-sidebar`. GitHub has no commits; the local checkout has one (the layout and the superseded v1 plan) and uncommitted edits, none of which is needed: the plan lives on here (as a dropped plan).
- Rex, if you want it gone: the app (`/Applications/Rex Beta.app`), the link `~/.local/bin/rex` and its skill `~/.claude/skills/rex` (not in your dotfiles). Its hook is already out of `settings.json`.
- workmux's skills: `workmux setup` put five in `~/.claude/skills` (`workmux`, `coordinator`, `merge`, `open-pr`, `rebase`), not in your dotfiles. `coordinator` has one agent start other agents and message them, which is the agent-to-agent orchestration agent-files leaves out; remove it if you don't want agents offered that.

## 1. Configure
- Prices are done (2026-11-02): `~/agent-files/config.toml` has blocks for `claude-opus-5-5`, `claude-fable-5-1`, `claude-sonnet-5-5` and `claude-haiku-5-5`. Any other paid model needs its own block, keyed by the exact `model:` name in quotes; without one it counts as $0 and the spend cap doesn't protect it. Local `ollama/...` and `lmstudio/...` models need none.
- Check `daily_spend_cap_usd` (default $5.00 a day, all threads together).
- Export `ANTHROPIC_API_KEY` in the shell that runs the runner.
- For local models, make sure Ollama or LM Studio is running at the `base_url` in the config.

## 2. Hook up Claude Code
The observed threads (`:AgentsNext`, the tabline, `agent-files-stats`) come from this hook; workmux's hooks are separate and already in. Run `~/code/agent-files/install.sh` to see the hook block it prints, then add that block to `~/.claude/settings.json`. It registers ten events and calls the hook by its absolute path.

Merge it; don't paste it in whole. Your `settings.json` already has a `"hooks"` object with arrays for `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `Notification` and `Stop` (workmux added three of them). For those seven, add the printed `{ "hooks": [ … ] }` entry to the existing array. Add the other three (`PermissionRequest`, `StopFailure`, `SessionEnd`) as new keys in the same `"hooks"` object; a second `"hooks"` key would silently drop one set. Check it with `python3 -m json.tool ~/.claude/settings.json > /dev/null`. S9 below is the end-to-end check.

## 2a. Check the tmux and workmux layout
This is [tmux-host](md/plans/2026-11-05-tmux-host/tmux-host.md) step 2. In a repo, run `workmux add <branch>`. In the new window:
- In the `claude` pane, `/ide` shows Neovim connected.
- Select lines in Neovim and press `<leader>cs`: Claude has them.
- Ask Claude for an edit: the diff opens in Neovim; `<leader>cy` accepts it, `<leader>cn` rejects it.
- Option+n and Option+h move between the Neovim and `claude` panes.

Tell the agent what failed. Restart Neovim first, so it loads the new `init.lua`.

## 3. Editor
First update the install clone: `git -C ~/code/agent-files pull --ff-only` (no `./install.sh` needed: no new executable). Then add `~/code/agent-files/nvim` to Neovim's `runtimepath` and call:
```lua
require('agents').setup({ root = '~/agent-files', tabline = true })
```
That also defines `:AgentsTerms`, `:AgentsTermSend` and `:AgentsTermCapture` (ARCHITECTURE §11.2); your own layout is in [md/docs/operator-neovim.md](md/docs/operator-neovim.md).
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
| S9 | start `claude` in a tmux pane in a project, trigger a permission prompt | a directory `~/agent-files/threads/_observed/<project>-…/` appears. `:AgentsNext` lists it as blocked as soon as the permission dialog opens. Open its `thread.md`: after you answer, the end mark shows the spinner (working), then ✓ (done) when Claude finishes. The directory is gone after you exit `claude` |
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
- [tmux-host](md/plans/2026-11-05-tmux-host/tmux-host.md#questions), its step 3, after you've checked the layout (2a):
  - **Q1.** `agents.term`: keep it for terminals inside Neovim only, give it a tmux backend, or retire it for `workmux capture`/`send`? The agent recommends keeping it as it is.
  - **Q2.** Should `agent-files-hook` keep writing session status beside workmux's, or keep only the record of each session? The agent recommends the record only: two status sources can disagree.
  - **Q3.** Should morla's command lane list workmux's worktrees, so it can write `workmux send` commands? Needed when the morla plan's step 3 comes up.
- [md/plans/2026-11-03-nvim-addressing/nvim-addressing.md](md/plans/2026-11-03-nvim-addressing/nvim-addressing.md): Q4 (replace `nvim` or use another name?) is open; Q1 is answered (no doorbell, no registry). The plan is being revisited so an agent in a tmux pane can find its Neovim (next-agents step 5).
- Design and build questions not owned by one plan (ARCHITECTURE §13 and build spec §14, both now pointers): [md/plans/2026-11-04-open-questions/open-questions.md](md/plans/2026-11-04-open-questions/open-questions.md). None blocks the next step.
- Before M6: [md/plans/2026-11-03-dag-orchestration/dag-orchestration.md](md/plans/2026-11-03-dag-orchestration/dag-orchestration.md#questions).
- Accept, change or drop the provenance plan? [md/plans/2026-11-05-provenance/provenance.md](md/plans/2026-11-05-provenance/provenance.md) makes direct-turn records checkable (provider ids, hashed step records, your name on `send` commits, a `verify` command). Its Q1-Q4 come to you when its steps do.
