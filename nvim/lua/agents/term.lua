-- agents.term — read from and type into terminal buffers in this Neovim (ARCHITECTURE §11.2).
-- An operator convenience for harness TUIs started in Neovim's :terminal. It is not part of the
-- thread system: threads still talk only through files (principle 8).
--
-- Sends come from :AgentsTermSend or over the socket (agent-files-term, rpc() below); both type
-- the text in the same way.
local M = {}
M.opts = {
  harnesses = { "claude", "codex" }, -- process names listed as a terminal's harness
  enter_delay = 80,  -- ms between a paste and its Enter, so a TUI sees two events
}

local function is_harness(name)
  return name ~= nil and vim.tbl_contains(M.opts.harnesses, name)
end

local function basename(s) return (s or ""):match("([^/%s]+)%s*$") or s end

-- the first process in the job's tree (the job, then its descendants) named in `harnesses`
local function harness_of(pid)
  local queue, seen, i = { pid }, {}, 1
  while queue[i] and i < 200 do
    local p = queue[i]
    i = i + 1
    if not seen[p] then
      seen[p] = true
      local ok, info = pcall(vim.api.nvim_get_proc, p)
      local name = ok and info and basename(info.name)
      if is_harness(name) then return name end
      local ok2, kids = pcall(vim.api.nvim_get_proc_children, p)
      if ok2 then vim.list_extend(queue, kids) end
    end
  end
  return nil
end

local function describe(buf)
  local name = vim.api.nvim_buf_get_name(buf)
  local cwd, cmd = name:match("^term://(.-)//%d+:(.*)$")
  local chan = vim.bo[buf].channel
  local pid = vim.b[buf].terminal_job_pid
  local running = chan > 0 and vim.fn.jobwait({ chan }, 0)[1] == -1
  local harness = running and pid and harness_of(pid) or nil
  if not harness and cmd then
    local first = basename(cmd:match("^(%S+)"))
    if is_harness(first) then harness = first end
  end
  return {
    buf = buf, chan = chan, pid = pid, running = running, harness = harness,
    cwd = cwd, cmd = cmd, title = vim.b[buf].term_title,
  }
end

function M.list()
  local out = {}
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].buftype == "terminal" then
      out[#out + 1] = describe(buf)
    end
  end
  return out
end

-- target: a buffer number, or a string matching one terminal's buffer number, harness, command,
-- directory or title. Returns the terminal, or nil and an error.
function M.resolve(target)
  local terms = M.list()
  local n = tonumber(target)
  if n then
    for _, t in ipairs(terms) do if t.buf == n then return t end end
    return nil, "no terminal buffer " .. n
  end
  if type(target) ~= "string" or target == "" then return nil, "no target given" end
  local exact, partial = {}, {}
  for _, t in ipairs(terms) do
    if t.harness == target then exact[#exact + 1] = t end
    for _, f in ipairs({ t.cmd, t.cwd, t.title }) do
      if f and f:find(target, 1, true) then partial[#partial + 1] = t; break end
    end
  end
  local hits = #exact > 0 and exact or partial
  if #hits == 1 then return hits[1] end
  if #hits == 0 then return nil, "no terminal matches '" .. target .. "'" end
  local bufs = {}
  for _, t in ipairs(hits) do bufs[#bufs + 1] = tostring(t.buf) end
  return nil, "'" .. target .. "' matches terminals " .. table.concat(bufs, ", ") .. "; give a buffer number"
end

-- the terminal's screen and scrollback, trailing blank lines dropped; the last `n` lines if given
function M.capture(target, n)
  local t, e = M.resolve(target)
  if not t then return nil, e end
  local lines = vim.api.nvim_buf_get_lines(t.buf, 0, -1, false)
  while #lines > 0 and not lines[#lines]:match("%S") do lines[#lines] = nil end
  n = tonumber(n)
  if n and n > 0 and #lines > n then lines = vim.list_slice(lines, #lines - n + 1, #lines) end
  return lines, t
end

-- opts.enter (default true) presses Enter after the text.
function M.send(target, text, opts)
  opts = opts or {}
  local t, e = M.resolve(target)
  if not t then return nil, e end
  if not t.running then return nil, "terminal " .. t.buf .. " has no running job" end
  text = (text or ""):gsub("\r\n", "\n"):gsub("\n+$", "")
  if text:find("\n", 1, true) then
    -- a harness TUI reads a bracketed paste as one message; a shell gets one command per line
    if t.harness then text = "\27[200~" .. text .. "\27[201~" else text = text:gsub("\n", "\r") end
  end
  vim.api.nvim_chan_send(t.chan, text)
  if opts.enter ~= false then
    if text == "" then
      vim.api.nvim_chan_send(t.chan, "\r")
    else
      vim.defer_fn(function() pcall(vim.api.nvim_chan_send, t.chan, "\r") end, M.opts.enter_delay)
    end
  end
  return t
end

-- Socket entry point for agent-files-term: one JSON request in, one JSON reply out.
function M.rpc(req)
  local ok, r = pcall(vim.json.decode, req)
  if not ok or type(r) ~= "table" then return vim.json.encode({ ok = false, error = "bad request" }) end
  local function reply(v, e, extra)
    if not v then return vim.json.encode({ ok = false, error = e }) end
    return vim.json.encode(vim.tbl_extend("force", { ok = true }, extra or {}))
  end
  if r.op == "ls" then
    local out = {}
    for _, t in ipairs(M.list()) do
      out[#out + 1] = { buf = t.buf, harness = t.harness or vim.NIL, running = t.running,
        cwd = t.cwd or vim.NIL, cmd = t.cmd or vim.NIL, title = t.title or vim.NIL }
    end
    return reply(true, nil, { terminals = out })
  elseif r.op == "capture" then
    local lines, t = M.capture(r.target, r.lines)
    return reply(lines, t, lines and { buf = t.buf, text = table.concat(lines, "\n") })
  elseif r.op == "send" then
    if type(r.text) ~= "string" then return reply(nil, "send needs text") end
    local t, e = M.send(r.target, r.text, { enter = r.enter ~= false })
    return reply(t, e, t and { buf = t.buf })
  end
  return reply(nil, "unknown op '" .. tostring(r.op) .. "'")
end

-- commands --------------------------------------------------------------------------------------
local function err(msg) vim.notify("agents: " .. msg, vim.log.levels.ERROR) end

local function complete()
  local out = {}
  for _, t in ipairs(M.list()) do
    out[#out + 1] = tostring(t.buf)
    if t.harness then out[#out + 1] = t.harness end
  end
  return out
end

function M.setup(opts)
  if opts then
    M.opts = vim.tbl_deep_extend("force", M.opts, opts)
  end
  vim.api.nvim_create_user_command("AgentsTerms", function()
    local chunks = {}
    for _, t in ipairs(M.list()) do
      chunks[#chunks + 1] = { ("%3d  %-8s %s%s\n"):format(t.buf, t.harness or "-",
        t.cmd or "?", t.running and "" or "  (exited)") }
    end
    if #chunks == 0 then chunks = { { "agents: no terminal buffers" } } end
    vim.api.nvim_echo(chunks, false, {})
  end, {})
  -- :[range]AgentsTermSend[!] {target}: the lines in range, else the unnamed register. ! leaves
  -- out the Enter. No register argument: Neovim would read the target's first letter as one.
  vim.api.nvim_create_user_command("AgentsTermSend", function(c)
    local text
    if c.range > 0 then
      text = table.concat(vim.api.nvim_buf_get_lines(0, c.line1 - 1, c.line2, false), "\n")
    else
      text = vim.fn.getreg('"')
    end
    if text == "" then return err("nothing to send") end
    local t, e = M.send(c.args, text, { enter = not c.bang })
    if not t then err(e) end
  end, { nargs = 1, range = true, bang = true, complete = complete })
  -- :AgentsTermCapture {target} [lines]: a scratch buffer with the terminal's text
  vim.api.nvim_create_user_command("AgentsTermCapture", function(c)
    local target, n = c.fargs[1], c.fargs[2]
    local lines, t = M.capture(target, n)
    if not lines then return err(t) end
    vim.cmd("new")
    local b = vim.api.nvim_get_current_buf()
    vim.bo[b].buftype, vim.bo[b].bufhidden, vim.bo[b].swapfile = "nofile", "wipe", false
    vim.api.nvim_buf_set_lines(b, 0, -1, false, lines)
    pcall(vim.api.nvim_buf_set_name, b, ("agents-capture://%d"):format(t.buf))
    vim.cmd("normal! G")
  end, { nargs = "+", complete = complete })
end

return M
