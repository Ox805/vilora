#!/bin/bash
# Hook: Block git commits that mention Claude in the commit MESSAGE only
# (not in file paths, branch names, etc.)
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Check if this is a git commit command
if echo "$COMMAND" | grep -qi 'git commit'; then
  # Extract just the commit message (text between quotes after -m)
  MSG=$(echo "$COMMAND" | grep -oP '(?<=-m\s["\x27])(.*?)(?=["\x27]\s*$)' || \
        echo "$COMMAND" | grep -oP '(?<=EOF\n)(.*)(?=\nEOF)' || \
        echo "")

  # Also try heredoc style: content between EOF markers
  if [ -z "$MSG" ]; then
    MSG=$(echo "$COMMAND" | sed -n '/<<.*EOF/,/EOF/p' | grep -v 'EOF' | grep -v 'cat')
  fi

  # Check if the commit message text mentions claude (case insensitive)
  if [ -n "$MSG" ] && echo "$MSG" | grep -qi 'claude'; then
    echo "Blocked: Commit messages must not mention Claude." >&2
    exit 2
  fi
fi

exit 0
