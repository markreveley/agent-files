# The operator's Neovim setup under tmux and workmux

> Status: operator notes · 2026-11-05 · not part of agent-files. agent-files is built for Neovim; this is how the operator's own Neovim, tmux and workmux fit together. Why the agents run in tmux panes rather than in Neovim: [tmux-host plan](../plans/2026-11-05-tmux-host/tmux-host.md). The config is in `~/.dotfiles` (`tmux/`, `workmux/`, `nvim/`). Rex is not used.

## 1. The layout

- **Ghostty, then tmux, then one window per worktree.** `workmux add <branch>` makes a git worktree and a tmux window for it, `workmux merge` merges it back and closes the window, and `workmux open` reopens one. The main checkout gets a window of its own (`prefix c`).
- **In each window:** Neovim on the left (nvim-tree, files) and `claude --ide` on the right (40 %), as set in `~/.config/workmux/config.yaml`.
- **Moving between panes:** Option+n/h/e/u (right / left / down / up), or `tn`/`th`/`te`/`tu` in normal mode. Inside Neovim they move between its windows; at Neovim's edge they go on to the next tmux pane. In any other pane tmux moves itself. They wrap at the edge, inside Neovim only when the window has no other tmux pane.
- **More agents or shells:** `prefix |` (beside) or `prefix -` (below) opens a pane in the current directory. A `claude --ide` there connects to the same Neovim. For separate work, use another worktree (`workmux add`).
- **Status and switching:** icons in the tmux window list (🤖 working, 💬 waiting, ✅ done). Then:
  - `prefix C-t`: the sidebar.
  - `prefix C-s`: the dashboard (`prefix C-w` opens it on its worktrees tab).
  - `prefix L`: jump to the last agent that finished or is waiting.
  - `prefix Tab`: switch between the two most recent agents.
- **Persistence:** tmux keeps everything when Ghostty quits (`tmux attach`). After a reboot or a tmux crash, `workmux resurrect` reopens the worktree windows, and `claude --resume` (or `--continue`) picks a session up again.
- **Copying out:** tmux copy mode (`prefix [`, with the init.lua motions; `y` copies to the clipboard), or `"+y` in Neovim.

## 2. Claude and Neovim: the IDE link

claudecode.nvim (`provider = "none"`) runs a WebSocket server inside Neovim. `claude --ide` in the next pane connects when it starts in Neovim's workspace; in a session that is already running, type `/ide`. With two Neovims on the same folder it can't choose, so `/ide` picks.

| Key | Does |
|---|---|
| `<leader>cs` (visual) | send the selection to Claude |
| `<leader>cb` | add the current buffer |
| `<leader>cs` in nvim-tree | add that file |
| `<leader>cy` / `<leader>cn` | accept / reject Claude's diff |

Claude also sees the current selection as it changes, the open buffers and the diagnostics. `<leader>cc`, `cf`, `cr` and `cC` are gone: Claude no longer runs in a Neovim split.

## 3. Reading and typing into agents

- **Agents in tmux panes** (the usual case): `workmux capture <worktree> [-n 200]` and `workmux send <worktree> "text"` (or `-f file`, or stdin). Without workmux: `tmux capture-pane -p -t <pane>` and `tmux send-keys -t <pane>`.
- **Terminals inside Neovim** (a shell, or a harness you start with `:terminal`): `agents.nvim` reaches them through Neovim's socket. tmux can't, because to tmux they are part of Neovim's pane.
  - `:AgentsTerms` lists them, with buffer number and harness.
  - `:'<,'>AgentsTermSend claude` types the selection into the `claude` terminal and presses Enter. With no range, `:AgentsTermSend 12` types the unnamed register (what you last yanked). `!` leaves out the Enter. With two `claude` terminals open, give the buffer number.
  - `:AgentsTermCapture claude 200` opens the last 200 lines of that terminal in a scratch buffer, to search or yank.
  - From a shell inside this Neovim: `agent-files-term ls`, `agent-files-term capture <target> -n 200`, `agent-files-term send <target> "text"`. `$NVIM` is already set inside every `:terminal`, so it finds this Neovim by itself.
- **Anything is sent as your message.** There is no send policy (tmux-host D5): a send through any of these is your message relayed, whoever runs it.

### 3.1 `agents.term` reference

Everything the code comments in `nvim/lua/agents/term.lua` and `bin/agent-files-term` say, in one place.

**What it is.** `agents.term` is a module of `agents.nvim`, the Neovim plugin that agent-files ships in its `nvim/` folder (built for agent-files in M1, not third-party). `agent-files-term` is its command-line side, in `bin/`.

**Targets.** Every command takes a target, matched in this order:
1. A buffer number (`:AgentsTerms` shows them): always exact.
2. A harness name (`claude`, `codex`): if exactly one terminal runs it.
3. Any text found in a terminal's command, directory or title: if exactly one terminal matches.

If more than one terminal matches, nothing is sent and the error names the buffer numbers to choose from.

**How a harness is recognised.** By process name, from the `harnesses` list (`claude` and `codex` by default): first the terminal's own process, then everything it started. A `claude` you started from a shell inside the terminal counts too.

**Multi-line text.** A harness gets it as one paste, so it arrives as one message. A shell gets it one line at a time, as separate commands. Enter is pressed at the end unless you use `:AgentsTermSend!` or `--no-enter`.

**Capture.** The terminal's screen plus its scrollback, with trailing blank lines dropped. `-n N` (or `:AgentsTermCapture {target} N`) keeps the last N lines.

**`agent-files-term`.**

| Command | Does |
|---|---|
| `agent-files-term ls [--json]` | buffer, harness, command, and whether it has exited |
| `agent-files-term capture TARGET [-n N]` | prints the text |
| `agent-files-term send TARGET "text"` | types the text and presses Enter |
| `agent-files-term send TARGET -` | types what comes in on stdin |
| `--no-enter` | (with `send`) leaves out the Enter |
| `--server SOCKET` | talks to that Neovim instead of `$NVIM` |

Exit status: 0 done; 1 failed (no match, no running job, or Neovim not reachable; the reason goes to stderr); 2 wrong usage or no `$NVIM`.

**Which Neovim.** Each Neovim runs its own socket and sets `$NVIM` only inside its own terminals, so an agent in a tmux pane has no `$NVIM`. Pass `--server` with the socket. `:echo v:servername` in that Neovim shows it; it is a random path unless that Neovim was started with `nvim --listen /tmp/nvim-<repo>.sock`. Finding it by name is the [nvim-addressing plan](../plans/2026-11-03-nvim-addressing/nvim-addressing.md). The other Neovim must have `agents.nvim` loaded.

## 4. Config to add

In `~/.dotfiles/nvim/.config/nvim/init.lua` (not done yet; the install clone already has `agents.term`, pulled 2026-11-03):

```lua
vim.opt.rtp:append(vim.fn.expand("~/code/agent-files/nvim"))
require("agents").setup({
  root = "~/agent-files",
  tabline = true,
  -- term = { harnesses = { "claude", "codex" } },  -- the default
})
```

## 5. Things to know

- workmux's hooks mark the tmux window of the pane they run in (`$TMUX_PANE`). A `claude` inside Neovim's `:terminal` would mark Neovim's window, shared with every other session in that Neovim; that is one reason the sessions run in their own panes.
- `workmux setup` rewrites `~/.claude/settings.json` (its hooks) and sets tmux's `window-status-format` for the session. Read its changes before committing the dotfiles.
- Without workmux, tmux alone still works: split a pane and run `claude --ide`. Only the status icons, the sidebar and the worktree commands are lost.
- Terminal buffers inside Neovim keep `scrollback` lines (Neovim's default is 10,000), so `:AgentsTermCapture` sees only that much. Raise it if you need more: `autocmd TermOpen * setlocal scrollback=100000`. tmux keeps 50,000 lines per pane (`history-limit`).
