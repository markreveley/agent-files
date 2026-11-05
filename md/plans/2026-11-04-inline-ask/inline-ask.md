# Plan: inline questions in any Markdown file

> Status: proposed · 2026-11-04 · from the operator's request, 2026-11-04

**Goal.** In any `.md` file open in Neovim, you write a question between `<-` and `->` lines and save. The agent answers in place, in a `===` block under the question, without leaving the document:

```
<-
what is this section referring to
->
===
This section describes ...
===
```

Change the question and save again, and the new answer replaces the old one.

**Why build it into agent-files.** This is a thread turn without the thread file. It reuses the runner's backends, config, spend cap and escaping, and lives in `agents.nvim` next to the thread buffers. The operator decided against adopting an outside tool for it (2026-11-04). aider's `--watch-files` mode (`AI?` comments answered on save) is the nearest existing tool; look at it as reference only, for the grammar and edge cases, if a step gets stuck.

## Decisions

- **D1. Saving triggers it; nothing polls.** Neovim fires `BufWritePost` on every save. One autocmd on `*.md` covers every Markdown buffer; the file system is never watched. `thread.md` files under the data root are skipped (the runner owns them). `vim.g.agents_ask = false` turns it off everywhere, and `vim.b.agents_ask = false` turns it off for one buffer.
- **D2. Grammar.** A question is a line that is exactly `<-`, the question's lines, then a line that is exactly `->`. An answer is a line starting `===`, the answer's lines, and a line that is exactly `===`, directly under the `->` (blank lines between are allowed). Markers inside fenced code blocks don't count. An unclosed `<-` is ignored until it is closed.
- **D3. Pending vs. answered.** A question with no answer block under it is pending. The answer's opening line carries a short hash of the question text: `=== 3f9a2c`. A question whose text no longer matches its hash is pending again, and its new answer replaces the old block (operator's decision, 2026-11-04: changing a question replaces the answer). The hash survives closing and reopening the file; see Q1.
- **D4. Neovim writes the answer, into the buffer.** No outside program writes the file, so nothing collides with your typing and `FileChangedShell` never fires. When a reply arrives, the plugin finds the question again by its text (you may have edited above it), replaces or inserts the answer block as one undo step, and leaves the buffer modified. It does not save; you do, and that save finds nothing pending. If the question is gone by then, the answer is dropped with a message.
- **D5. The model call is a CLI: `agent-files-ask`.** The plugin runs it with `vim.system` (not blocking). It reads JSON on stdin (`{"path", "text", "question", "line"}`), sends the whole document as context with the question and its line number, and prints the answer on stdout. It uses the backend, model and spend cap from `config.toml` (`[ask]` table, else the default agent's model), through `lib/agent_files/backends`. Errors go to stderr with a non-zero exit, and the plugin shows them; the document is not touched.
- **D6. Escaping.** An answer line that is exactly `===`, `<-` or `->`, or begins with `=== `, is written with a leading `\`, the way runner output escapes `\END`. The parser reads `\` lines back as text.
- **D7. Alerts.** `vim.notify` when questions are sent ("asking 2 questions…") and when each answer lands or fails. `vim.b.agents_ask_pending` holds the count, for the statusline or tabline.
- **D8. One request per question, at most one in flight per question.** Saving again while a question is in flight doesn't send it twice; if its text changed meanwhile, the stale reply is dropped and the new text sent.

## Questions

- **Q1.** D3 puts a hash on the answer's opening line (`=== 3f9a2c`), which is visible. The alternative is a sidecar keyed by file path, which keeps the line a bare `===` but breaks when the file is moved or edited elsewhere. Recommendation: the hash. Ask the operator at step 1.
- **Q2.** Should asks leave a record (a request/response pair, as a thread's `steps/` does), and where? Recommendation: not in v1; spend still counts toward the daily cap. Ask at step 2.

## Steps

1. **Parser** (`nvim/lua/agents/ask.lua`): find questions, answers, hashes, fences and escapes (D2, D3, D6); return the pending questions and the range each answer goes in. Headless tests in `tests/nvim/test_agents.lua`, with a fixture in `tests/fixtures/`.
2. **CLI** (`bin/agent-files-ask`, logic in `lib/agent_files/ask.py`): D5, with tests on the mock backend in `tests/test_ask.py`; refuses a code-checkout root like the other programs. `install.sh` links it.
3. **Plugin wiring**: the autocmd, the in-flight table, insertion and replacement as one undo step, alerts (D1, D4, D7, D8). Headless tests with a fake `agent-files-ask` that answers instantly and one that sleeps, to check edits during a request.
4. **Docs**: a section in ARCHITECTURE §11 (Neovim), the `[ask]` table in the build spec's config section, a line in `md/plans/README.md` marking this plan done.
