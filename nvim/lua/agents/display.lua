-- Thread-aware display (view-layer step 1): highlights, folds, end-of-thread mark.
local T = require("agents.thread")
local S = require("agents.status")
local M = {}

M.ns = vim.api.nvim_create_namespace("agents_display")
M.ns_end = vim.api.nvim_create_namespace("agents_endmark")

local links = {
  AgentsYou = "Title", AgentsAgent = "Special", AgentsNote = "Comment", AgentsCarry = "Constant",
  AgentsEnd = "Comment", AgentsEndAbnormal = "WarningMsg", AgentsDiag = "ErrorMsg", AgentsTool = "Comment",
  AgentsMark = "Comment",
}
function M.define_highlights()
  for name, to in pairs(links) do vim.api.nvim_set_hl(0, name, { link = to, default = true }) end
end

local fold_cache = {}

local function compute_folds(lines)
  local lv = {}
  local in_tool = false
  local p = T.parse(lines)
  local tool_lines = {}
  for _, m in ipairs(p.marks) do if m[2] == "AgentsTool" then tool_lines[m[1]] = true end end
  for n, l in ipairs(lines) do
    if tool_lines[n] then
      lv[n] = ">1"
      in_tool = true
    elseif in_tool and l:match("^%s+%S") then
      lv[n] = "1"
    else
      in_tool = false
      lv[n] = "0"
    end
  end
  return lv
end

function M.foldexpr(lnum)
  local buf = vim.api.nvim_get_current_buf()
  local tick = vim.api.nvim_buf_get_changedtick(buf)
  local c = fold_cache[buf]
  if not c or c.tick ~= tick then
    c = { tick = tick, lv = compute_folds(vim.api.nvim_buf_get_lines(buf, 0, -1, false)) }
    fold_cache[buf] = c
  end
  return c.lv[lnum] or "0"
end

--- Re-apply highlights and the end mark. `info` = status.read(dir) or nil.
function M.apply(buf, info)
  if not vim.api.nvim_buf_is_valid(buf) then return end
  local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  local p = T.parse(lines)
  vim.api.nvim_buf_clear_namespace(buf, M.ns, 0, -1)
  for _, m in ipairs(p.marks) do
    local l = lines[m[1]]
    vim.api.nvim_buf_set_extmark(buf, M.ns, m[1] - 1, 0, { end_col = #l, hl_group = m[2], priority = 300 })
  end
  M.endmark(buf, lines, p, info)
end

function M.endmark(buf, lines, p, info)
  vim.api.nvim_buf_clear_namespace(buf, M.ns_end, 0, -1)
  lines = lines or vim.api.nvim_buf_get_lines(buf, 0, -1, false)
  p = p or T.parse(lines)
  local last = T.last(p)
  local target
  if last and last.role == "agent" and last.closed == "none" then
    target = last.header
  else
    for i = #p.turns, 1, -1 do
      if p.turns[i].end_line then target = p.turns[i].end_line break end
    end
    target = target or (last and last.header)
  end
  if not target then return end
  local glyph, hl, word = S.mark(info or {})
  local parts = {}
  if glyph ~= "" then parts[#parts + 1] = glyph end
  if word ~= "" then parts[#parts + 1] = word end
  local txt = table.concat(parts, " ")
  if txt ~= "" then txt = txt .. " · " end
  txt = "  " .. txt .. "~" .. S.tokens(lines) .. "k"
  vim.api.nvim_buf_set_extmark(buf, M.ns_end, target - 1, 0, {
    virt_text = { { txt, hl or "AgentsMark" } }, virt_text_pos = "eol", priority = 300,
  })
end

local FOLDEXPR = "v:lua.require'agents.display'.foldexpr(v:lnum)"
local WINOPTS = { conceallevel = 2, wrap = true, linebreak = true, foldmethod = "expr", foldexpr = FOLDEXPR,
  foldenable = true, foldlevel = 0 }

--- Thread settings for the thread buffer shown in `win`, like :setlocal, so other buffers and new
--- windows keep their own. Only the first time the thread shows in that window: Vim restores these
--- when the buffer comes back to the window, and setting them again would re-close the user's folds.
function M.setup_window(win)
  if vim.api.nvim_get_option_value("foldexpr", { win = win }) == FOLDEXPR then return end
  for name, value in pairs(WINOPTS) do vim.api.nvim_set_option_value(name, value, { scope = "local", win = win }) end
end

return M
