# agent-files

Threads as plain-text files. Design: [ARCHITECTURE.md](ARCHITECTURE.md). This build: [docs/m1-build-spec.md](docs/m1-build-spec.md).

| Piece | What |
|---|---|
| `bin/agent-files-run` | replay runtime: `init`, `watch`, `once <thread>`, `check <thread>` |
| `bin/agent-files-hook` | Claude Code hook → observed status for hand-started sessions |
| `bin/agent-files-stats` | trial measurement (H1–H4) |
| `bin/agent-files-grep` | logged `rg` over all threads |
| `nvim/` | `agents.nvim`: marks, read-only while working, `:AgentsNew/Send/Stop/Fork/Next/Blocked/Grep` |

**The data root is `~/agent-files/` (or `$AGENT_FILES_ROOT`) — do not clone this repo there.**

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
