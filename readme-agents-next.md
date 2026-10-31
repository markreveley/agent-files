# Next steps for agents (AI coding sessions)

You are continuing the M1 build of agent-files. Read [docs/m1-build-spec.md](docs/m1-build-spec.md) first; where it is silent, [docs/m1-plan.md](docs/m1-plan.md) and [ARCHITECTURE.md](ARCHITECTURE.md) apply. The operator's checklist is in [readme-operator-next.md](readme-operator-next.md).

## Rules and checks
Standing rules and the pre-push test commands are in [AGENTS.md](AGENTS.md).

## Open items, in priority order
1. **Anthropic refusal fallback** (`lib/agent_files/backends/anthropic.py`). `fallbacks = true` currently only records a caveat in `steps/*.response.json`. Look up the server-side fallback option and beta flag in the current API docs, wire it in, and add the `! served by <model>` diagnostic path (runner already emits it when `served_model` differs). Needs a mock of the SDK stream for a unit test.
2. **Verify the hook against current Claude Code docs** (`bin/agent-files-hook`): event names, settings shape, `Notification` fields (`notification_type`), and whether a failure event exists beyond `StopFailure`. Today `blocked` also triggers when `notification_type` is absent and the message contains "permission"; remove that guess once confirmed. Update `install.sh` and `tests/test_hook.py`.
3. **Verify `claude -p` flags** (`backends/claude_cli.py`, spec §5.4.2): `--tools ""`, `--setting-sources ""`, `--system-prompt`, `--include-partial-messages` were checked against `--help` only. Run one real turn, confirm no tools or settings leak in, and record any gap in `backend_caveats`. This needs a logged-in `claude`; if you lack one, leave it for the operator.
4. **Neovim 0.10+**: tests ran on 0.9.5. Re-run on 0.10 and confirm `FileChangedShell` reload into a briefly non-modifiable buffer and the spinner timer behave. The plugin uses `vim.uv or vim.loop`.
5. **Add a test for the Anthropic and OpenAI-compatible backends** using fake clients, covering: `max_tokens` stop adds `! stopped: max_tokens`, refusal becomes a failed turn, 4xx fails immediately, cost computed from `[prices]`.
6. **Stats edge cases** (`bin/agent-files-stats`): `--since` filters sends only, not thread counts; deleted-fork detection uses `git log --diff-filter=A` and is lightly tested. Add cases for renamed threads and forks created and deleted in the same day.
7. **Optional, after the trial starts:** `agent-files-render` (view-layer step 2, spec §12). It must import `thread.py` and write only under `~/.cache/agent-files/view/`.

## Do not do
- No tools in the runner, no `inbox/`, notes writing, compaction, `resume` context or grounding (spec §13).
- Do not edit the operator's `config.toml` or `trial/journal.md` in the data root.
- Do not skip or weaken a test to get green.
