# Scene 5: Trace a failing request across services
# Continues from scene 4: error filter and analysis filter are active
Output docs/screenshots/paged-05-trace.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state: open logdelve, apply error level filter, navigate to errors
Hide
Type "uv run python scripts/gen_promo_logs.py incident"
Enter
Sleep 2s
Type "clear"
Enter
Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 2s
Type "e"
Sleep 1s
Down@100ms 5
Show

# Trace by request ID
Sleep 5s
Type "r"
Sleep 3s

# See the full request lifecycle across components
Down@400ms 3
Sleep 2s

# Expand a line to see full JSON
Enter
Sleep 5s
