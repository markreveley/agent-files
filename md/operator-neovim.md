# The operator's Neovim setup under Rex

> Status: operator notes · 2026-11-03 · not part of agent-files. agent-files needs only an editor that can open files; this is how the operator's own Neovim and Rex fit together. For what agent-files does with Rex, read [md/docs/rex-host.md](docs/rex-host.md).

## 1. The layout

- **One Rex session per repo.** Before, there was one Ghostty tab per repo. Rex sessions do the same job and keep running when the app quits; reopen it and every session is where you left it.
- **One Neovim per session**, in a Rex pane: nvim-tree on the left, files in the middle, the agent on the right. `<space>cc` toggles the agent: `coder/claudecode.nvim` runs `claude` in a native `:terminal` split (40 % width, right side), and is also its IDE (selection, diffs).
- **Moving between panes:** `ctrl-w h/j/k/l`, as before. Everything is in one Neovim, so Neovim's window keys reach every pane, agents included. Rex's own pane keys come into it only if you split Rex panes beside Neovim.
- **More agents or shells for the same repo:** a Neovim tab or a window split with `:terminal`, as before. A Rex tab or pane would also work, but `ctrl-w` doesn't reach it.
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

## 4. Config to add

In `~/.dotfiles/nvim/.config/nvim/init.lua` (not done; the install clone must have the change first, `git -C ~/code/agent-files pull`):

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
