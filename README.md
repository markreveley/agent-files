# agent-files

The logbook for human–agent work: every exchange a file you can edit as context, every settled conclusion a node that records who or what accepted it, every change linked to the turns and decisions behind it — beside any harness, under any host.

Direction: [md/docs/direction-analysis.md](md/docs/direction-analysis.md). Design: [ARCHITECTURE.md](ARCHITECTURE.md). This build (M1, threads as plain-text files): [md/docs/m1-build-spec.md](md/docs/m1-build-spec.md).

| Piece | What |
|---|---|
| `bin/agent-files-run` | replay runtime: `init`, `watch`, `once <thread>`, `check <thread>` |
| `bin/agent-files-hook` | Claude Code hook → observed status for hand-started sessions |
| `bin/agent-files-stats` | trial measurement (H1–H3; observed sessions as information) |
| `bin/agent-files-grep` | logged `rg` over all threads |
| `bin/agent-files-term` | list, read and type into Neovim's terminal buffers; agents can't type into `claude` / `codex` (ARCHITECTURE §11.2) |
| `nvim/` | `agents.nvim`: marks, read-only while working, `:AgentsNew/Send/Stop/Fork/Next/Blocked/Grep`; `:AgentsTerms`, `:AgentsTermSend`, `:AgentsTermCapture` |

**The data root is `~/agent-files/` (or `$AGENT_FILES_ROOT`) — do not clone this repo there.**

Claude Code and Codex sessions run in [Superlogical Rex](https://superlogical.com), which hosts them (often inside Neovim's `:terminal`, with Neovim in a Rex pane); agent-files observes them through hooks ([md/docs/rex-host.md](md/docs/rex-host.md)). TUIOS is the fallback host.

```sh
./install.sh                 # symlinks bin/*, prints the hook block for ~/.claude/settings.json
agent-files-run init
agent-files-run watch        # leave running
```
Neovim (0.9+; spec says 0.10+): add `nvim/` to `runtimepath`, then `require('agents').setup({ root = '~/agent-files', tabline = true })`.

## Tests
```sh
python3 -W ignore -m unittest discover -s tests -t .      # parser, assembly, runner, hook, stats
nvim --headless -u NONE -l tests/nvim/test_agents.lua     # plugin (run from repo root)
sh tests/smoke.sh                                         # smoke S1–S5 with the mock backend
```
Smoke S6–S11 (real model, local model, real `claude`, editor) are by hand — spec §10.2.
