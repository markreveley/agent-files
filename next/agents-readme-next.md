# Next steps for agents (AI coding sessions)

You are continuing the M1 build of agent-files. Read [docs/m1-build-spec.md](../docs/m1-build-spec.md) first; where it is silent, [docs/m1-plan.md](../docs/m1-plan.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) apply. The operator's checklist is in [operator-readme-next.md](operator-readme-next.md).

Since 2026-11-01 harness sessions run in TUIOS and H4 is no longer a trial hypothesis ([docs/host-analysis.md](../docs/host-analysis.md)). Nothing in the M1 code changes because of that.

Done and recorded elsewhere: the hook (PR #10), and the `claude -p` flags, verified with one real turn on 2026-11-01 (spec §14.1; the remaining gaps are in `claude_cli.CAVEATS`). Re-run that check after a Claude Code upgrade: run the backend's exact `command()` argv once from a shell with no `CLAUDE*` env vars, and read the stream's `system`/`init` event (`tools`, `mcp_servers`, `slash_commands`, `skills` should all be empty) and the result's input tokens (hundreds, not thousands).

This checkout is shared by parallel sessions: make new branches in a `git worktree`, not by switching branches here.

## Rules and checks
Standing rules and the pre-push test commands are in [AGENTS.md](../AGENTS.md).

## Open items, in priority order
1. **Anthropic refusal fallback** (`lib/agent_files/backends/anthropic.py`). `fallbacks = true` currently only records a caveat in `steps/*.response.json`. Look up the server-side fallback option and beta flag in the current API docs, wire it in, and add the `! served by <model>` diagnostic path (runner already emits it when `served_model` differs). Test it with the fake SDK in `tests/fakes/anthropic` (add a scenario), as `tests/test_backends.py` does.
2. **Neovim 0.10+ — interactive half only.** The headless plugin tests pass on Neovim 0.12.5, the operator's version (44 checks, 2026-11-01). Still to confirm by hand, in a real editor: `FileChangedShell` reload into a briefly non-modifiable buffer, and the spinner timer. The operator can do this during smoke S11. The plugin uses `vim.uv or vim.loop`.
3. **Optional, after the trial starts:** `agent-files-render` (view-layer step 2, spec §12). It must import `thread.py` and write only under `~/.cache/agent-files/view/`.
4. **Residue list for AGENTS.md** (ARCHITECTURE §9.7). For each rule in `AGENTS.md`, name the test that enforces it (e.g. is the hook's 100 ms limit tested?), or list it under a new "Residue" heading as enforced by review only. Add no new tests in this item; record what exists.

## Do not do
- No tools in the runner, no `inbox/`, notes writing, compaction, `resume` context or grounding (spec §13).
- Do not edit the operator's `config.toml` or `trial/journal.md` in the data root.
- Do not skip or weaken a test to get green.
