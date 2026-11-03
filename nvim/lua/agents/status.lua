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

--- `working` with no status write for STALE_SECS: the runner died.
function M.stale(info, now)
  return info.status == "working" and info.status_mtime ~= nil
    and (now or os.time()) - info.status_mtime >= M.STALE_SECS
end

--- `working` and not stale: lock the buffer, run the spinner.
function M.working(info, now) return info.status == "working" and not M.stale(info, now) end

--- Returns glyph, highlight group, word ("" = idle).
function M.mark(info, now)
  local st = info.status
  if not st then return "", nil, "" end
  if st == "working" then
    if M.stale(info, now) then return "?", "WarningMsg", "stale" end
    return FRAMES[M.frame], "DiagnosticInfo", "working"
  elseif st == "blocked" then
    return "●", "ErrorMsg", "blocked"
  elseif st == "failed" then
    return "✗", "ErrorMsg", "failed"
  elseif st == "done" or st == "interrupted" then
    if M.unseen(info) then return st == "done" and "✓" or "⏸", "DiagnosticOk", st end
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

--- `seen` is missing or older than `status`.
function M.unseen(info)
  return not info.seen_mtime or (info.status_mtime ~= nil and info.status_mtime > info.seen_mtime)
end

--- Touch `seen`, only when the status is unseen: writing it fires the directory watcher.
function M.touch_seen(dir)
  local info = M.read(dir)
  if not info.status or not M.unseen(info) then return end
  local f = io.open(dir .. "/seen", "w")
  if f then f:close() end
end

return M
