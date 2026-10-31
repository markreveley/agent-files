# AGENTS.md — standing instructions for AI sessions in this repo

Durable rules only. What to do next lives in [readme-agents-next.md](readme-agents-next.md) and [readme-operator-next.md](readme-operator-next.md) and gets deleted or rewritten as it is done.

## Where to read first
- Design: [ARCHITECTURE.md](ARCHITECTURE.md). Current build: [docs/m1-build-spec.md](docs/m1-build-spec.md) (wins over the plan for M1), then [docs/m1-plan.md](docs/m1-plan.md), [docs/view-layer.md](docs/view-layer.md), [docs/role-of-neovim.md](docs/role-of-neovim.md).
- Do not build anything the spec lists under "Not in this build" (§13).

## Layout
- `bin/` entry points; `lib/agent_files/` shared Python; `nvim/` the `agents.nvim` plugin; `tests/`; `docs/examples/view-fixture/` shared parser/plugin fixture.
- **The data root is `$AGENT_FILES_ROOT` (default `~/agent-files/`), never this checkout.** Programs refuse to run if the root contains `bin/agent-files-run`. Tests use temp roots; never write into a real root from a session.

## Rules for code
- One parser: everything reading `thread.md` imports `lib/agent_files/thread.py`. `nvim/lua/agents/thread.lua` mirrors it; change both together, with tests.
- `thread.py`, the hook, stats and grep use the standard library only. `anthropic` and `openai` are imported lazily inside their backends.
- `agent-files-hook` must finish in under 100 ms, exit 0 and print nothing.
- Runner output is escaped (`\END`, `\## you`, `\! `); never write model text to `thread.md` without `escape_line`.
- Git failures never fail a turn. Commit only the thread's `thread.md`, `steps/` and `out/`, never sidecars (`status`, `seen`, `STOP`, `last_turn`).
- Do not edit the operator's `config.toml` or `trial/journal.md`.
- Never skip, disable or weaken a test to get green.

## Checks before every push
```sh
python3 -W ignore -m unittest discover -s tests -t .
nvim --headless -u NONE -l tests/nvim/test_agents.lua    # from the repo root
sh tests/smoke.sh                                        # S1-S5, mock backend
```
Smoke S6-S11 need a real model, editor or `claude` session and are the operator's.

## Workflow
- Work on a feature branch, push, open a draft PR against `main`.
- Say plainly what was not verified (live API, real `claude`, Neovim version) in the PR body.
- Do not put model identifiers in commits, PR text or code comments.
