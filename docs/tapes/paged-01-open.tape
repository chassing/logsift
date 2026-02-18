# Scene 1: Open the incident logs
Output docs/screenshots/paged-01-open.gif

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

# Open the merged incident log
Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 3s

# Scroll down to show the log view
Down@400ms 5
Sleep 3s
