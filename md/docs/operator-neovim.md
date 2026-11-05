# The operator's Neovim setup under Rex

> Status: operator notes · 2026-11-04 · not part of agent-files. agent-files is built for Neovim (Neovim-first since 2026-11-04); this is how the operator's own Neovim and Rex fit together. For what agent-files does with Rex, read [md/docs/rex-host.md](rex-host.md).

## 1. The layout

- **One Rex session per repo.** Before, there was one Ghostty tab per repo. Rex sessions do the same job and keep running when the app quits; reopen it and every session is where you left it.
- **One Neovim per session**, in a Rex pane: nvim-tree on the left, files in the middle, the agent on the right. `<space>cc` toggles the agent: `coder/claudecode.nvim` runs `claude` in a native `:terminal` split (40 % width, right side), and is also its IDE (selection, diffs).
- **Moving between panes:** `ctrl-w h/j/k/l`, as before. Everything is in one Neovim, so Neovim's window keys reach every pane, agents included. Rex's own pane keys come into it only if you split Rex panes beside Neovim.
- **More agents or shells for the same repo:** a Neovim tab or a window split with `:terminal`, as before. A Rex tab or pane would also work, but `ctrl-w` doesn't reach it. Planned: the `agents.nvim` sidebar starts, lists and switches the agent sessions in this Neovim ([plan](../plans/2026-11-04-nvim-sidebar/nvim-sidebar.md)).
- **Copying out:** `"+y` from a file or an agent's terminal buffer, paste into a shell.

## 2. What Rex adds over Ghostty alone

- **Persistence.** Neovim, its terminals and the agents in them outlive the terminal app. A machine reboot still ends them (not checked); `claude --resume` (`<space>cr`) picks a session up again.
- **Remote hosts**, optional: a Rex server on another machine, added with `rex hosts add LABEL ENDPOINT`, runs sessions there while the laptop sleeps.
- **A scriptable CLI** (`rex capture`, `rex send`, `rex run`, `rex events --json`) for Rex panes. It sees your Neovim as one pane, though, so it cannot reach the agents inside it. §3 covers those.

## 3. Reading and typing into the agents inside Neovim

`agents.nvim` (ARCHITECTURE §11.2) works on any terminal buffer in this Neovim, including the one claudecode.nvim opens:

- `:AgentsTerms` lists them, with buffer number, harness and send policy.
- `:'<,'>AgentsTermSend claude` types the selection into the `claude` terminal and presses Enter; `:AgentsTermSend 12` with no range types the unnamed register (what you last yanked); `!` leaves out the Enter. With two `claude` terminals open, give the buffer number.
- `:AgentsTermCapture claude 200` opens the last 200 lines of that terminal in a scratch buffer, to search or yank.
- From an agent or a shell inside this Neovim: `agent-files-term ls`, `agent-files-term capture <target> -n 200`, `agent-files-term send <target> "text"`. `$NVIM` is already set inside every `:terminal`, so it finds this Neovim by itself.

**The send rule.** `claude` and `codex` take only text you wrote: an `agent-files-term send` into them is refused. Agents can read any terminal and type into shells. A harness on an API key, or one whose terms allow it, can be opened up per terminal: `:let b:agents_send = "any"` in its buffer. This is ARCHITECTURE §5.1, decided per harness on 2026-11-03.

### 3.1 Reference

Everything the code comments in `nvim/lua/agents/term.lua` and `bin/agent-files-term` say, in one place.

**What it is.** `agents.term` is a module of `agents.nvim`, the Neovim plugin that agent-files ships in its `nvim/` folder (built for agent-files in M1, not third-party). `agent-files-term` is its command-line side, in `bin/`.

**Targets.** Every command takes a target, matched in this order:
1. A buffer number (`:AgentsTerms` shows them): always exact.
2. A harness name (`claude`, `codex`): if exactly one terminal runs it.
3. Any text found in a terminal's command, directory or title: if exactly one terminal matches.

If more than one terminal matches, nothing is sent and the error names the buffer numbers to choose from.

**How a harness is recognised.** By process name: the terminal's own process, then everything it started. A `claude` you started from a shell inside the terminal counts too.

**Who is sending.** Every send is either *human* or *agent*:
- *Human*: you ran `:AgentsTermSend`. Always allowed.
- *Agent*: anything through `agent-files-term`, whoever typed it. Refused when the terminal's policy is `human`.

**Policies.** `human` (only your text) or `any`. `claude` and `codex` are `human`; everything else, including shells, is `any`. Override one terminal with `:let b:agents_send = "any"` (or `"human"`) in its buffer. A misspelled value counts as `human`.

**Multi-line text.** A harness gets it as one paste, so it arrives as one message. A shell gets it one line at a time, as separate commands. Enter is pressed at the end unless you use `:AgentsTermSend!` or `--no-enter`.

**Capture.** The terminal's screen plus its scrollback, with trailing blank lines dropped. `-n N` (or `:AgentsTermCapture {target} N`) keeps the last N lines.

**`agent-files-term`.**

| Command | Does |
|---|---|
| `agent-files-term ls [--json]` | buffer, harness, policy, command, and whether it has exited |
| `agent-files-term capture TARGET [-n N]` | prints the text |
| `agent-files-term send TARGET "text"` | types the text and presses Enter |
| `agent-files-term send TARGET -` | types what comes in on stdin |
| `--no-enter` | (with `send`) leaves out the Enter |
| `--server SOCKET` | talks to that Neovim instead of `$NVIM` |

Exit status: 0 done; 1 refused, no match, or Neovim not reachable (the reason goes to stderr); 2 wrong usage or no `$NVIM`.

**Which Neovim.** Each Neovim runs its own socket and sets `$NVIM` only inside its own terminals. So an agent reaches the terminals of the Neovim it runs in. To reach another Neovim, pass `--server` with its socket. `:echo v:servername` in that Neovim shows the socket; it is a random path unless that Neovim was started with `nvim --listen /tmp/nvim-<repo>.sock`. The other Neovim must have `agents.nvim` loaded, and its own send policies apply.

## 4. Config to add

In `~/.dotfiles/nvim/.config/nvim/init.lua` (not done yet; the install clone already has `agents.term`, pulled 2026-11-03):

```lua
vim.opt.rtp:append(vim.fn.expand("~/code/agent-files/nvim"))
require("agents").setup({
  root = "~/agent-files",
  tabline = true,
  -- term = { policy = { claude = "human", codex = "human" }, default = "any" },  -- the defaults
})
vim.keymap.set("x", "<leader>ct", ":AgentsTermSend claude<cr>", { desc = "Agents: type selection into claude" })
```

## 5. Things to know

- A `claude` inside Neovim gets Neovim's `REX_SESSION` and `REX_BLOCK` from Rex's hook. A `rex send` to that block types into Neovim, not into the agent; use `agent-files-term` for agents inside Neovim.
- Terminal buffers keep `scrollback` lines (Neovim's default is 10,000), so `:AgentsTermCapture` sees only that much. Raise it for agent terminals if you need more: `autocmd TermOpen * setlocal scrollback=100000`.
- If Rex misbehaves, the same layout works in Ghostty without persistence, or with TUIOS as the fallback host.
