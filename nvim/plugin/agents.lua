-- agents.nvim loads lazily: call require('agents').setup({ root = '~/agent-files' }) from your config.
if vim.g.loaded_agents_nvim then return end
vim.g.loaded_agents_nvim = true
