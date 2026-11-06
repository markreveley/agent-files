# AGENTS.md — standing instructions for AI sessions in this repo

Durable rules only. What to do next lives in [next-agents.md](next-agents.md) and [next-operator.md](next-operator.md) and gets deleted or rewritten as it is done.

## Where to read first
- Direction: [md/docs/direction-analysis.md](md/docs/direction-analysis.md) (what agent-files is for, the planning harness, what to adopt). Design: [ARCHITECTURE.md](md/governance/ARCHITECTURE.md). Current build: [md/docs/m1-build-spec.md](md/docs/m1-build-spec.md) (wins over the plan for M1), then [md/plans/2026-10-31-m1/m1.md](md/plans/2026-10-31-m1/m1.md), [md/docs/view-layer.md](md/docs/view-layer.md), [md/docs/role-of-neovim.md](md/docs/role-of-neovim.md).
- Do not build anything the spec lists under "Not in this build" (§13).
- **Adopt before building.** Before building any milestone, grade existing tools against it the way [md/docs/host-analysis.md](md/docs/host-analysis.md) graded M2, and drop what they already do. agent-files is Neovim-first for threads (ARCHITECTURE v0.8), and host-neutral (v0.10): harness sessions run in their own panes beside Neovim, grouped per worktree, and what a host must do is in ARCHITECTURE §12. The host is Superlogical Rex. Don't design for other editors or hosts until the operator asks.

## Layout
- `bin/` entry points; `lib/agent_files/` shared Python; `nvim/` the `agents.nvim` plugin; `tests/`; `md/docs/examples/view-fixture/` shared parser/plugin fixture.
- The layout follows [repo-template](https://github.com/markreveley/repo-template); `~/dev/repos/repo-template/bin/check-layout.sh` checks it. `md/` holds the prose: `governance/` (ARCHITECTURE), `docs/` (specs, decision records), `plans/` and `analysis/` (dated folders), `issues/`, `audits/`, `tested/`. Each folder's README says what goes there and how files are named. The operator's own host, terminal and editor setup is not kept here, only what applies to agent-files: what it needs from a host, its hook, and `agents.nvim`. The handoff files `next-agents.md` and `next-operator.md` stay at the root.
- Threads are not kept here: `/end` writes them to the private thread-archive repo, under `threads/agent-files/`.
- **The data root is `$AGENT_FILES_ROOT` (default `~/agent-files/`), never this checkout.** Programs refuse to run if the root contains `bin/agent-files-run`. Tests use temp roots; never write into a real root from a session.
- **The install clone is `~/code/agent-files`**, separate from this checkout; the operator's `~/.local/bin/agent-files-*` links and Neovim's `runtimepath` point into it. It falls behind `main` after every merge. Pull it (`git -C ~/code/agent-files pull --ff-only`, then `./install.sh` there if an executable was added) only when the operator asks; check `git status` there first and never pull over local changes.

## Rules for code
- One parser: everything reading `thread.md` imports `lib/agent_files/thread.py`. `nvim/lua/agents/thread.lua` mirrors it; change both together, with tests.
- `thread.py`, the hook, stats and grep use the standard library only. `anthropic` and `openai` are imported lazily inside their backends.
- `agent-files-hook` must finish in under 100 ms, exit 0 and print nothing.
- Runner output is escaped (`\END`, `\## you`, `\! `); never write model text to `thread.md` without `escape_line`.
- Git failures never fail a turn. Commit only the thread's `thread.md`, `steps/` and `out/`, never sidecars (`status`, `seen`, `STOP`, `last_turn`).
- Do not edit the operator's `config.toml`.
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
- Parallel sessions share the main checkout. Create your branch in a `git worktree`, never by switching branches in the main checkout, which moves every session's `HEAD`. Don't `git stash` there either: it stashes other sessions' edits too.
- Say plainly what was not verified (live API, real `claude`, Neovim version) in the PR body.
- **What to build comes from `next-agents.md`**, not from reading other docs. Its steps link to the plans they come from. Plan docs live in `md/plans/YYYY-MM-DD-<slug>/<slug>.md`, and each opens with a dated status line (`> Status: proposed · YYYY-MM-DD`), updated when the plan changes. A question in a plan moves to `next-operator.md` when the step that waits on it comes up.
- Do not put model identifiers in commits, PR text or code comments.
