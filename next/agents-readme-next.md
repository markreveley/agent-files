---
type: handoff
audience: agent
updated: 2026-11-02
---

# Next steps for agents (AI coding sessions)

Read with [operator-readme-next.md](operator-readme-next.md). Rewrite both at the end of each thread and delete finished steps.

You are continuing the M1 build of agent-files. For what agent-files is for and where it goes after M1, read [docs/direction-analysis.md](../docs/direction-analysis.md). For M1 itself, read [docs/m1-build-spec.md](../docs/m1-build-spec.md) first; where it is silent, [docs/m1-plan.md](../docs/m1-plan.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) apply. Standing rules and the pre-push checks are in [AGENTS.md](../AGENTS.md).

## State
- M1 is built. `main` is pushed and clean, and no PRs are open.
- Verified:
  - Mock-backend tests and smoke S1-S5.
  - Headless plugin tests on Neovim 0.12.5 (44 checks).
  - The hook, against the Claude Code hooks reference (PR #10).
  - The `claude -p` flags, with one real turn (PR #13; results in spec §14.1, remaining gaps in `claude_cli.CAVEATS`).
- Not verified: anything through the runner against a real model (S6-S8), the hook in a live `claude` session (S9), and the interactive Neovim behaviour (S11). All three wait on the operator's install and smoke tests.
- Harness sessions run in TUIOS, and H4 is not a trial hypothesis ([docs/host-analysis.md](../docs/host-analysis.md)). No M1 code changes because of that. ARCHITECTURE.md was checked against that decision and the code on 2026-11-01, and its stale lines were fixed (PR #18), so don't re-audit it.
- **Direction, decided with the operator on 2026-11-02** ([docs/direction-analysis.md](../docs/direction-analysis.md), ARCHITECTURE v0.6):
  - agent-files is the logbook for human–agent work. It is not a host: building a Charm-based host like TUIOS was reconsidered and rejected. It is not a coding harness either. Don't reopen these without new evidence.
  - After M1 it builds a **planning harness** (M6, grown from `agent-files-run`). Coding is farmed out to Claude Code and Codex: briefs go out, records come back (ARCHITECTURE §8.1).
  - The KB is built on **artifact-dag** (§7). Acceptance is a policy per node type (`manual`, `auto`, `sample`), and every node records `accepted_by`.
  - Before building any capture of coding sessions, grade **Entire** (§12.1, §13 Q16).
  - Principle 13 keeps the format, the hook, the links and the HTML viewer extractable.
  - **M1 is unchanged** (spec, H1–H3, thresholds). The record trial (attribution and the DAG) is the next trial.
- Operator steps 1-6 were checked on 2026-11-02 and none had been started: the install clone was at `7f6e6ee`, there was no `~/agent-files`, no standalone `rg`, TUIOS wasn't pinned, there were no hook entries in `~/.claude/settings.json`, and `watch` wasn't running.

## Environment facts (operator's Mac)
- The repo checkout is `/Users/mark/dev/repos/agent-files`, and parallel sessions share it. Make branches in a `git worktree` (AGENTS.md, Workflow).
- GitHub deletes a PR's branch when it merges (turned on 2026-11-01), and it retargets PRs stacked on that branch to `main`. After a merge, remove only your worktree and local branch.
- The operator's install clone is `~/code/agent-files`, a separate clone that the `~/.local/bin/agent-files-*` links point at. It is at `7f6e6ee`, behind `main`, until the operator pulls it.
- Tool versions: Claude Code 2.1.316 (logged in with claude.ai, so `claude -p` works without an API key), Neovim 0.12.5, TUIOS 0.12.1, Python 3.14.
- **No standalone `rg`.** In a Claude Code shell, `rg` is a function that subprocesses can't see, so `tests.test_stats.Stats.test_numbers` fails with exit 127. It is a known failure until the operator runs `brew install ripgrep`, not a regression. Don't touch the test.
- To re-check the `claude -p` flags after a Claude Code upgrade:
  1. Run the backend's exact `claude_cli.command()` argv once, from a shell with every `CLAUDE*` env var removed.
  2. In the stream's `system`/`init` event, `tools`, `mcp_servers`, `slash_commands` and `skills` should all be empty.
  3. The result's input tokens should be in the hundreds, not thousands.

## Next, in order
1. **(Blocked on operator)** Act on smoke results. When the operator reports S6-S11, fix each failure from the symptom and the thread's `steps/` files. S11 includes the interactive Neovim check: `FileChangedShell` reload into a briefly non-modifiable buffer, and the spinner timer (the plugin uses `vim.uv or vim.loop`).
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
