---
type: handoff
audience: agent
updated: 2026-11-02
---

# Next steps for agents (AI coding sessions)

Read with [operator-readme-next.md](operator-readme-next.md). Rewrite both at the end of each thread and delete finished steps.

You are continuing the M1 build of agent-files. For what agent-files is for and where it goes after M1, read [docs/direction-analysis.md](../docs/direction-analysis.md). For M1 itself, read [docs/m1-build-spec.md](../docs/m1-build-spec.md) first; where it is silent, [docs/m1-plan.md](../docs/m1-plan.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) apply. Standing rules and the pre-push checks are in [AGENTS.md](../AGENTS.md).

## State
- M1 is built. On 2026-11-02 an adversarial audit found bugs that would have skewed H1, wedged threads, billed `claude-cli` turns to the API and duplicated plugin buffers, plus operator steps that failed verbatim. All are fixed and merged (PR #24, `b1bd8d8`); the commits name each fix. What is left is in [audit-2026-11-02.md](audit-2026-11-02.md). Fix one of those only if it causes friction in the trial, or after day 10.
- Verified:
  - Mock-backend tests and smoke S1-S5.
  - Headless plugin tests on Neovim 0.12.5 (75 checks after the audit fixes; 93 unit tests).
  - The hook, against the Claude Code hooks reference (PR #10).
  - The `claude -p` flags, with one real turn (PR #13), re-checked on Claude Code 2.1.317 on 2026-11-02 (spec §14.1; remaining gaps in `claude_cli.CAVEATS`).
- Not verified: anything through the runner against a real model (S6-S8), the hook in a live `claude` session (S9), and the interactive Neovim behaviour (S11). All three wait on the operator's configuration and smoke tests.
- Harness sessions run in TUIOS, and H4 is not a trial hypothesis ([docs/host-analysis.md](../docs/host-analysis.md)). No M1 code changes because of that. ARCHITECTURE.md was checked against that decision and the code on 2026-11-01 (PR #18); v0.6 (0046b91) changed it since, and the 2026-11-02 docs audit found nothing in it that contradicts the code.
- **Direction, decided with the operator on 2026-11-02** ([docs/direction-analysis.md](../docs/direction-analysis.md), ARCHITECTURE v0.6):
  - agent-files is the logbook for human–agent work. It is not a host: building a Charm-based host like TUIOS was reconsidered and rejected. It is not a coding harness either. Don't reopen these without new evidence.
  - After M1 it builds a **planning harness** (M6, grown from `agent-files-run`). Coding is farmed out to Claude Code and Codex: briefs go out, records come back (ARCHITECTURE §8.1).
  - The KB is built on **artifact-dag** (§7). Acceptance is a policy per node type (`manual`, `auto`, `sample`), and every node records `accepted_by`.
  - Before building any capture of coding sessions, grade **Entire** (§12.1, §13 Q16).
  - Principle 13 keeps the format, the hook, the links and the HTML viewer extractable.
  - **M1 is unchanged** (spec, H1–H3, thresholds). The record trial (attribution and the DAG) is the next trial.
- The install is finished (2026-11-02; the agent ran it at the operator's request): install clone at `f627b15`, which is behind the audit fixes (operator step 2 pulls), `agent-files-run init` run, ripgrep 15.2.0 installed, TUIOS pinned at 0.12.1. Operator steps 1-5 (configure, hook, TUIOS integration, editor, `watch`) and the smoke tests are not started: on 2026-11-02 there were no `agent-files-hook` entries in `~/.claude/settings.json` and `watch` wasn't running.
- On 2026-11-02 the operator asked the agent to fill `[prices]` in `~/agent-files/config.toml`. Blocks for Opus 5.5, Fable 5.1, Sonnet 5.5 and Haiku 5.5 were appended (5-minute cache-write rates; Haiku at its ≤100K-prompt rate) and left uncommitted. That was a one-off request: the rule against editing `config.toml` still stands.
- Known quirk, not a bug to fix before day 10: `claude-cli` turns store the CLI's `total_cost_usd` (API-equivalent even on a plan), and `spend_today` adds it to the daily cap. If the operator wants plan turns excluded, that is a post-trial change. With plain `model: claude-cli` (no `/<model>`), `claude -p` runs Claude Code's default model, which was `claude-fable-5-1` on 2026-11-02.

## Environment facts (operator's Mac)
- The repo checkout is `/Users/mark/dev/repos/agent-files`, and parallel sessions share it. Make branches in a `git worktree` (AGENTS.md, Workflow).
- GitHub deletes a PR's branch when it merges (turned on 2026-11-01), and it retargets PRs stacked on that branch to `main`. After a merge, remove only your worktree and local branch.
- `threads/` at the repo root holds session logs, one per thread, such as `2026-11-02-01.md` (the thread behind direction-analysis). They are not data-root threads, and no program reads them. `/end` writes them with `node ~/.claude/skills/end/thread-from-export.mjs --session threads/<date>-<name>.md` (since 2026-11-02 it reads the session transcript, so the operator no longer has to `/export`). The repo is public: commit only that trimmed form (user prompts and prose replies), never a raw transcript. `threads/raw/` and `threads/redact.json` are git-ignored. Auto mode blocked a push of an untrimmed transcript once.
- The operator's install clone is `~/code/agent-files`, a separate clone that the `~/.local/bin/agent-files-*` links point at. It falls behind `main` whenever a PR merges; ask the operator to pull it after a code change.
- **Testing the hook, grep or runner by hand:** always set `AGENT_FILES_ROOT` to a temp dir. Without it they write into the operator's real root (`~/agent-files`); an audit subagent did this on 2026-11-02 (cleaned up). Only `run` and `stats` refuse a code-checkout root. Say this in every brief to a subagent.
- Worktrees for this repo go under `/Users/mark/dev/repos/agent-files-worktrees/<name>`. Parallel fix agents each got their own worktree and branch; the lead then cherry-picked their commits onto one branch for a single PR.
- TUIOS 0.12.1 facts (from its `--help`): `tuios integration install claude-code` writes the hooks and keeps a symlinked `settings.json` a symlink; there is no separate approvals option (`tuios list-options agents`); its config is `~/Library/Application Support/tuios/config.toml`.
- The data root lives at `~/dev/repos/agent-files-data` (its own local git repo, no remote), and `~/agent-files` is a symlink to it (operator's choice, 2026-11-02). The Python programs use `abspath`, so they keep the link path; the plugin compares both forms (`nvim/lua/agents/init.lua:22-24`). It must stay outside this code checkout, which is public.
- Tool versions: Claude Code 2.1.317 (logged in with claude.ai, so `claude -p` works without an API key), Neovim 0.12.5, TUIOS 0.12.1, Python 3.14.
- **ripgrep is at `/opt/homebrew/bin/rg`** (installed 2026-11-02), and `tests.test_stats` passes. Inside a Claude Code shell, `type rg` still shows a shell function; check the path, not `command -v`.
- To re-check the `claude -p` flags after a Claude Code upgrade:
  1. Run the backend's exact `claude_cli.command()` argv once, from a shell with every `CLAUDE*` env var removed.
  2. In the stream's `system`/`init` event, `tools`, `mcp_servers`, `slash_commands` and `skills` should all be empty.
  3. The result's input tokens should be in the hundreds, not thousands.

## Next, in order
1. **(Blocked on operator)** Act on smoke results. When the operator reports S6-S11, fix each failure from the symptom and the thread's `steps/` files. S11 includes the interactive Neovim check: `FileChangedShell` reload into a briefly non-modifiable buffer, and the spinner timer (the plugin uses `vim.uv or vim.loop`). The audit fixes rewrote draft re-apply (`nvim/lua/agents/draft.lua`, a diff against the last-read file), the watcher (a throttle, ignoring `seen`) and window options (window-local, set on `BufWinEnter`). All of that has been tested only headless, so read S11 failures with those in mind.
2. **After the trial starts, optional:** `agent-files-render` (view-layer step 2, spec §12). It must import `thread.py` and write only under `~/.cache/agent-files/view/`. It is the first piece of the record viewer (M8, principle 13), so keep its output a static HTML page.
3. **After the trial:** Anthropic refusal fallback (`lib/agent_files/backends/anthropic.py`). The operator decided on 2026-11-01 to build this after the trial, not before S6. Reasons: refusals should be rare in the trial's threads, a refusal already shows as a failed turn, it doesn't affect H1-H3, and no new building is allowed before day 10. `fallbacks = true` only records a caveat in `steps/*.response.json` today.
   - Look up the server-side fallback option and beta flag in the current API docs, and wire them in.
   - Add the `! served by <model>` diagnostic path. The runner already emits it when `served_model` differs.
   - Test with the fake SDK in `tests/fakes/anthropic` (add a scenario), as `tests/test_backends.py` does.
4. **After the trial:** the residue list for AGENTS.md (ARCHITECTURE §9.7). For each rule in `AGENTS.md`, name the test that enforces it (e.g. is the hook's 100 ms limit tested?), or list the rule under a new "Residue" heading as enforced by review only. Add no new tests; record what exists. Include the tier-1 rule from ARCHITECTURE §5.1 that agents don't write to `threads/`. On 2026-11-01 the operator decided to record it as residue rather than add a deny-rule install step.
5. **At day 10, with the operator:**
   - Confirm or change the post-M1 order in ARCHITECTURE §14 (the record trial → M6 → M8 → …).
   - If the record trial is next, write its hypotheses and thresholds before building anything, as m1-plan §5 did for M1.
   - Grade Entire, and SpecStory with it, against §13 Q16 before building capture.
   - Use the journal's notes on `claude-cli` threads and the `cache_read_input_tokens` in their `steps/*.response.json` for §13 Q17.
6. **After the trial, optional:** T3 Code as a host (ARCHITECTURE §13 Q15, [docs/multi-subscription-analysis.md](../docs/multi-subscription-analysis.md)). First ask the operator to run S9 with T3 Code as the host. Only if it passes, grade T3 Code against host-analysis §1. Don't use CLIProxyAPI for Claude. If hosts are re-graded, add Superlogical Rex (host-analysis §2).

Build nothing new before the day-10 decision ([m1-plan §5](../docs/m1-plan.md#5-decision-criteria)) beyond the fixes in item 1.

## Pending operator decisions
- None.

## Do not do
- No tools in the runner, no `inbox/`, notes writing, compaction, `resume` context or grounding (spec §13).
- Do not edit the operator's `config.toml` or `trial/journal.md` in the data root.
- Do not skip or weaken a test to get green.
