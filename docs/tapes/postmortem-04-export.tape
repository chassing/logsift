# Scene 4: Export the evidence
# Continues from scene 3: logdelve has error filter, bookmarks exist
Output docs/screenshots/postmortem-04-export.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state: open logdelve, filter errors, add bookmarks
Hide
Type "uv run python scripts/gen_promo_logs.py incident"
Enter
Sleep 2s
Type "mkdir -p /tmp/logdelve; cd /tmp/logdelve"
Enter
Type "clear"
Enter
Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 2s
Type "e"
Sleep 1s
Type "b"
Sleep 0.5s
Down@100ms 3
Type "b"
Sleep 0.5s
Show

# Open export dialog
Sleep 1s
Ctrl+E
Sleep 2s

# Select bookmarked scope
Down
Sleep 0.5s
Down
Sleep 0.5s
Enter
Sleep 3s

# Quit and show the exported file
Type "q"
Sleep 1s

Type "head -5 logdelve-export-*.log"
Enter
Sleep 3s
