-- status / seen sidecars, marks, token estimate.
local M = {}
local uv = vim.uv or vim.loop

local FRAMES = { "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏" }
M.frame = 1
M.STALE_SECS = 600

local function mtime(path)
  local st = uv.fs_stat(path)
  return st and st.mtime.sec + st.mtime.nsec / 1e9 or nil
end

function M.read(dir)
  local f = io.open(dir .. "/status", "r")
  local status
  if f then
    status = (f:read("*a") or ""):gsub("%s+$", "")
    f:close()
    if status == "" then status = nil end
  end
  return { status = status, status_mtime = mtime(dir .. "/status"), seen_mtime = mtime(dir .. "/seen") }
end

--- Returns glyph, highlight group, word ("" = idle).
function M.mark(info, now)
  now = now or os.time()
  local st = info.status
  if not st then return "", nil, "" end
  if st == "working" then
    if info.status_mtime and now - info.status_mtime >= M.STALE_SECS then return "?", "WarningMsg", "stale" end
    return FRAMES[M.frame], "DiagnosticInfo", "working"
  elseif st == "blocked" then
    return "●", "ErrorMsg", "blocked"
  elseif st == "failed" then
    return "✗", "ErrorMsg", "failed"
  elseif st == "done" or st == "interrupted" then
    local unseen = not info.seen_mtime or (info.status_mtime and info.status_mtime > info.seen_mtime)
    if unseen then return st == "done" and "✓" or "⏸", "DiagnosticOk", st end
    return "", nil, ""
  end
  return "", nil, st
end

function M.tokens(lines)
  local n = 0
  for _, l in ipairs(lines) do n = n + #l + 1 end
  return math.ceil(n / 4 / 1000)
end

function M.advance() M.frame = M.frame % #FRAMES + 1 end

function M.touch_seen(dir)
  local f = io.open(dir .. "/seen", "w")
  if f then f:close() end
end

return M
