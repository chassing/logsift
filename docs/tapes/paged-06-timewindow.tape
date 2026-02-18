# Scene 6: Narrow the time window
# Continues from scene 5: logdelve is open, viewing error area
Output docs/screenshots/paged-06-timewindow.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state: open logdelve fresh
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

# Jump to the incident start time
Sleep 1s
Type "@"
Sleep 0.5s
Type "14:11"
Sleep 2s
Enter
Sleep 3s

# Open filter dialog, switch to Time tab
Type "f"
Sleep 1s
Shift+Tab
Sleep 0.5
Right@200ms 2
Sleep 0.5s
Tab
Sleep 1s

# Set start time
Type "14:15"
Tab
Sleep 1s

# Set end time
Type "14:20"
Enter
Sleep 3s

# Scroll through the filtered incident window
Down@300ms 5
Sleep 3s
