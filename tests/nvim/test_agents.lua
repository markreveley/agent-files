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
vim.fn.writefile(readf(repo .. "/docs/examples/view-fixture/thread.md"), tmp .. "/threads/fixture/thread.md")
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

print(("%d checks, %d failed"):format(n, fails))
vim.fn.delete(tmp, "rf")
os.exit(fails == 0 and 0 or 1)
