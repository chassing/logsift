# Scene 2: Get oriented - component display and JSON expansion
# Continues from scene 1: logdelve is open, scrolled down a few lines
Output docs/screenshots/paged-02-orient.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state
Hide
Type "uv run python scripts/gen_promo_logs.py incident"
Enter
Sleep 2s
Type "clear"
Enter
Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 2s
Down@100ms 5
Show

# Cycle component display to full names
Sleep 2s
Type "c"
Sleep 3s

# Expand a single JSON line
Enter
Sleep 3s
Down@300ms 5

# Collapse it
Enter
Sleep 2s

# Expand all JSON
Type "j"
Sleep 3s

# Collapse all JSON
Type "j"
Sleep 3s
