# Adversarial audit, 2026-11-02: what is left

| | |
|---|---|
| Checked | parser, runner and backends, hook/stats/install, Neovim plugin, docs: five parallel read-only audits |
| Commit | the tree before the audit fixes merged in PR #24 (`b1bd8d8`) |
| Rechecked | 2026-11-04: items about code removed since were dropped |
| Reported | here only; no tracker entries |
| Status | every item below is open. Delete an item when it is fixed and has a test |

Five parallel read-only audits ran before first use: parser, runner and backends, hook/stats/install, Neovim plugin, and docs. At the time the baseline was green: 70 unit tests, 44 Neovim checks, smoke S1-S5.

Its A list (wrong stats numbers, wedged threads, `claude-cli` billing the API, plugin data loss) and B list (operator steps that fail verbatim) were fixed in branch `claude/audit-fixes-2026-11-02`. Each code fix has a test that failed before it. Afterwards: 93 unit tests, 75 Neovim checks, smoke S1-S5 green. Read that branch's commits for what changed.

What follows was **not** fixed. None of it loses data in normal use. Fix an item when it causes friction. Delete an item when it's fixed and has a test. Items about code removed since (stats' edit counts, grep's log) were dropped on 2026-11-04.

## Edge cases found by the audit

- **Parser:**
  - A frontmatter value keeps an inline `# comment` (`thread.py:94-103`), so `runtime: direct  # x` is not direct.
  - A UTF-8 BOM hides the frontmatter (`thread.py:290`; use `utf-8-sig`).
  - The Lua patterns `^%s*(.-)%s*$` and `gsub("%s+$")` are quadratic on long runs of whitespace: a line with 40k spaces takes 9.8 s to parse, on every keystroke.
  - Python strips Unicode whitespace and Lua doesn't (an NBSP-indented fence, `END<NBSP>`). Python's `\d` also accepts non-ASCII digits.
  - `## carry` after stray text: Python drops it, Lua highlights it.
  - `escape_carry` (`init.lua:~308`) lacks `\b` and re-escapes lines that are already escaped, so the model sees `\## notes` in a fork's carry.
  - A fence line between `END` and the next header flips `in_fence`, which can hide that header.
- **Runner:**
  - `output_config.effort` is sent to every model (`anthropic.py:13`); Sonnet 4.5 and Haiku 4.5 reject it with a 400.
  - Bad UTF-8 in any `thread.md` crashes `watch`, because `UnicodeDecodeError` isn't an `OSError`.
  - `claude_cli`:
    - it treats a nonzero exit with no `result` event as `done`;
    - it has no timeout, and STOP waits for the child's next line;
    - a stopped `claude -p` records no cost, because the child is killed before its `result` event.
  - A stopped anthropic stream records only the output tokens from `message_start`, so its cost is slightly low.
  - `spend_today` uses file mtime, so a clone or checkout puts old spend on today.
  - A bad TOML makes `once` exit 0; the spec says 1.
  - A quoted price raises `TypeError` after `END`.
  - The commit lock covers only this process.
- **Hook:**
  - The observed directory is keyed by the basename of `cwd`, which follows `cd`, so a session can leave an orphaned `working` directory.
  - `SessionStart` with source `compact` sets `done` mid-turn.
  - `PermissionDenied` isn't registered, so the status stays `blocked` after a denial.
  - `session_id` isn't validated. `../..` can delete `threads/`; real UUIDs can't.
  - The hook and grep don't enforce D1: they don't refuse a code-checkout root.
- **Plugin:**
  - Each reload is an undo step (fix: `undoreload=0`).
  - `:AgentsNew .` and `:AgentsNew ..` are accepted.
  - `:bd` doesn't detach the buffer.
  - A missing `agent-files-grep` raises E475.
  - A model-written `▸` line can fold real content.
  - The plugin no longer reacts when another editor writes `seen`.
- **Smoke:** S2-S5 assert less than their names claim. The runner behaves correctly; the asserts are just thin.
