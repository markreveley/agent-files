-- agents.nvim — thread buffers, watching, marks, commands (docs/m1-build-spec.md §9).
local T = require("agents.thread")
local S = require("agents.status")
local D = require("agents.display")
local uv = vim.uv or vim.loop

local M = {}
M.opts = { root = nil, tabline = false, grep_cmd = "agent-files-grep" }
M.attached = {}   -- bufnr -> { dir=, watcher=, timer=, observed= }

local group = vim.api.nvim_create_augroup("AgentsNvim", { clear = true })

local function root()
  local r = os.getenv("AGENT_FILES_ROOT")
  if r == nil or r == "" then r = M.opts.root or "~/agent-files" end
  return (vim.fn.fnamemodify(vim.fn.expand(r), ":p"):gsub("/$", ""))
end
M.root = root

local function thread_info(path)
  -- returns dir, observed(bool) when `path` is <root>/threads/**/thread.md
  local prefix = root() .. "/threads/"
  path = vim.fn.resolve(vim.fn.fnamemodify(path, ":p"))
  local rprefix = vim.fn.resolve(root()) .. "/threads/"
  for _, pre in ipairs({ prefix, rprefix }) do
    if path:sub(1, #pre) == pre and path:match("/thread%.md$") then
      local rel = path:sub(#pre + 1)
      return (path:gsub("/thread%.md$", "")), rel:sub(1, 9) == "_observed"
    end
  end
  return nil
end

local function bufdir(buf)
  local a = M.attached[buf]
  return a and a.dir
end

local function lines_of(buf) return vim.api.nvim_buf_get_lines(buf, 0, -1, false) end

local function any_working()
  for b, a in pairs(M.attached) do
    if vim.api.nvim_buf_is_valid(b) then
      local info = S.read(a.dir)
      if info.status == "working" then return true end
    end
  end
  return false
end

-- spinner ---------------------------------------------------------------------------------------
local spin
local function refresh_buf(buf)
  local a = M.attached[buf]
  if not a or not vim.api.nvim_buf_is_valid(buf) then return end
  local info = S.read(a.dir)
  a.info = info
  local working = info.status == "working"
  if not a.observed then
    local want = not working
    if vim.bo[buf].modifiable ~= want then vim.bo[buf].modifiable = want end
    if vim.bo[buf].readonly == want then vim.bo[buf].readonly = not want end
  end
  D.endmark(buf, nil, nil, info)
end

local function spin_check()
  if any_working() then
    if not spin then
      spin = uv.new_timer()
      spin:start(120, 120, vim.schedule_wrap(function()
        S.advance()
        for b in pairs(M.attached) do refresh_buf(b) end
        vim.cmd("redrawtabline")
        if not any_working() and spin then spin:stop(); spin:close(); spin = nil end
      end))
    end
  elseif spin then
    spin:stop(); spin:close(); spin = nil
  end
end

-- status line / tabline -------------------------------------------------------------------------
function M.status(buf)
  buf = buf or vim.api.nvim_get_current_buf()
  local a = M.attached[buf]
  if not a then return "" end
  local glyph, _, word = S.mark(S.read(a.dir))
  local name = vim.fn.fnamemodify(a.dir, ":t")
  local parts = { name }
  if glyph ~= "" then parts[#parts + 1] = glyph end
  if word ~= "" and word ~= "idle" then parts[#parts + 1] = word end
  parts[#parts + 1] = "~" .. S.tokens(lines_of(buf)) .. "k"
  return table.concat(parts, " ")
end

function M.tabline()
  local out = {}
  local cur = vim.api.nvim_get_current_buf()
  for b in pairs(M.attached) do
    if vim.api.nvim_buf_is_valid(b) then
      out[#out + 1] = (b == cur and "%#TabLineSel# " or "%#TabLine# ") .. M.status(b):gsub("%%", "%%%%") .. " "
    end
  end
  return table.concat(out) .. "%#TabLineFill#"
end

-- seen ------------------------------------------------------------------------------------------
local function touch_seen(buf)
  local a = M.attached[buf]
  if a and not a.observed and vim.api.nvim_get_current_buf() == buf then
    S.touch_seen(a.dir)
    refresh_buf(buf)
  end
end

-- draft re-apply --------------------------------------------------------------------------------
local function capture_draft(buf)
  if not vim.bo[buf].modified then return nil end
  local lines = lines_of(buf)
  local p = T.parse(lines)
  local last = T.last(p)
  local draft = {}
  if last and last.role == "you" and last.closed == "none" then
    for n = last.header + 1, #lines do draft[#draft + 1] = lines[n] end
  else
    local from = 1
    if last and last.end_line then from = last.end_line + 1 end
    for n = from, #lines do draft[#draft + 1] = lines[n] end
  end
  while #draft > 0 and not draft[#draft]:match("%S") do draft[#draft] = nil end
  while #draft > 0 and not draft[1]:match("%S") do table.remove(draft, 1) end
  if #draft == 0 then return nil end
  return draft
end

local function reapply_draft(buf, draft)
  local lines = lines_of(buf)
  local p = T.parse(lines)
  local last = T.last(p)
  local was = vim.bo[buf].modifiable
  vim.bo[buf].modifiable = true
  if last and last.role == "you" and last.closed == "none" and last.empty then
    local new = { "" }
    vim.list_extend(new, draft)
    vim.api.nvim_buf_set_lines(buf, last.header, -1, false, new)
  else
    local new = { "" }
    vim.list_extend(new, draft)
    vim.api.nvim_buf_set_lines(buf, #lines, #lines, false, new)
  end
  vim.bo[buf].modifiable = was
  vim.notify("agents: draft re-applied", vim.log.levels.INFO)
end

-- attach ----------------------------------------------------------------------------------------
local function detach(buf)
  local a = M.attached[buf]
  if not a then return end
  if a.watcher then a.watcher:stop(); if not a.watcher:is_closing() then a.watcher:close() end end
  if a.timer then a.timer:stop(); if not a.timer:is_closing() then a.timer:close() end end
  M.attached[buf] = nil
  spin_check()
end

local function on_fs_event(buf)
  local a = M.attached[buf]
  if not a or not vim.api.nvim_buf_is_valid(buf) then return end
  local was_modifiable = vim.bo[buf].modifiable
  -- reload needs a modifiable buffer
  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_call(buf, function() vim.cmd("silent! checktime " .. buf) end)
  refresh_buf(buf)
  D.apply(buf, a.info)
  if vim.api.nvim_get_current_buf() == buf and vim.api.nvim_get_current_win() and vim.api.nvim_win_get_buf(0) == buf then
    local info = a.info or {}
    if info.status == "done" or info.status == "interrupted" or info.status == "failed" then touch_seen(buf) end
  end
  spin_check()
end

function M.attach(buf)
  if M.attached[buf] then return end
  local path = vim.api.nvim_buf_get_name(buf)
  local dir, observed = thread_info(path)
  if not dir then return end
  local a = { dir = dir, observed = observed }
  M.attached[buf] = a
  vim.bo[buf].autoread = true
  if observed then
    vim.bo[buf].modifiable = false
    vim.bo[buf].readonly = true
  end
  D.define_highlights()
  local w = uv.new_fs_event()
  local timer = uv.new_timer()
  a.watcher, a.timer = w, timer
  w:start(dir, {}, function()
    timer:stop()
    timer:start(100, 0, vim.schedule_wrap(function() on_fs_event(buf) end))
  end)
  vim.api.nvim_create_autocmd("BufWipeout", { group = group, buffer = buf, callback = function() detach(buf) end })
  vim.api.nvim_create_autocmd("FileChangedShell", { group = group, buffer = buf, callback = function()
    a.draft = capture_draft(buf)
    vim.bo[buf].modifiable = true
    vim.v.fcs_choice = "reload"
  end })
  vim.api.nvim_create_autocmd("FileChangedShellPost", { group = group, buffer = buf, callback = function()
    if a.draft then
      local d = a.draft
      a.draft = nil
      vim.schedule(function() reapply_draft(buf, d) end)
    end
    vim.schedule(function() refresh_buf(buf); D.apply(buf, a.info) end)
  end })
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, { group = group, buffer = buf, callback = function()
    D.apply(buf, a.info)
  end })
  vim.api.nvim_create_autocmd({ "BufEnter", "FocusGained" }, { group = group, buffer = buf, callback = function()
    D.setup_window()
    touch_seen(buf)
  end })
  D.setup_window()
  refresh_buf(buf)
  D.apply(buf, a.info)
  touch_seen(buf)
  spin_check()
end

-- commands --------------------------------------------------------------------------------------
local function err(msg) vim.notify("agents: " .. msg, vim.log.levels.ERROR) end

local function current()
  local buf = vim.api.nvim_get_current_buf()
  local a = M.attached[buf]
  if not a then err("not a thread buffer"); return nil end
  return buf, a
end

local function writable(buf, a)
  if a.observed then err("observed threads are read-only"); return false end
  return true
end

function M.send()
  local buf, a = current()
  if not buf or not writable(buf, a) then return end
  local info = S.read(a.dir)
  if info.status == "working" then return err("thread is working") end
  local lines = lines_of(buf)
  local p = T.parse(lines)
  local last = T.last(p)
  if not last or last.role ~= "you" or last.closed ~= "none" then
    return err("the last section is not an open '## you' turn")
  end
  if last.fence_open then return err("your turn leaves a code fence open; END inside a fence is not a send") end
  if last.empty then return err("your turn is empty") end
  while #lines > 0 and not lines[#lines]:match("%S") do lines[#lines] = nil end
  lines[#lines + 1] = "END"
  vim.bo[buf].modifiable = true
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  vim.cmd("silent write")
  D.apply(buf, info)
end

function M.stop()
  local buf, a = current()
  if not buf or not writable(buf, a) then return end
  local f = io.open(a.dir .. "/STOP", "w")
  if f then f:close() end
end

local SLUG = "^[a-z0-9._-]+$"

local function frontmatter(fields)
  local out = { "---" }
  for _, kv in ipairs(fields) do out[#out + 1] = kv[1] .. ": " .. kv[2] end
  out[#out + 1] = "---"
  return out
end

local function create_and_open(dir, lines, cursor_line)
  if uv.fs_stat(dir .. "/thread.md") then return err("already exists: " .. dir) end
  vim.fn.mkdir(dir, "p")
  vim.fn.writefile(lines, dir .. "/thread.md")
  vim.cmd("edit " .. vim.fn.fnameescape(dir .. "/thread.md"))
  vim.api.nvim_win_set_cursor(0, { cursor_line or #lines, 0 })
  vim.cmd("startinsert")
end

function M.new(slug)
  if not slug or not slug:match(SLUG) then return err("slug must match [a-z0-9._-]+") end
  local lines = frontmatter({ { "agent", "default" }, { "runtime", "direct" }, { "model", "null" },
    { "context", "replay" }, { "kind", "main" } })
  vim.list_extend(lines, { "", "## you · t1", "" })
  create_and_open(root() .. "/threads/" .. slug, lines, #lines)
end

local function fm_value(lines, key)
  local p = T.parse(lines)
  for n = 2, (p.fm_end > 0 and p.fm_end - 1 or 0) do
    local v = lines[n]:match("^" .. key .. ":%s*(.*)$")
    if v then return v end
  end
  return nil
end

local function escape_carry(l)
  if l:match("^\\*## carry") or l:match("^\\*## you") or l:match("^\\*## agent") or l:match("^\\*## note")
     or l:match("^\\*END") or l:match("^\\*! ") then
    return "\\" .. l
  end
  return l
end

function M.fork(slug, l1, l2)
  local buf, a = current()
  if not buf or not writable(buf, a) then return end
  if not slug or not slug:match(SLUG) then return err("slug must match [a-z0-9._-]+") end
  local lines = lines_of(buf)
  local p = T.parse(lines)
  local sel, branched
  if l1 and l2 and l1 > 0 then
    sel = vim.list_slice(lines, l1, l2)
    for _, t in ipairs(p.turns) do
      if t.header <= l1 and l1 <= t.last_line then branched = "t" .. t.id end
    end
    branched = branched or (T.last(p) and ("t" .. T.last(p).id)) or "null"
  else
    local last = T.last(p)
    if not last then return err("nothing to fork from") end
    sel = vim.list_slice(lines, last.header + 1, last.end_line and last.end_line - 1 or last.last_line)
    branched = "t" .. last.id
  end
  local carry, fences = {}, 0
  for _, l in ipairs(sel) do
    if T.is_fence(l) then fences = fences + 1 end
    carry[#carry + 1] = escape_carry(l)
  end
  if fences % 2 == 1 then carry[#carry + 1] = "```" end
  local fields = {}
  for _, k in ipairs({ "agent", "runtime", "model", "context", "grounding" }) do
    local v = fm_value(lines, k)
    if v then fields[#fields + 1] = { k, v } end
  end
  fields[#fields + 1] = { "kind", "fork" }
  fields[#fields + 1] = { "branched_at", branched }
  local out = frontmatter(fields)
  vim.list_extend(out, { "", "## carry" })
  vim.list_extend(out, carry)
  vim.list_extend(out, { "", "## you · t1", "" })
  create_and_open(a.dir .. "/" .. slug, out, #out)
end

local ORDER = { blocked = 1, failed = 2, unseen = 3, stale = 4 }

local function scan(only_blocked)
  local items = {}
  local base = root() .. "/threads"
  local function walk(dir)
    local h = uv.fs_scandir(dir)
    if not h then return end
    while true do
      local name, typ = uv.fs_scandir_next(h)
      if not name then break end
      if typ == "directory" and name ~= "steps" and name ~= "out" then
        local d = dir .. "/" .. name
        if uv.fs_stat(d .. "/thread.md") then
          local info = S.read(d)
          local glyph, _, word = S.mark(info)
          local cat
          if info.status == "blocked" then cat = "blocked"
          elseif info.status == "failed" then cat = "failed"
          elseif word == "stale" then cat = "stale"
          elseif word == "done" or word == "interrupted" then cat = "unseen" end
          if cat and (not only_blocked or cat == "blocked" or cat == "failed") then
            local observed = d:find("/_observed/", 1, true) ~= nil
            local lnum = 1
            if not observed then
              local ok, ls = pcall(vim.fn.readfile, d .. "/thread.md")
              if ok then
                local p = T.parse(ls)
                local last = T.last(p)
                lnum = last and last.header or 1
              end
            end
            items[#items + 1] = { cat = cat, filename = d .. "/thread.md", lnum = lnum,
              text = (word ~= "" and word or cat) .. " " .. glyph }
          end
        end
        walk(d)
      end
    end
  end
  walk(base)
  table.sort(items, function(x, y)
    if ORDER[x.cat] ~= ORDER[y.cat] then return ORDER[x.cat] < ORDER[y.cat] end
    return x.filename < y.filename
  end)
  return items
end

function M.next(only_blocked)
  local items = scan(only_blocked)
  local qf = {}
  for _, it in ipairs(items) do qf[#qf + 1] = { filename = it.filename, lnum = it.lnum, text = it.text } end
  vim.fn.setqflist({}, " ", { title = only_blocked and "AgentsBlocked" or "AgentsNext", items = qf })
  if #qf == 0 then
    vim.notify("agents: nothing needs you", vim.log.levels.INFO)
    return
  end
  vim.cmd("cfirst")
end

function M.grep(pattern)
  if not pattern or pattern == "" then return err("usage: :AgentsGrep <pattern>") end
  local out = vim.fn.systemlist({ M.opts.grep_cmd, pattern })
  vim.fn.setqflist({}, " ", { title = "AgentsGrep: " .. pattern, lines = out, efm = "%f:%l:%c:%m" })
  if #out > 0 then vim.cmd("cfirst") else vim.notify("agents: no matches", vim.log.levels.INFO) end
end

function M.setup(opts)
  M.opts = vim.tbl_extend("force", M.opts, opts or {})
  D.define_highlights()
  vim.api.nvim_create_autocmd({ "BufReadPost", "BufNewFile", "BufEnter" }, {
    group = group, pattern = "*/thread.md", callback = function(ev) M.attach(ev.buf) end,
  })
  for _, b in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(b) and vim.api.nvim_buf_get_name(b):match("/thread%.md$") then M.attach(b) end
  end
  vim.api.nvim_create_user_command("AgentsSend", function() M.send() end, {})
  vim.api.nvim_create_user_command("AgentsStop", function() M.stop() end, {})
  vim.api.nvim_create_user_command("AgentsNew", function(c) M.new(c.args) end, { nargs = 1 })
  vim.api.nvim_create_user_command("AgentsFork", function(c)
    if c.range > 0 then M.fork(c.args, c.line1, c.line2) else M.fork(c.args) end
  end, { nargs = 1, range = true })
  vim.api.nvim_create_user_command("AgentsNext", function() M.next(false) end, {})
  vim.api.nvim_create_user_command("AgentsBlocked", function() M.next(true) end, {})
  vim.api.nvim_create_user_command("AgentsGrep", function(c) M.grep(c.args) end, { nargs = "+" })
  if M.opts.tabline then
    vim.o.showtabline = 2
    vim.o.tabline = "%!v:lua.require'agents'.tabline()"
  end
end

return M
