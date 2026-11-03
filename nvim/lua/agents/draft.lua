-- Draft re-apply (md/docs/m1-build-spec.md §9.1): keep what the user typed when thread.md changes
-- under a modified buffer. `old` is the file as the buffer last read or wrote it, `mine` the
-- buffer before the reload, `new` the file now. What the user typed is diff(old, mine), so text
-- that came from the file (a streamed reply) is never part of it.
-- * An edit inside old's lines goes back in place when the file did not change those lines.
-- * Anything else, text added after old's last line or an edit the file also changed, is the
--   draft: put under the file's new empty `## you · tN` scaffold if it ends with one, else
--   appended at the end.
local T = require("agents.thread")
local M = {}

local diff = (vim.text and vim.text.diff) or vim.diff

-- hunks {start_a, count_a, start_b, count_b}; count == 0 means "after line start"
local function hunks(a, b)
  return diff(table.concat(a, "\n") .. "\n", table.concat(b, "\n") .. "\n", { result_type = "indices" })
end

--- Returns the merged lines and whether a draft was placed, or nil when `mine` equals `old`.
function M.merge(old, mine, new)
  local user = hunks(old, mine)
  if #user == 0 then return nil end
  local disk = hunks(old, new)
  -- line k of old, as a line of new; nil when the file changed it
  local function map(k)
    local off = 0
    for _, h in ipairs(disk) do
      local sa, ca, cb = h[1], h[2], h[4]
      if ca == 0 then
        if sa >= k then break end
        off = off + cb
      else
        if k < sa then break end
        if k < sa + ca then return nil end
        off = off + cb - ca
      end
    end
    return k + off
  end
  local edits, draft = {}, {}
  for _, h in ipairs(user) do
    local sa, ca, sb, cb = h[1], h[2], h[3], h[4]
    local typed = vim.list_slice(mine, sb, sb + cb - 1)
    local s -- 0-based start in new; nil = not in place
    if (ca == 0 and sa or sa + ca - 1) < #old then
      if ca == 0 then
        s = sa == 0 and 0 or map(sa)
      else
        local first, last = map(sa), map(sa + ca - 1)
        if first and last and last - first == ca - 1 then s = first - 1 end
      end
    end
    if s then edits[#edits + 1] = { s, s + ca, typed } else vim.list_extend(draft, typed) end
  end
  local out = vim.list_slice(new, 1, #new)
  for i = #edits, 1, -1 do
    local e = edits[i]
    local tail = vim.list_slice(out, e[2] + 1, #out)
    for j = #out, e[1] + 1, -1 do out[j] = nil end
    vim.list_extend(out, e[3])
    vim.list_extend(out, tail)
  end
  while #draft > 0 and not draft[#draft]:match("%S") do draft[#draft] = nil end
  while #draft > 0 and not draft[1]:match("%S") do table.remove(draft, 1) end
  if #draft == 0 then return out, false end
  local last = T.last(T.parse(out))
  if last and last.role == "you" and last.closed == "none" and last.empty then
    for j = #out, last.header + 1, -1 do out[j] = nil end
    out[#out + 1] = ""
  elseif #out > 0 and out[#out]:match("%S") then
    out[#out + 1] = ""
  end
  vim.list_extend(out, draft)
  return out, true
end

--- Change the buffer's lines to `lines`, touching only the lines that differ.
function M.set(buf, lines)
  local cur = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local hs = hunks(cur, lines)
  for i = #hs, 1, -1 do
    local sa, ca, sb, cb = hs[i][1], hs[i][2], hs[i][3], hs[i][4]
    local s = ca == 0 and sa or sa - 1
    vim.api.nvim_buf_set_lines(buf, s, s + ca, false, vim.list_slice(lines, sb, sb + cb - 1))
  end
end

return M
