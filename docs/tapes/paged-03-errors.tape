# Scene 3: Find the errors - level filter
# Continues from scene 2: logdelve is open with default view
Output docs/screenshots/paged-03-errors.gif

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
Show

# Cycle level filter to ERROR
Sleep 2s
Type "e"
Sleep 3s

# Scroll through error lines
Down@300ms 5
Sleep 2s
Down@300ms 5
Sleep 5s
