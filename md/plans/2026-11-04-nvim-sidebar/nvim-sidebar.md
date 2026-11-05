# Plan: the agent sidebar in `agents.nvim`

> Status: proposed · 2026-11-04 · replaces the separate neovim-agent-sidebar repo, which is folded in here and deleted · thread: thread-archive `threads/agent-files/2026-11-04-nvim-sidebar.md`

**Goal.** A pane on the left of Neovim lists every agent: the `claude` and `codex` sessions running in Neovim's terminals, and agent-files' own threads. Moving onto one and pressing Enter shows it in the main window, the way nvim-tree opens a file: a session's terminal, or a thread's `thread.md`. Sessions keep running while not shown, and closed Claude sessions can be resumed from the list.

**Why here and not in its own plugin.** A separate plugin would host the same terminals that `agents.term` reads, and would watch the same Claude Code events that `agent-files-hook` records, with its own status words and its own idea of which session is which. Two designs for one thing. Built into `agents.nvim`, there is one status source (the observed threads), one identity (the Claude session id), one list, and one send policy (`agents.term`). agent-files is Neovim-first (ARCHITECTURE §1): Neovim hosts the harness sessions, and Rex hosts Neovim.

## Decisions

- **D1. Sessions are terminal buffers, not tabs.** A `:terminal` is a buffer; its process runs whether or not a window shows it. Showing a session is `nvim_win_set_buf(main_win, buf)`. Tabs stay free, and the operator's `nk` (zoom into a new tab) and `nK` keymaps work on a session window unchanged ([md/operator-neovim.md](../../docs/operator-neovim.md)).
- **D2. Sessions run as children of Neovim** (`jobstart(cmd, { term = true })`). Quitting Neovim ends them; resuming (D6) brings Claude sessions back. Rex keeps Neovim, and so the sessions, alive when the terminal app quits.
- **D3. The harness is a command.** `claude` by default, `codex` or any other. Hook-based status (D5) and resume (D6) apply to Claude Code only; other harnesses get activity status.
- **D4. Claude sessions connect to claudecode.nvim, if it is installed.** Each `claude` starts with the environment claudecode.nvim gives its own terminal (`lua/claudecode/terminal.lua`): `ENABLE_IDE_INTEGRATION=true`, `FORCE_CODE_TERMINAL=true`, `CLAUDE_CODE_SSE_PORT=<require("claudecode.server.init").state.port>`. Each session then opens files and shows diffs in this Neovim; the server tracks diffs per client, so several sessions can connect at once (read in claudecode.nvim's source on 2026-11-04: `lua/claudecode/server/tcp.lua` keeps a table of clients, and `diff.close_diffs_for_client` closes one client's diffs; recheck after a plugin update). Without claudecode.nvim this step is skipped. Consequence for the runner: these variables are inherited by anything a session runs, including `agent-files-run`, so the `claude -p` backend removes them (and every other `CLAUDE_CODE_*` IDE variable) from its environment, as it already removes the API keys. Otherwise a headless turn could connect to Neovim's IDE server and gain tools.
- **D5. One status source: the observed threads.** The sidebar runs no hook of its own. It reads `threads/_observed/*/status`, written by `agent-files-hook`, through the plugin's existing file watcher, and shows the same words as everywhere else: `working`, `blocked`, `done`, `failed`, `closed`. A harness without hooks (Codex, a shell) gets `working` while its terminal output changed in the last few seconds (`nvim_buf_attach` `on_lines`), else `done`; `closed` when its job exits.
- **D6. Identity and resume come from the hook.** The sidebar starts each session with `AGENT_FILES_AGENT=<sidebar id>` in its environment. The hook records it, and the full session id, in the observed thread's frontmatter (`agent:`, `session:`). That joins a terminal buffer to its observed thread with no guessing. On `SessionEnd` the hook writes `closed` instead of removing the directory, so a closed Claude session stays listed; Enter on it runs `claude --resume <session>` in its `project:` directory. `d` on a closed entry removes its directory (after a confirm). The sidebar keeps no state file of its own.
- **D7. Sessions started elsewhere are listed too.** A `claude` started by hand in `:terminal` or by claudecode.nvim (`<leader>cc`) has an observed thread but no `agent:`. The sidebar lists it; Enter shows its terminal if exactly one terminal buffer in this Neovim runs that harness in that directory (`agents.term`'s detection), and otherwise opens its `thread.md`.
- **D8. The sidebar never types into a session.** Sending text stays with `agents.term` and its policy (ARCHITECTURE §5.1): Claude and Codex take only text a human wrote.
- **D9. The spawn backend is a seam.** v1 spawns with `jobstart`. The interface (`spawn`, `show`, `kill`) stays narrow so a Rex backend can come later (sessions in Rex panes, shown by `rex swap`). Not built now.

## Parts

1. **Spawn** (`nvim/lua/agents/spawn.lua`): `spawn({ name, cwd, cmd })` makes a buffer, runs `jobstart(cmd, { term = true, cwd, env })` with `AGENT_FILES_AGENT` and the D4 variables, sets `bufhidden=hide` and names the buffer `agent://<name>`. Keeps an in-memory map from sidebar id to buffer. `kill(id)` stops the job.
2. **Sidebar** (`nvim/lua/agents/sidebar.lua`): a scratch buffer, `filetype=agentsidebar`, in a fixed-width window pinned to the left. Two groups, sessions and threads; one line each: status mark, name, status word. The marks are the tabline's (spinner, red dot, check). Keys:

   | Key    | Action                                                   |
   | ------ | -------------------------------------------------------- |
   | `<CR>` | show in the main window (a terminal, or a `thread.md`)   |
   | `o`    | show in a split                                          |
   | `a`    | new session (prompts: name, cwd, harness)                |
   | `r`    | rename (the sidebar name only)                           |
   | `d`    | kill a running session; remove a closed one (confirms)   |
   | `q`    | close the sidebar                                        |

3. **Main window tracking**: the sidebar remembers the last other window it showed into; if that window is gone, it uses the nearest window to its right, or opens one.
4. **Hook changes** (`bin/agent-files-hook`, tests in `tests/test_hook.py`): `SessionEnd` writes `closed` and keeps the directory; the frontmatter written on creation gains `session: <full id>` and, when `AGENT_FILES_AGENT` is set, `agent: <id>`. Still standard library only, under 100 ms, silent.
5. **Runner environment** (`lib/agent_files/backends/claude_cli.py`): drop the D4 variables before calling `claude -p`. Test with those variables set.
6. **Commands**: `:AgentsSidebar` (toggle), `:AgentsSpawn` (new session; `:AgentsNew` already makes a thread), `:AgentsSessionNext` / `:AgentsSessionPrev` (cycle sessions in the main window). No default keymaps; the operator's are added in `~/.dotfiles/nvim/` (`<leader>a` is LSP code action there).

## Steps

1. Parts 1–3. Done when two `claude` sessions can be started from the sidebar, switched between with `<CR>`, and keep running while hidden. Headless tests in `tests/nvim/test_agents.lua` with a fake harness command.
2. Part 4 (hook) and D5 status in the sidebar. Done when a sidebar session shows `blocked` the moment a permission dialog opens, and `closed` after `/exit`.
3. D6 resume and D7 sessions started elsewhere.
4. D4 and part 5. Done when a file opened by either of two sessions appears in Neovim, a diff from each can be accepted, and `agent-files-run` started from such a session gets no IDE variables.
5. Part 6, the ARCHITECTURE §11 update, the operator's keymaps in `~/.dotfiles/nvim/`, and `:help`.

## Out of scope

A worktree per session, rendering transcripts as anything but the terminal, harnesses without a terminal, the Rex backend (D9), and the addressable-Neovim plan ([nvim-addressing.md](../2026-11-03-nvim-addressing/nvim-addressing.md)), which stays separate.

## Questions

- Q1. Selection broadcast (D4): claudecode.nvim sends the current selection to every connected session. Acceptable, or should only the shown session receive it? The latter needs a change in claudecode.nvim. Waits on step 4.
- Q2. Does `claude --resume <id>` keep the same session id, so the resumed session writes into the same observed thread? If it forks a new id, the hook should match on `agent:` and update `session:`. Check in step 3.
- Q3. Sessions the hook never saw (run before the hook was installed, or on another machine) have no observed thread, so D6 cannot resume them. List them too, from Claude Code's own transcripts (`~/.claude/projects/<project>/*.jsonl`) behind a picker, or leave them to `claude --resume` in a terminal? Waits on step 3.
