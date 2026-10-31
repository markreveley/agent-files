-- Minimal Lua mirror of lib/agent_files/thread.py (read-only subset): headers, ENDs, ids, fences.
local M = {}

local function is_fence(l)
  local s = l:match("^%s*(.-)%s*$")
  local p = s:sub(1, 3)
  return p == "```" or p == "~~~"
end
M.is_fence = is_fence

local function header(l)
  for _, sep in ipairs({ "\194\183", "%-", "%." }) do
    local id = l:match("^## you " .. sep .. " t(%d+)$")
    if id then return "you", tonumber(id) end
    id = l:match("^## agent " .. sep .. " t(%d+)$")
    if id then return "agent", tonumber(id) end
  end
  local src, nid = l:match("^## note \194\183 (.+) \194\183 t(%d+)$")
  if src then return "note", tonumber(nid), src end
  return nil
end

local function end_kind(l)
  if l == "END" then return "ok" end
  local k = l:match("^END %((%a+)%)$")
  if k == "interrupted" or k == "failed" or k == "conflict" then return k end
  return nil
end

--- Parse buffer lines. Returns { turns = {...}, marks = {{lnum, group}...}, carry = lnum|nil, malformed = bool }.
function M.parse(lines)
  local res = { turns = {}, marks = {}, carry = nil, malformed = false, fm_end = 0 }
  local i = 1
  if lines[1] and lines[1]:gsub("%s+$", "") == "---" then
    for j = 2, #lines do
      if lines[j]:gsub("%s+$", "") == "---" then
        res.fm_end = j
        i = j + 1
        break
      end
    end
  end
  local cur, in_fence, section = nil, false, "pre"
  local function mark(lnum, group) res.marks[#res.marks + 1] = { lnum, group } end
  local function close_cur(last_line, kind)
    cur.closed = kind
    cur.end_line = last_line
    cur.fence_open = false
    res.turns[#res.turns + 1] = cur
    cur = nil
  end
  for n = i, #lines do
    local line = lines[n]
    local s = line:gsub("%s+$", "")
    local handled = false
    if not in_fence then
      if s == "## carry" and section == "pre" and #res.turns == 0 and not res.carry then
        res.carry = n
        section = "carry"
        mark(n, "AgentsCarry")
        handled = true
      else
        local role, id, src = header(s)
        if role then
          if cur then
            if cur.role == "agent" then
              res.malformed = true
              cur.last_line = n - 1
              res.turns[#res.turns + 1] = cur
            else
              close_cur(n - 1, "ok")
            end
          end
          cur = { role = role, id = id, header = n, source = src, closed = "none", empty = true, last_line = n }
          section = "turn"
          mark(n, role == "you" and "AgentsYou" or role == "agent" and "AgentsAgent" or "AgentsNote")
          handled = true
        elseif cur and cur.closed == "none" and end_kind(s) then
          local k = end_kind(s)
          mark(n, k == "ok" and "AgentsEnd" or "AgentsEndAbnormal")
          close_cur(n, k)
          section = "after"
          handled = true
        end
      end
    end
    if not handled then
      if cur then
        cur.last_line = n
        if cur.role == "agent" and not in_fence and line:sub(1, 2) == "! " then
          mark(n, "AgentsDiag")
        else
          if line:match("%S") then cur.empty = false end
          if cur.role == "agent" and not in_fence and line:sub(1, 3) == "\226\150\184" then mark(n, "AgentsTool") end
        end
      end
    end
    if is_fence(line) then in_fence = not in_fence end
  end
  if cur then
    cur.fence_open = in_fence
    res.turns[#res.turns + 1] = cur
  end
  return res
end

function M.last(p) return p.turns[#p.turns] end

return M
