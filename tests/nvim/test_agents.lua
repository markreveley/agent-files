-- Run: nvim --headless -u NONE -l tests/nvim/test_agents.lua   (from the repo root)
local repo = vim.fn.getcwd()
vim.opt.rtp:prepend(repo .. "/nvim")
local tmp = vim.fn.tempname()
vim.fn.mkdir(tmp .. "/threads", "p")
vim.env.AGENT_FILES_ROOT = tmp

local fails, n = 0, 0
local function ok(cond, msg)
  n = n + 1
  if not cond then fails = fails + 1; print("FAIL: " .. msg) end
end
local function eq(a, b, msg) ok(vim.deep_equal(a, b), msg .. " (got " .. vim.inspect(a) .. ", want " .. vim.inspect(b) .. ")") end

local errors = {}
local orig_notify = vim.notify
vim.notify = function(m, lvl) if lvl == vim.log.levels.ERROR then errors[#errors + 1] = m end end

local agents = require("agents")
agents.setup({ root = tmp })
local D = require("agents.display")

local function readf(p) return vim.fn.readfile(p) end
local function write_status(dir, s) vim.fn.writefile({ s }, dir .. "/status") end

-- :AgentsNew ------------------------------------------------------------------------------------
vim.cmd("AgentsNew smoke")
vim.cmd("stopinsert")
local dir = tmp .. "/threads/smoke"
local buf = vim.api.nvim_get_current_buf()
eq(readf(dir .. "/thread.md"), { "---", "agent: default", "runtime: direct", "model: null", "context: replay", "kind: main", "---", "", "## you · t1", "" }, "AgentsNew file")
ok(agents.attached[buf] ~= nil, "buffer attached")
vim.cmd("AgentsNew BAD/slug")
ok(#errors == 1, "bad slug rejected")

-- :AgentsSend refusals and success --------------------------------------------------------------
errors = {}
vim.cmd("AgentsSend")
ok(#errors == 1 and errors[1]:find("empty"), "empty turn refused: " .. vim.inspect(errors))
errors = {}
vim.api.nvim_buf_set_lines(buf, -1, -1, false, { "```", "open fence" })
vim.cmd("AgentsSend")
ok(#errors == 1 and errors[1]:find("fence"), "open fence refused: " .. vim.inspect(errors))
vim.api.nvim_buf_set_lines(buf, -3, -1, false, {})
vim.api.nvim_buf_set_lines(buf, -1, -1, false, { "hello", "", "" })
errors = {}
vim.cmd("AgentsSend")
eq(#errors, 0, "send ok")
local f = readf(dir .. "/thread.md")
eq(f[#f], "END", "END appended")
eq(f[#f - 1], "hello", "trailing blanks trimmed")
errors = {}
vim.cmd("AgentsSend")
ok(#errors == 1, "second send refused (last section is not an open you turn)")

-- read-only while working, and reload + scaffold --------------------------------------------------
write_status(dir, "working")
ok(vim.wait(3000, function() return not vim.bo[buf].modifiable end, 50), "read-only while working")
eq(vim.bo[buf].readonly, true, "readonly flag")
-- simulate the runner finishing the turn
local fh = io.open(dir .. "/thread.md", "a")
fh:write("\n## agent · t2\necho: hello\n\nEND\n\n## you · t3\n\n")
fh:close()
write_status(dir, "done")
ok(vim.wait(3000, function() return vim.bo[buf].modifiable and #vim.api.nvim_buf_get_lines(buf, 0, -1, false) > 14 end, 50), "buffer reloaded and writable again")
local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
eq(lines[#lines - 1], "## you · t3", "scaffold present after reload")

-- draft re-apply --------------------------------------------------------------------------------
vim.api.nvim_buf_set_lines(buf, -1, -1, false, { "my half-written draft" })
ok(vim.bo[buf].modified, "buffer modified by draft")
local fh2 = io.open(dir .. "/thread.md", "a")
fh2:write("")
fh2:close()
-- external rewrite: a new agent turn + scaffold t5 (file changed under the modified buffer)
local ext = readf(dir .. "/thread.md")
local base = {}
for i = 1, #ext do base[#base + 1] = ext[i] end
while base[#base] == "" do base[#base] = nil end
base[#base] = nil -- drop the '## you · t3' scaffold header
vim.list_extend(base, { "## you · t3", "again", "END", "", "## agent · t4", "ok", "END", "", "## you · t5", "" })
vim.fn.writefile(base, dir .. "/thread.md")
write_status(dir, "done")
ok(vim.wait(4000, function()
  local l = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local has_new, has_draft = false, false
  for _, x in ipairs(l) do
    if x == "## agent · t4" then has_new = true end
    if x == "my half-written draft" then has_draft = true end
  end
  return has_new and has_draft
end, 50), "draft re-applied after external change")
local l = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
local idx
for i, x in ipairs(l) do if x == "## you · t5" then idx = i end end
ok(idx and l[idx + 2] == "my half-written draft", "draft placed under the new scaffold: " .. vim.inspect(l))
vim.bo[buf].modified = false

-- :AgentsFork -----------------------------------------------------------------------------------
vim.cmd("edit! " .. dir .. "/thread.md")
buf = vim.api.nvim_get_current_buf()
local ls = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
local sel1
for i, x in ipairs(ls) do if x == "echo: hello" then sel1 = i end end
vim.cmd(sel1 .. "," .. (sel1 + 1) .. "AgentsFork smoke-fork")
vim.cmd("stopinsert")
local cdir = dir .. "/smoke-fork"
local c = readf(cdir .. "/thread.md")
eq(c[1], "---", "fork frontmatter")
ok(vim.tbl_contains(c, "kind: fork"), "kind fork")
ok(vim.tbl_contains(c, "branched_at: t2"), "branched_at t2: " .. vim.inspect(c))
ok(vim.tbl_contains(c, "runtime: direct") and vim.tbl_contains(c, "model: null"), "parent fields copied")
local ci
for i, x in ipairs(c) do if x == "## carry" then ci = i end end
eq({ c[ci + 1], c[ci + 2] }, { "echo: hello", "" }, "carry has the selected lines verbatim")
eq(c[#c - 1], "## you · t1", "fork starts with you t1")

-- observed threads are read-only ---------------------------------------------------------------
local od = tmp .. "/threads/_observed/proj-abcd1234"
vim.fn.mkdir(od, "p")
vim.fn.writefile({ "---", "runtime: observed", "---" }, od .. "/thread.md")
write_status(od, "blocked")
vim.cmd("edit " .. od .. "/thread.md")
local obuf = vim.api.nvim_get_current_buf()
eq(vim.bo[obuf].modifiable, false, "observed buffer not modifiable")
errors = {}
vim.cmd("AgentsSend")
ok(#errors == 1, "send refused on observed")

-- :AgentsNext -----------------------------------------------------------------------------------
write_status(dir, "failed")
vim.fn.writefile({}, dir .. "/seen")
vim.cmd("AgentsNext")
local qf = vim.fn.getqflist()
ok(#qf >= 2, "AgentsNext lists threads: " .. #qf)
ok(vim.fn.bufname(qf[1].bufnr):find("proj%-abcd1234"), "blocked first")
ok(vim.fn.bufname(qf[2].bufnr):find("smoke/thread.md"), "failed second")
vim.cmd("AgentsBlocked")
eq(#vim.fn.getqflist(), 2, "AgentsBlocked lists blocked+failed")

-- :AgentsStop -----------------------------------------------------------------------------------
vim.cmd("edit " .. dir .. "/thread.md")
vim.cmd("AgentsStop")
ok(vim.fn.filereadable(dir .. "/STOP") == 1, "STOP created")

-- :AgentsGrep -----------------------------------------------------------------------------------
vim.fn.mkdir(tmp .. "/trial", "p")
agents.opts.grep_cmd = repo .. "/bin/agent-files-grep"
vim.cmd("AgentsGrep hello")
local gq = vim.fn.getqflist({ title = 1, size = 1 })
ok(gq.title == "AgentsGrep: hello" and gq.size >= 1, "AgentsGrep fills quickfix: " .. vim.inspect(gq))
ok(#readf(tmp .. "/trial/searches.log") == 1, "search logged")

-- display on the view fixture --------------------------------------------------------------------
vim.fn.mkdir(tmp .. "/threads/fixture", "p")
vim.fn.writefile(readf(repo .. "/md/docs/examples/view-fixture/thread.md"), tmp .. "/threads/fixture/thread.md")
write_status(tmp .. "/threads/fixture", "failed")
vim.cmd("edit " .. tmp .. "/threads/fixture/thread.md")
local fb = vim.api.nvim_get_current_buf()
vim.cmd("redraw")
local fl = vim.api.nvim_buf_get_lines(fb, 0, -1, false)
local groups = {}
for _, m in ipairs(vim.api.nvim_buf_get_extmarks(fb, D.ns, 0, -1, { details = true })) do
  groups[m[2] + 1] = m[4].hl_group
end
local function line_of(text, from) for i = from or 1, #fl do if fl[i] == text then return i end end end
eq(groups[line_of("## you · t1")], "AgentsYou", "you header hl")
eq(groups[line_of("## agent · t2")], "AgentsAgent", "agent header hl")
eq(groups[line_of("END (interrupted)")], "AgentsEndAbnormal", "END (interrupted) hl")
eq(groups[line_of("END (failed)")], "AgentsEndAbnormal", "END (failed) hl")
eq(groups[line_of("! error: daily spend cap reached ($5.00)")], "AgentsDiag", "diag hl")
eq(groups[line_of("▸ grep -rn refresh_token src/")], "AgentsTool", "tool hl")
local fake = line_of("## you · t99")
ok(fake and groups[fake] == nil, "fake marker inside fence is not highlighted")
local fakeend = line_of("END", line_of("```text"))
ok(fakeend and groups[fakeend] == nil, "END inside fence not highlighted")
ok(groups[line_of("\\END")] == nil, "escaped END not highlighted")
-- fold closed
local tool = line_of("▸ grep -rn refresh_token src/")
ok(vim.fn.foldclosed(tool) == tool, "tool fold is closed")
ok(vim.fn.foldclosedend(tool) > tool + 30, "fold covers the indented output")
-- end mark
local marks = vim.api.nvim_buf_get_extmarks(fb, D.ns_end, 0, -1, { details = true })
ok(#marks == 1, "one end mark")
local vt = marks[1] and marks[1][4].virt_text[1][1] or ""
ok(vt:find("✗") and vt:find("failed") and vt:find("~%d+k"), "end mark shows status and tokens: " .. vt)

-- helpers for the sections below ------------------------------------------------------------------
local function append(d, text) local h = io.open(d .. "/thread.md", "a"); h:write(text); h:close() end
local function buf_lines(b) return vim.api.nvim_buf_get_lines(b, 0, -1, false) end
local function count(ls, text) local k = 0; for _, x in ipairs(ls) do if x == text then k = k + 1 end end; return k end
local function has(b, text) return count(buf_lines(b), text) > 0 end

-- draft: text typed right after a send survives a streamed reply once ----------------------------
vim.cmd("AgentsNew draft-stream")
vim.cmd("stopinsert")
local sd = tmp .. "/threads/draft-stream"
local sb = vim.api.nvim_get_current_buf()
vim.api.nvim_buf_set_lines(sb, -1, -1, false, { "question" })
vim.cmd("AgentsSend")
vim.api.nvim_buf_set_lines(sb, -1, -1, false, { "", "my next thought" })
write_status(sd, "working")
local stream_ok, stream = true, { "\n## agent · t2\n", "line 1\n", "line 2\n", "line 3\n" }
for i, chunk in ipairs(stream) do
  append(sd, chunk)
  local want = i == 1 and "## agent · t2" or ("line " .. (i - 1))
  ok(vim.wait(3000, function() return has(sb, want) end, 20), "stream step " .. i .. " reloaded")
  local bl = buf_lines(sb)
  if count(bl, "## you · t1") ~= 1 or count(bl, want) ~= 1 or #bl ~= #readf(sd .. "/thread.md") + 2
     or bl[#bl] ~= "my next thought" then
    stream_ok = false
  end
end
ok(stream_ok, "while the reply streams the buffer is the file plus the draft, nothing duplicated: " .. #buf_lines(sb))
append(sd, "\nEND\n\n## you · t3\n\n")
write_status(sd, "done")
ok(vim.wait(3000, function() return has(sb, "## you · t3") and vim.bo[sb].modifiable end, 20), "reply finished")
local want_sb = readf(sd .. "/thread.md")
want_sb[#want_sb + 1] = "my next thought"
eq(buf_lines(sb), want_sb, "draft once, under the new scaffold")
vim.bo[sb].modified = false

-- draft: a partly saved turn, sent from outside, does not duplicate the saved part ----------------
vim.cmd("AgentsNew draft-partial")
vim.cmd("stopinsert")
local pd = tmp .. "/threads/draft-partial"
local pb = vim.api.nvim_get_current_buf()
vim.api.nvim_buf_set_lines(pb, -1, -1, false, { "saved part" })
vim.cmd("silent write")
vim.api.nvim_buf_set_lines(pb, -1, -1, false, { "unsaved part" })
append(pd, "END\n")
ok(vim.wait(3000, function() return has(pb, "END") end, 20), "partial: reloaded")
local pl = buf_lines(pb)
eq(vim.list_slice(pl, #pl - 4), { "", "saved part", "END", "", "unsaved part" }, "partial: only the unsaved text is re-applied")

-- draft: an unsaved edit above the last END is kept in place when the file grows ------------------
vim.cmd("silent edit!")
local el
for i, x in ipairs(buf_lines(pb)) do if x == "saved part" then el = i end end
vim.api.nvim_buf_set_lines(pb, el - 1, el, false, { "saved part, edited" })
append(pd, "\n## agent · t2\nreply\nEND\n")
ok(vim.wait(3000, function() return has(pb, "reply") end, 20), "mid edit: reloaded")
pl = buf_lines(pb)
ok(pl[el] == "saved part, edited" and count(pl, "saved part") == 0 and count(pl, "reply") == 1, "mid edit kept in place: " .. vim.inspect(pl))
ok(vim.bo[pb].modified, "mid edit: buffer still modified")
vim.bo[pb].modified = false

-- a stale 'working' (no status write for 10 min: the runner died) does not lock the buffer -------
local St = require("agents.status")
vim.cmd("edit " .. sd .. "/thread.md")
write_status(sd, "working")
ok(vim.wait(3000, function() return not vim.bo[sb].modifiable end, 20), "stale: locked while working")
local long_ago = os.time() - 660
vim.uv.fs_utime(sd .. "/status", long_ago, long_ago)
ok(vim.wait(3000, function() return vim.bo[sb].modifiable and not vim.bo[sb].readonly end, 20), "stale: writable again")
local frame0 = St.frame
vim.wait(400, function() return false end)
eq(St.frame, frame0, "stale: spinner stopped")
ok(vim.bo[sb].modifiable and not vim.bo[sb].readonly, "stale: still writable after 400 ms")
ok(agents.status(sb):find("? stale", 1, true), "stale: status line says stale: " .. agents.status(sb))
local smark = vim.api.nvim_buf_get_extmarks(sb, D.ns_end, 0, -1, { details = true })[1]
ok(smark and smark[4].virt_text[1][1]:find("? stale", 1, true), "stale: end mark says stale")
write_status(sd, "done")

-- window settings: local to the thread in its window, set once -----------------------------------
local function wopts() return { vim.wo.foldmethod, vim.wo.conceallevel, vim.wo.linebreak } end
local other = tmp .. "/other.md"
vim.fn.writefile({ "# notes", "", "text" }, other)
eq({ vim.go.foldmethod, vim.go.conceallevel, vim.go.linebreak }, { "manual", 0, false }, "window: no global value set")
vim.cmd("edit " .. tmp .. "/threads/fixture/thread.md")
eq(wopts(), { "expr", 2, true }, "window: thread settings in the thread's window")
vim.cmd("redraw")
vim.api.nvim_win_set_cursor(0, { tool, 0 })
vim.cmd("normal! zo")
ok(vim.fn.foldclosed(tool) == -1, "window: fold opened")
vim.cmd("doautocmd FocusGained")
vim.cmd("vnew " .. other)
eq(wopts(), { "manual", 0, false }, "window: a new window on another file keeps its defaults")
vim.cmd("wincmd p")
vim.cmd("redraw")
ok(vim.fn.foldclosed(tool) == -1, "window: an opened fold stays open after FocusGained and a window switch")
vim.cmd("edit " .. other)
eq(wopts(), { "manual", 0, false }, "window: another file in the thread's window keeps its defaults")
vim.cmd("only")

-- seen: viewing a finished thread writes seen once, with no watcher loop --------------------------
local function mt(p) local st = vim.uv.fs_stat(p); return st and { st.mtime.sec, st.mtime.nsec } end
local function newer_or_same(x, y) return x[1] > y[1] or (x[1] == y[1] and x[2] >= y[2]) end
vim.cmd("edit " .. sd .. "/thread.md")
write_status(sd, "done")
ok(vim.wait(3000, function()
  local s, t = mt(sd .. "/seen"), mt(sd .. "/status")
  return s and t and newer_or_same(s, t)
end, 20), "seen: touched after the turn finished")
vim.wait(300, function() return false end)
local seen0, applies, orig_apply = mt(sd .. "/seen"), 0, D.apply
D.apply = function(...) applies = applies + 1; return orig_apply(...) end
vim.wait(1500, function() return false end)
D.apply = orig_apply
eq(mt(sd .. "/seen"), seen0, "seen: not rewritten while nothing changes")
ok(applies <= 1, "seen: no reload loop (" .. applies .. " redraws in 1.5 s)")

-- a reply streaming a line every 20-50 ms reloads live, and the lock lands during it --------------
vim.cmd("AgentsNew fast-stream")
vim.cmd("stopinsert")
local fsd = tmp .. "/threads/fast-stream"
local fsb = vim.api.nvim_get_current_buf()
vim.api.nvim_buf_set_lines(fsb, -1, -1, false, { "go" })
vim.cmd("AgentsSend")
write_status(fsd, "working")
append(fsd, "\n## agent · t2\n")
local written, total, writer = 0, 50, vim.uv.new_timer()
local function write_line()
  written = written + 1
  append(fsd, "line " .. written .. "\n")
  if written < total then writer:start(20 + (written % 4) * 10, 0, write_line) end
end
writer:start(20, 0, write_line)
local sizes, nsizes, locked = {}, 0, false
vim.wait(6000, function()
  if written < total then
    local n = #buf_lines(fsb)
    if not sizes[n] then sizes[n], nsizes = true, nsizes + 1 end
    if not vim.bo[fsb].modifiable then locked = true end
  end
  return written >= total
end, 10)
writer:close()
ok(nsizes >= 4, "fast stream: the buffer reloads while the reply streams (" .. nsizes .. " sizes seen)")
ok(locked, "fast stream: read-only during the stream")
append(fsd, "\nEND\n\n## you · t3\n\n")
write_status(fsd, "done")
ok(vim.wait(3000, function() return has(fsb, "## you · t3") and vim.bo[fsb].modifiable end, 20), "fast stream: finished")
eq(buf_lines(fsb), readf(fsd .. "/thread.md"), "fast stream: buffer matches the file")

-- agents.term: capture and send, with the send policy (ARCHITECTURE §11.2) -----------------------
local Term = require("agents.term")
Term.opts.policy.cat = "human" -- treat `cat` as a harness that takes only human-written text
local function open_term(cmd)
  vim.cmd("enew")
  vim.fn.jobstart(cmd, { term = true })
  return vim.api.nvim_get_current_buf()
end
local function screen_has(b, s)
  for _, l in ipairs(vim.api.nvim_buf_get_lines(b, 0, -1, false)) do if l:find(s, 1, true) then return true end end
  return false
end
local tb = open_term({ "cat" })
local listed = nil
for _, t in ipairs(Term.list()) do if t.buf == tb then listed = t end end
ok(listed and listed.harness == "cat" and listed.policy == "human" and listed.running, "term: list finds the harness " .. vim.inspect(listed))
local t1, e1 = Term.send("cat", "from an agent", "agent")
ok(t1 == nil and e1:find("human%-written"), "term: agent send refused by policy: " .. tostring(e1))
ok(Term.send(tostring(tb), "typed by you", "human"), "term: human send accepted")
ok(vim.wait(3000, function() return screen_has(tb, "typed by you") end, 20), "term: sent text reaches the terminal")
local cap = Term.capture(tb)
ok(cap and screen_has(tb, "typed by you") and cap[#cap]:match("%S"), "term: capture drops trailing blank lines")
eq(#Term.capture(tb, 1), 1, "term: capture -n keeps the last lines")
local reply = vim.json.decode(Term.rpc(vim.json.encode({ op = "send", target = tb, text = "x" })))
ok(reply.ok == false and reply.error:find("human%-written"), "term: rpc sends are agent sends: " .. vim.inspect(reply))
vim.b[tb].agents_send = "any"
ok(Term.send(tb, "allowed now", "agent"), "term: b:agents_send = 'any' lets agents send")
ok(vim.wait(3000, function() return screen_has(tb, "allowed now") end, 20), "term: agent text arrives")
vim.b[tb].agents_send = "anyy"
eq(Term.resolve(tb).policy, "human", "term: a mistyped override fails closed")
vim.b[tb].agents_send = nil
local tb2 = open_term({ "cat" })
local amb, ae = Term.resolve("cat")
ok(amb == nil and ae:find("give a buffer number"), "term: ambiguous target refused: " .. tostring(ae))
eq(Term.resolve(tb2).buf, tb2, "term: buffer number resolves")
local sh = open_term({ "sh" })
eq(Term.resolve(sh).policy, "any", "term: a plain shell takes agent text")
ok(Term.send(sh, "echo one\necho two", "agent"), "term: multi-line send to a shell")
ok(vim.wait(3000, function() return screen_has(sh, "two") end, 20), "term: shell ran both lines")
ok(select(2, Term.send(99999, "x", "human")):find("no terminal buffer"), "term: unknown buffer refused")
-- the Ex commands: the unnamed register, then a range from another buffer
vim.fn.setreg('"', "echo via-$((40+2))")
vim.cmd("AgentsTermSend " .. sh)
ok(vim.wait(3000, function() return screen_has(sh, "via-42") end, 20), "term: :AgentsTermSend sends the register")
vim.cmd("enew")
vim.api.nvim_buf_set_lines(0, 0, -1, false, { "echo range-$((1+1))" })
vim.cmd("1AgentsTermSend " .. sh)
ok(vim.wait(3000, function() return screen_has(sh, "range-2") end, 20), "term: :AgentsTermSend sends a range")
ok(vim.fn.exists(":AgentsTermSend") == 2 and vim.fn.exists(":AgentsTermCapture") == 2 and vim.fn.exists(":AgentsTerms") == 2, "term: commands defined")
for _, b in ipairs({ tb, tb2, sh }) do pcall(vim.fn.jobstop, vim.bo[b].channel) end

print(("%d checks, %d failed"):format(n, fails))
vim.fn.delete(tmp, "rf")
os.exit(fails == 0 and 0 or 1)
