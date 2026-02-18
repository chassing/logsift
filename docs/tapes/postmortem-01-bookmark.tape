# Scene 1: Bookmark key evidence
Output docs/screenshots/postmortem-01-bookmark.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Setup
Hide
Type "uv run python scripts/gen_promo_logs.py incident"
Enter
Sleep 2s
Type "clear"
Enter
Show

Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 2s

# Filter to errors
Type "e"
Sleep 2s

# Bookmark the first error
Type "b"
Sleep 2s

# Scroll down to find another key line
Down@300ms 5
Sleep 1s

# Bookmark it
Type "b"
Sleep 2s

# Navigate between bookmarks
Type "["
Sleep 2s
Type "]"
Sleep 2s

# List all bookmarks
Shift+B
Sleep 3s

Escape
Sleep 2s
