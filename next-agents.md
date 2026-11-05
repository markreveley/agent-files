---
type: handoff
audience: agent
updated: 2026-11-04
---

# Next steps for agents (AI coding sessions)

Read with [next-operator.md](next-operator.md). Rewrite both at the end of each thread and delete finished steps.

You are continuing the M1 build of agent-files. For what agent-files is for and where it goes after M1, read [md/docs/direction-analysis.md](md/docs/direction-analysis.md). For M1 itself, read [md/docs/m1-build-spec.md](md/docs/m1-build-spec.md) first; where it is silent, [md/plans/2026-10-31-m1/m1.md](md/plans/2026-10-31-m1/m1.md) and [ARCHITECTURE.md](md/governance/ARCHITECTURE.md) apply. Standing rules and the pre-push checks are in [AGENTS.md](AGENTS.md).

## State
- Git: `main` at `47930bf` has PR #35, which laid the repo out per [repo-template](https://github.com/markreveley/repo-template) (`868468a`): ARCHITECTURE in `md/governance/`, plans and analyses in dated folders, a README with the pinned template text in every `md/` folder, the open questions gathered into [md/plans/2026-11-04-open-questions/open-questions.md](md/plans/2026-11-04-open-questions/open-questions.md), threads moved to thread-archive. `check-layout.sh` reports `layout ok`, and `template-sync` reports every pin in sync. No other branches or worktrees exist.
- **Layout rules (2026-11-04):** follow each `md/` folder's README for names and form (AGENTS.md, Layout). ARCHITECTURE §13, build spec §14 and juggler §7 keep closed questions and numbered pointers; a new open question goes in the open-questions plan (`A`/`S`/`J` + its source number), not in those sections. After a template change, run the `template-sync` skill.
- **2026-11-04, operator's decisions** (thread: thread-archive `threads/agent-files/2026-11-04-nvim-sidebar.md`):
  - **The trial is cancelled, and every trace of it removed.** No hypotheses, journal, measurement or day-10 gate; building is not frozen. `init` no longer creates `trial/`; the hook and grep no longer log; `agent-files-stats` reports threads, turns, spend (by day and thread) and live observed sessions. The session logs were left as written. Don't reintroduce a trial or measurement gate unless the operator asks.
  - **Neovim-first** (ARCHITECTURE v0.8). agent-files is built around Neovim; `agents.nvim` hosts harness sessions in terminal buffers (§11.3), and Rex hosts Neovim. Don't design for other editors or hosts until the operator asks. The separate neovim-agent-sidebar repo was folded in here as [md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md](md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md); the operator deletes that repo.
- M1 is built. On 2026-11-02 an adversarial audit found bugs that would have skewed measurements, wedged threads, billed `claude-cli` turns to the API and duplicated plugin buffers, plus operator steps that failed verbatim. All are fixed and merged (PR #24, `b1bd8d8`); the commits name each fix. What is left is in [md/issues/2026-11-02-audit-leftovers.md](md/issues/2026-11-02-audit-leftovers.md). Fix one of those when it causes friction.
- Verified:
  - Mock-backend tests and smoke S1-S5.
  - Headless plugin tests on Neovim 0.12.5 (75 checks after the audit fixes; 93 unit tests).
  - The hook, against the Claude Code hooks reference (PR #10).
  - The `claude -p` flags, with one real turn (PR #13), re-checked on Claude Code 2.1.317 on 2026-11-02 (spec §14.1; remaining gaps in `claude_cli.CAVEATS`).
- Not verified: anything through the runner against a real model (S6-S8), the hook in a live `claude` session (S9), and the interactive Neovim behaviour (S11). All three wait on the operator's configuration and smoke tests.
- **Hosting:** Rex hosts Neovim (since 2026-11-03, [md/docs/rex-host.md](md/docs/rex-host.md)); Neovim hosts the harness sessions (v0.8). TUIOS is installed but no longer a fallback.
- **`agents.term` and `agent-files-term` (2026-11-03, at the operator's request):** read and type into Neovim terminal buffers over Neovim's socket (ARCHITECTURE §11.2). §5.1's policy rule is per harness (operator's decision): `claude` and `codex` take only human-written text, so agent sends to them are refused; API-keyed harnesses and shells take any text (`vim.b.agents_send = "any"`). Tested headless (plugin checks, `tests/test_term.py` through a real socket); not tried with a live `claude` in a terminal.
- **Direction, decided with the operator on 2026-11-02** ([md/docs/direction-analysis.md](md/docs/direction-analysis.md), ARCHITECTURE v0.6):
  - agent-files is the logbook for human–agent work. A standalone Charm-based host like TUIOS was reconsidered and rejected (hosting is now `agents.nvim`'s, inside Neovim). It is not a coding harness either. Don't reopen these without new evidence.
  - After M1 it builds a **planning harness** (M6, grown from `agent-files-run`). Coding is farmed out to Claude Code and Codex: briefs go out, records come back (ARCHITECTURE §8.1).
  - The KB is built on **artifact-dag** (§7). Acceptance is a policy per node type (`manual`, `auto`, `sample`), and every node records `accepted_by`.
  - Before building any capture of coding sessions, grade **Entire** (§12.1, §13 Q16).
  - Principle 13 keeps the format, the hook, the links and the HTML viewer extractable.
  - After the sidebar, the record work (attribution and the DAG) comes next (ARCHITECTURE §14).
- **DAG-grounded orchestration analysed (2026-11-03):** [md/analysis/2026-11-03-orchestrator/orchestrator.md](md/analysis/2026-11-03-orchestrator/orchestrator.md). An orchestrator picks DAG nodes for a question and briefs an agent; answers label every claim (`grounded`, `sourced`, `derived`, `contradicted`, `unsupported`). It maps onto M6 and the brief (§8.1). Operator's answers: knowledge graphs first, code graphs possibly too; "resource DAGs" means other projects' DAGs and DAGs built from outside material. The order of work and its open questions are in [md/plans/2026-11-03-dag-orchestration/dag-orchestration.md](md/plans/2026-11-03-dag-orchestration/dag-orchestration.md).
- The install: `agent-files-run init` run and ripgrep installed (2026-11-02). The install clone is at `1a85870`, behind `main` by docs-only changes (nothing in `bin/`, `lib/`, `nvim/` or `tests/` changed since); pull it when the operator asks. Operator steps 1-5 (configure, the hook block, Rex, editor, `watch`) and the smoke tests are not started: on 2026-11-04 `~/.claude/settings.json` had no `agent-files-hook` entries, `watch` wasn't running and the dotfiles' `init.lua` doesn't load the plugin.
- On 2026-11-02 the operator asked the agent to fill `[prices]` in `~/agent-files/config.toml`. Blocks for Opus 5.5, Fable 5.1, Sonnet 5.5 and Haiku 5.5 were appended (5-minute cache-write rates; Haiku at its ≤100K-prompt rate) and left uncommitted. That was a one-off request: the rule against editing `config.toml` still stands.
- Known quirk: `claude-cli` turns store the CLI's `total_cost_usd` (API-equivalent even on a plan), and `spend_today` adds it to the daily cap. If the operator wants plan turns excluded, change it then. With plain `model: claude-cli` (no `/<model>`), `claude -p` runs Claude Code's default model.

## Environment facts (operator's Mac)
- The repo checkout is `/Users/mark/dev/repos/agent-files`, and parallel sessions share it. Make branches in a `git worktree` (AGENTS.md, Workflow).
- GitHub deletes a PR's branch when it merges (turned on 2026-11-01), and it retargets PRs stacked on that branch to `main`. After a merge, remove only your worktree and local branch.
- **The repo is public, and both project DAG repos that the orchestrator analysis counts (§5) are private** (checked with `gh repo view`, 2026-11-03). identikey-dev was already named here. The second is called "a second project DAG" (operator's choice, 2026-11-03), and PR #26's commits still contain its name. Don't name other private repos here.
- **Threads live in the private [thread-archive](https://github.com/markreveley/thread-archive) repo**, under `threads/agent-files/`, unredacted (repo-template guideline 10). `/end` writes them there. The six session logs that were in `md/threads/` moved there on 2026-11-04, as the redacted copies this repo had. This repo keeps what a thread learned in its handoff files and documents, never the exchange itself.
- The install clone and when to pull it: AGENTS.md ("Layout"). Last pulled 2026-11-04, to `1a85870`.
- **Testing the hook, grep or runner by hand:** always set `AGENT_FILES_ROOT` to a temp dir. Without it they write into the operator's real root (`~/agent-files`); an audit subagent did this on 2026-11-02 (cleaned up). Only `run` and `stats` refuse a code-checkout root. Say this in every brief to a subagent.
- Worktrees for this repo go under `/Users/mark/dev/repos/agent-files-worktrees/<name>`. Parallel fix agents each got their own worktree and branch; the lead then cherry-picked their commits onto one branch for a single PR.
- **Rex facts (2026-11-03):** the CLI is inside the app, `/Applications/Rex Beta.app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex`, linked as `~/.local/bin/rex`. `rex skill setup` was already run: a skill at `~/.claude/skills/rex` and a `SessionStart` hook in `~/.claude/settings.json` that calls `rex` by name. The sidebar's "laptop" and "rolling-pine" are Rex *sessions* on this Mac's server, not hosts; `rex hosts` lists none. A harness inside Neovim inherits Neovim's `REX_BLOCK`, so `rex send` to it types into Neovim; use `agent-files-term` there.
- TUIOS 0.12.1 is installed but unused. From its `--help`: `tuios integration install claude-code` writes the hooks and keeps a symlinked `settings.json` a symlink.
- The data root lives at `~/dev/repos/agent-files-data` (its own git repo; private remote `markreveley/agent-files-data`, added and pushed 2026-11-04, after the operator removed `trial/` and committed the prices in `config.toml`; nothing in agent-files pushes it), and `~/agent-files` is a symlink to it (operator's choice, 2026-11-02). The Python programs use `abspath`, so they keep the link path; the plugin compares both forms (`nvim/lua/agents/init.lua:22-24`). It must stay outside this code checkout, which is public.
- Tool versions: Claude Code 2.1.317 (logged in with claude.ai, so `claude -p` works without an API key), Neovim 0.12.5, Rex Beta 0.1.0 (CLI 0.0.1793645657), TUIOS 0.12.1, Python 3.14.
- **ripgrep is at `/opt/homebrew/bin/rg`** (installed 2026-11-02), and `tests.test_stats` passes. Inside a Claude Code shell, `type rg` still shows a shell function; check the path, not `command -v`.
- To re-check the `claude -p` flags after a Claude Code upgrade:
  1. Run the backend's exact `claude_cli.command()` argv once, from a shell with every `CLAUDE*` env var removed.
  2. In the stream's `system`/`init` event, `tools`, `mcp_servers`, `slash_commands` and `skills` should all be empty.
  3. The result's input tokens should be in the hundreds, not thousands.

## Next, in order
1. **Build the sidebar**: [md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md](md/plans/2026-11-04-nvim-sidebar/nvim-sidebar.md), its steps 1-5 in order, one PR per step or two. Tests go in `tests/nvim/test_agents.lua` (a fake harness command) and `tests/test_hook.py`. Step 3 checks the plan's Q2 (does `claude --resume <id>` keep the session id?) with a real `claude`; ask the operator before running one. Q1 goes to the operator at step 4. Update ARCHITECTURE §5.1 (the `SessionEnd` line) and §11.3 as the hook and sidebar land.
2. **(Blocked on operator)** Act on smoke results. When the operator reports S6-S11, fix each failure from the symptom and the thread's `steps/` files. S11 includes the interactive Neovim check: `FileChangedShell` reload into a briefly non-modifiable buffer, and the spinner timer (the plugin uses `vim.uv or vim.loop`). The audit fixes rewrote draft re-apply (`nvim/lua/agents/draft.lua`), the watcher (a throttle, ignoring `seen`) and window options (window-local, set on `BufWinEnter`), all tested only headless.
3. **Analysis: revisit the doorbell and editor registry** (operator's request, 2026-11-03). They were dropped on 2026-11-01 because the TUIOS Inbox covered attention for harness sessions. TUIOS is not the host any more, and with the sidebar, attention for harness sessions lives inside Neovim. Write a dated analysis, `md/analysis/YYYY-MM-DD-<slug>/<slug>.md` in the folder README's form, deciding whether to reinstate them in whole, in part or not at all.
   - Resources: [md/docs/role-of-neovim.md](md/docs/role-of-neovim.md) §2–§10; ARCHITECTURE §11.1 and the "Dropped" line under §10.1; [md/docs/host-analysis.md](md/docs/host-analysis.md) and [md/docs/rex-host.md](md/docs/rex-host.md); the commits that added it (`dddd259`, `489a3ed`) and dropped it (`e194b0a`, PR #8, `9807116`); [md/plans/2026-11-03-nvim-addressing/nvim-addressing.md](md/plans/2026-11-03-nvim-addressing/nvim-addressing.md), which finds Neovims by socket for a different job.
   - Do the doorbell and nvim-addressing merge into one registry, or stay separate? Its Q1 is answered by this analysis.
   - What does the sidebar already cover (focus, jump to a blocked session), and what would the doorbell add (alerts when no editor is looking)?
   - The result goes to the operator as a recommendation.
4. `agent-files-render` (view-layer step 2, spec §12). It must import `thread.py` and write only under `~/.cache/agent-files/view/`. It is the first piece of the record viewer (M8, principle 13), so keep its output a static HTML page.
5. Anthropic refusal fallback (`lib/agent_files/backends/anthropic.py`). `fallbacks = true` only records a caveat in `steps/*.response.json` today.
   - Look up the server-side fallback option and beta flag in the current API docs, and wire them in.
   - Add the `! served by <model>` diagnostic path. The runner already emits it when `served_model` differs.
   - Test with the fake SDK in `tests/fakes/anthropic` (add a scenario), as `tests/test_backends.py` does.
6. The residue list for AGENTS.md (ARCHITECTURE §9.7). For each rule in `AGENTS.md`, name the test that enforces it (e.g. is the hook's 100 ms limit tested?), or list the rule under a new "Residue" heading as enforced by review only. Add no new tests; record what exists. Include the tier-1 rule from ARCHITECTURE §5.1 that agents don't write to `threads/`.
7. With the operator, before the record work: confirm the order in ARCHITECTURE §14, and grade Entire (with SpecStory) against §13 Q16 before building capture.

## Pending operator decisions
- None blocking. Questions to answer eventually are in [md/plans/2026-11-04-open-questions/open-questions.md](md/plans/2026-11-04-open-questions/open-questions.md) and, before M6, [md/plans/2026-11-03-dag-orchestration/dag-orchestration.md](md/plans/2026-11-03-dag-orchestration/dag-orchestration.md#questions); each moves to `next-operator.md` when its step comes up.

## Do not do
- No tools in the runner, no `inbox/`, notes writing, compaction, `resume` context or grounding (spec §13).
- Do not edit the operator's `config.toml` in the data root.
- Do not skip or weaken a test to get green.
