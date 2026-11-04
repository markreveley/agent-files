# Plan: Neovim instances you can address by name

> Status: proposed · 2026-11-03 (Q2, Q3 decided; Q1 moved to the doorbell revisit) · extends `agents.term` ([ARCHITECTURE §11.2](../../ARCHITECTURE.md), [operator-neovim §3](../operator-neovim.md#3-reading-and-typing-into-the-agents-inside-neovim))
> Not built before the M1 day-10 decision (Q2), and not until the doorbell revisit answers Q1.

**Goal.** Every Neovim the operator starts gets a socket at a known path, and the socket's name is its id: `agent-files`, `identikey-dev`, one per repo. An agent in one Neovim can then list the others and read or type into their terminals by id (`agent-files-term --server identikey-dev capture claude`), instead of needing a random socket path that only `:echo v:servername` reveals.

**What stays the same.** The send policy (ARCHITECTURE §5.1) is checked by the *receiving* Neovim, so a send from another Neovim is an agent send like any other: refused for `claude` and `codex` terminals, allowed for shells and API-keyed harnesses. Reading is always allowed.

## Design

**The directory is the registry.** Sockets live in `~/.local/state/agent-files/nvim/` (mode `0700`), named `<id>.sock`. `ls` of that directory lists every addressable Neovim. No file other than the socket is written, by anyone. The socket exists only while its Neovim runs; a crash can leave a dead one, which the next launch or `peers` removes.

- Why this directory: it sits beside agent-files' other state, and it is short. A unix socket path is limited to 104 bytes on macOS; this one is 68 bytes for the longest repo name on this Mac.

**The id.**
1. An explicit name, if given.
2. Otherwise the repo's directory name: the basename of `git rev-parse --show-toplevel`, or of the working directory outside a repo.
3. If that id is taken by a live Neovim, `-2`, `-3`, … is appended.

Ids are lowercased and limited to `[a-z0-9._-]`.

**The launcher: `agent-files-nvim [--name ID] [nvim args…]`.** A POSIX `sh` script in `bin/`, installed by `install.sh` like the others:
1. Work out the id.
2. If `<id>.sock` exists and its Neovim doesn't answer (`nvim --server S --remote-expr 1` fails within 1 s), remove it.
3. `exec nvim --listen <dir>/<id>.sock "$@"`.

The shell function is a one-liner in the operator's dotfiles, so plain `nvim` gets a socket:

```sh
nvim() { agent-files-nvim "$@"; }
```

An executable rather than only a function, so it can be tested, checked with `shellcheck`, and run by an agent or a Rex `run` command (principle 3).

**`agent-files-term` changes.**
- `--server ID`: a value without a `/` is read as an id in the socket directory. A path still works.
- `agent-files-term peers [--json]`: one line per live socket: id, working directory and terminal count (one `--remote-expr` call each). Dead sockets are removed and not listed.
- `agent-files-term ls --all`: the terminals of every peer, each prefixed with its id.
- `$NVIM` stays the default target, so nothing changes for an agent talking to its own Neovim.

**Inside Neovim.** `agents.nvim` exposes the id as `vim.g.agents_nvim_id` (read from `v:servername`), and `:AgentsTerms` shows it in its first line. Nothing else changes: the plugin writes no file for this.

## Not the dropped editor registry

The doorbell's editor registry (role-of-neovim §10) was dropped on 2026-11-01, and AGENTS.md says never to build what is dropped. This plan differs from it:

| | Dropped editor registry | This plan |
|---|---|---|
| Purpose | Ring editors when a thread changes (attention) | Address a Neovim's terminals by name (operator tooling, §11.2) |
| Files written | One per Neovim, by `agents.nvim` on `VimEnter` | None; the socket is the entry |
| Who calls it | Hooks, the runner, the Notifier | Agents and shells, on request |
| Carries | Thread paths and events | Terminal text, under the §5.1 policy |

Whether that difference is enough is Q1.

## Steps

1. `bin/agent-files-nvim`, with `shellcheck` clean. *Waits on Q1 and the day-10 decision.*
2. `agent-files-term`: id resolution for `--server`, `peers`, `ls --all`.
3. `agents.nvim`: `vim.g.agents_nvim_id`, and the id in `:AgentsTerms`.
4. Tests: `tests/test_term.py` starts two headless Neovims through `agent-files-nvim`, checks `peers` lists both, and sends and captures across them, including a refused send to a `human`-policy terminal in the other Neovim. Plus a dead socket being removed, and an id collision getting `-2`.
5. Docs: ARCHITECTURE §11.2, [operator-neovim](../operator-neovim.md) §3.1 and §4 (the function), the README table.
6. Operator: add the function to the dotfiles, restart Neovims. *Waits on Q4.*

## Questions

1. **Is this the dropped registry under another name?** *Moved (2026-11-03):* the operator asked to revisit the doorbell and its editor registry now that TUIOS is no longer the host ([next-agents.md](../../next-agents.md), step 7). That analysis answers this question, and may merge the two designs.
2. *Decided (2026-11-03): after the M1 day-10 decision.* It stays a plan until then.
3. *Decided (2026-11-03): the repo name*, with `--name` for anything else. The Rex session label was the alternative; it works only inside Rex and can change while Neovim runs.
4. **Replace `nvim` or use another name?** The function above makes every `nvim` addressable, including quick edits from a shell, which then appear in `peers`. A separate name (say `nv`) keeps quick edits out. Recommendation: replace `nvim`; `peers` shows the working directory, so stray ones are easy to tell apart. Two more points:
   - *For replacing:* a Neovim started without the launcher is unreachable, and you find out only when an agent can't find it. With the function there is no second command to remember.
   - *A limit either way:* a shell function covers only `nvim` typed in an interactive shell. Programs that start Neovim themselves (`git commit` through `$EDITOR`, for example) bypass it. Those are the short-lived edits you'd want left out anyway.
