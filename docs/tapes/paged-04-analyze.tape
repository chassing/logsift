# Scene 4: Analyze message patterns
# Continues from scene 3: logdelve is open with ERROR level filter active
Output docs/screenshots/paged-04-analyze.gif

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
Type "e"
Sleep 1s
Show

# Open analysis dialog
Sleep 2s
Type "a"
Sleep 3s

# Sort by count to see dominant patterns
Type "s"
Sleep 2s

# Scroll through groups
Down@300ms 3
Sleep 2s

# Select the top error group to create filter
Type "f"
Sleep 3s
