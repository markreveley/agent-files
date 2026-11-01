#!/bin/sh
# Symlink bin/* into ~/.local/bin and print the Claude Code hook block.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HOME/.local/bin}"
mkdir -p "$DEST"
for f in "$HERE"/bin/agent-files-*; do
  ln -sf "$f" "$DEST/$(basename "$f")"
  echo "linked $DEST/$(basename "$f")"
done
cat <<JSON

Add this to ~/.claude/settings.json (merge with any existing "hooks"):

{ "hooks": {
JSON
first=1
for ev in $("$HERE/bin/agent-files-hook" --events); do
  [ $first = 1 ] || printf ',\n'
  first=0
  printf '  "%s": [{ "hooks": [{ "type": "command", "command": "agent-files-hook" }] }]' "$ev"
done
printf '\n}}\n\n'
echo "Data root: \${AGENT_FILES_ROOT:-~/agent-files} (NOT this checkout). Run: agent-files-run init"
echo "Neovim: add $HERE/nvim to runtimepath, then require('agents').setup({ root = '~/agent-files' })"
