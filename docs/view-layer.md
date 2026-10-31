# The view layer — readable in Neovim, rich in the browser

> Status: draft · 2026-10-31 · companion to [ARCHITECTURE.md](../ARCHITECTURE.md) and [role-of-neovim.md](role-of-neovim.md)
> Not part of M1's go/no-go. Steps 0–1 below are cheap and fix daily friction; step 2 is an optional prototype ([m1-plan](m1-plan.md)).

**Summary.** Markdown stays the single source of truth. Neovim is made to display it well. A separate, read-only HTML view is generated from the same files for rich display (tables, charts, collapsible tool output). The HTML is a cache: delete it and nothing is lost. Nothing is ever translated back from HTML to text.

## 1. The problem

Markdown in Neovim looks broken: headings, tables and long tool output are hard to read. The current workaround is to write in Neovim and read in a separate Markdown viewer (Warp). That works, but it splits one task across two tools and leaves no room for interactive display.

## 2. Decision: one source, two views

| Option | Verdict | Why |
|---|---|---|
| **Markdown source → read-only HTML cache** | **Chosen** | Matches principle 7 (indexes are caches) and principle 2 (plain-text formats). No sync problem. |
| HTML primary, translated to text for editing | Rejected | `thread.md` is also the replay context sent to the model, so the text you edit must be the text the model sees. A translation layer makes two sources of truth, and the round trip is lossy. |
| Hand-edited HTML template filled from data | Rejected | You would be editing the template, not the content, and it would not be readable in Neovim. |

HTML-first is right for one case: **agent outputs** (a report, a dashboard). There the HTML *is* the content. Store it in the thread's `out/` directory and link it from the turn. It is not replayed as context, so no translation is needed.

## 3. Principles

1. **Raw text first.** Every enhanced construct must be readable as plain text in Neovim, `cat` or `grep`. HTML only upgrades it.
2. **One-way.** Markdown → HTML. The HTML never writes to the source.
3. **Read-only view.** Actions that change a thread (send, fork, stop) go through the normal file path ([role-of-neovim.md](role-of-neovim.md)), not the browser. A later step may add buttons that write files; that is out of scope here.
4. **A cache.** Output goes under a cache directory outside the root repo (default `~/.cache/agent-files/view/`). It is never committed.
5. **An extension.** The renderer is an executable named `agent-files-render` on `PATH` (principle 3). Any language.

## 4. Enhanced blocks — the "template" is a convention

Instead of a template file you edit, the markdown carries conventions that degrade gracefully:

| In the source | Neovim shows | HTML renders |
|---|---|---|
| Pipe table | Aligned text (use a table formatter) | Styled, sortable table |
| Fenced ```` ```csv ```` block | Readable rows | Sortable table |
| Fenced ```` ```chart ```` block (see §5.3) | A few lines of `key: value` data | Bar or line chart |
| Fenced ```` ```mermaid ```` block | Diagram source | Diagram |
| `▸ Read src/x.ts (212 lines)` plus indented output ([ARCHITECTURE §4.2](../ARCHITECTURE.md)) | A fold | Collapsed `<details>` |
| `## you · tN` / `## agent · tN` … `END` | Turn headers | Chat-style turns, `END` hidden |
| Frontmatter | YAML | Header card (agent, model, kind, status) |

## 5. Plan

### Step 0 — fix the Neovim display (about an hour, no code)

Most of the "looks broken" problem is the renderer, not the format.

- Install `render-markdown.nvim` or `markview.nvim` for inline headings, tables and code blocks. Needs treesitter `markdown` and `markdown_inline` parsers and a Nerd Font in the terminal.
- Add a table formatter for aligned pipe tables: `prettier --write` on save, or `vim-table-mode`.
- Set `conceallevel=2` for markdown buffers, and `wrap` with `linebreak` for prose.
- Check the colorscheme gives distinct heading levels; some themes flatten them.
- Try `peek.nvim` or `markdown-preview.nvim` for a live browser preview with scroll sync. Use it for a few days before building anything.

**Exit check:** can you read a thread with a table and a long tool output in Neovim without opening Warp?

### Step 1 — thread-aware display in `agents.nvim`

Generic markdown rendering does not know about turns. Add to the plugin ([m1-plan §3.2](m1-plan.md)):

- Highlight groups for `## you · tN`, `## agent · tN`, `END`, and `▸` tool lines.
- A fold for each `▸` line with its indented output, closed by default.
- A virtual-text mark on the last `END` showing the thread's `status`.

### Step 2 — the HTML prototype (`agent-files-render`)

A single script, about 100–150 lines. Read-only. Prove that a browser view is worth having before growing it.

#### 5.1 Interface

```
agent-files-render build [--root DIR] [--out DIR] [THREAD_DIR ...]
agent-files-render watch [--root DIR] [--out DIR] [--port 8765]
```

- `--root` defaults to `~/agent-files`; `--out` defaults to `~/.cache/agent-files/view`.
- `build` renders the given thread directories (all under `threads/` if none) and exits `0` on success, `1` if any file failed.
- `watch` runs `build`, serves `--out` on `127.0.0.1:<port>` only, then re-renders a thread when its `thread.md` or `status` changes and tells open pages to reload.

#### 5.2 Output layout

```
<out>/
├── index.html                       # table of all threads: id, status, last turn, token estimate
├── static/view.css  static/view.js  # one stylesheet, one script, no build step
└── threads/<thread id>/index.html   # one page per thread, branches are nested paths
```

Each thread page shows: the frontmatter card; a breadcrumb and links to child branches (subdirectories containing `thread.md`); turns in order; `status` from the sidecar file; a link to `steps/` files if present.

#### 5.3 Parsing rules

- Split `thread.md` on the turn grammar: a line matching `^## (you|agent|note) · t\d+$` starts a turn; a line that is exactly `END` or `END (...)` closes it. The last turn may have no `END` (a draft); mark it "draft".
- Render turn bodies as CommonMark with pipe tables, escaping raw HTML from the source (the source may contain model output).
- A `▸` line followed by lines indented two spaces becomes a `<details>` block with the first line as `<summary>`.
- A `chart` block holds `key: value` lines, plus optional `title:`, `type: bar|line` header lines. Render as inline SVG. Invalid data falls back to the raw text in a `<pre>`.
- `csv` blocks render as a table with click-to-sort headers.
- `mermaid` blocks load the Mermaid script only on pages that contain one.
- **Never fail on odd input.** Anything that does not parse is shown as raw preformatted text, not dropped.

#### 5.4 Constraints

- **No network at view time.** Vendor the few scripts (Mermaid, a markdown library) into `static/` at install time; the page must work offline.
- **Safe by default.** Source text is data: escape it; no `innerHTML` of source content; bind the server to loopback only.
- **Never write to the root.** The renderer reads `threads/` and writes only under `--out`.
- **Idempotent.** The same input always gives the same output; rebuilding is safe at any time.
- **Suggested stack:** Python 3 standard library plus `markdown-it-py` (or `pandoc` as a subprocess); live reload through a server-sent-events endpoint. Match the M1 runner's language.

#### 5.5 Test fixture

Create `docs/examples/view-fixture/thread.md` with, in one thread: frontmatter; a user turn with a pipe table; an agent turn with a `▸` tool fold (long indented output), a `chart` block, a `csv` block, a `mermaid` block, and a line that looks like a marker inside a code fence; a closed turn with `END (interrupted)`; and a trailing draft turn without `END`. Add a child directory with its own `thread.md`.

#### 5.6 Acceptance checks

1. `agent-files-render build` on the fixture exits `0` and creates `index.html` and one page per thread.
2. Both turn types, the `END (interrupted)` close and the draft turn appear in the right order and styling.
3. The tool fold is collapsed by default and opens on click.
4. The pipe table, `csv` table and chart render; a corrupted `chart` block shows raw text instead of failing.
5. A `<script>` tag in the source appears as visible text and does not run.
6. With `watch` running, appending a turn to the fixture updates the open page within about one second without a manual refresh.
7. With the network disabled, every page still renders.
8. The root repo shows no changes (`git status` clean) after any run.
9. The page for a 50-turn thread opens in under a second.

### Step 3 — only if step 2 earns its keep

Candidates, each optional and in this order: a jump-to-line link that opens a turn in Neovim through the doorbell ([role-of-neovim.md §3](role-of-neovim.md)); a diff view of edits above `END` (the H1 measurement made visible); search across `threads/`; buttons that write files (send, fork, stop) through a small local endpoint that only creates the same files the plugin does.

## 6. How we decide

Treat this like the M1 trial: set the question in advance.

- **Keep the browser view** if, over two weeks, the journal shows you used it for reading on more days than you used Warp or another viewer.
- **Drop step 2** if steps 0–1 already remove the need for a separate viewer. That is a good outcome, not a failure.

## 7. Open questions

1. Should `chart` and `csv` blocks be formalized in the thread grammar ([ARCHITECTURE §4.3](../ARCHITECTURE.md)), or stay renderer-only conventions?
2. Does the model produce these blocks reliably if the agent's system prompt asks for them, or should the renderer detect plain tables only?
3. Where does the cache live on a synced or multi-machine root — per machine, never synced?
4. Should agent-produced HTML artifacts in `out/` be served by the same renderer, with a sandboxed frame, or opened directly?
