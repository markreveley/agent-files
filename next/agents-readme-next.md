# Next steps for agents (AI coding sessions)

You are continuing the M1 build of agent-files. Read [docs/m1-build-spec.md](../docs/m1-build-spec.md) first; where it is silent, [docs/m1-plan.md](../docs/m1-plan.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) apply. The operator's checklist is in [operator-readme-next.md](operator-readme-next.md).

Since 2026-11-01 harness sessions run in TUIOS and H4 is no longer a trial hypothesis ([docs/host-analysis.md](../docs/host-analysis.md)). Nothing in the M1 code changes because of that.

## Rules and checks
Standing rules and the pre-push test commands are in [AGENTS.md](../AGENTS.md).

## Open items, in priority order
1. **Anthropic refusal fallback** (`lib/agent_files/backends/anthropic.py`). `fallbacks = true` currently only records a caveat in `steps/*.response.json`. Look up the server-side fallback option and beta flag in the current API docs, wire it in, and add the `! served by <model>` diagnostic path (runner already emits it when `served_model` differs). Test it with the fake SDK in `tests/fakes/anthropic` (add a scenario), as `tests/test_backends.py` does.
2. **Verify `claude -p` flags** (`backends/claude_cli.py`, spec §5.4.2): `--tools ""`, `--setting-sources ""`, `--system-prompt`, `--include-partial-messages` were checked against `--help` only. Run one real turn, confirm no tools or settings leak in, and record any gap in `backend_caveats`. This needs a logged-in `claude`; if you lack one, leave it for the operator.
3. **Neovim 0.10+**: tests ran on 0.9.5. Re-run on 0.10 and confirm `FileChangedShell` reload into a briefly non-modifiable buffer and the spinner timer behave. The plugin uses `vim.uv or vim.loop`.
4. **Optional, after the trial starts:** `agent-files-render` (view-layer step 2, spec §12). It must import `thread.py` and write only under `~/.cache/agent-files/view/`.
5. **Residue list for AGENTS.md** (ARCHITECTURE §9.7). For each rule in `AGENTS.md`, name the test that enforces it (e.g. is the hook's 100 ms limit tested?), or list it under a new "Residue" heading as enforced by review only. Add no new tests in this item; record what exists.

## Do not do
- No tools in the runner, no `inbox/`, notes writing, compaction, `resume` context or grounding (spec §13).
- Do not edit the operator's `config.toml` or `trial/journal.md` in the data root.
- Do not skip or weaken a test to get green.
