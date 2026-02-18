# Scene 3: Analyze the changes - message templates
# Continues from scene 2: logdelve is open with anomaly filter active
Output docs/screenshots/changed-03-analyze.gif

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
Type "uv run python scripts/gen_promo_logs.py baseline"
Enter
Sleep 1s
Type "uv run python scripts/gen_promo_logs.py current-slow"
Enter
Sleep 1s
Type "clear"
Enter
Type "uv run logdelve inspect --baseline /tmp/baseline.log /tmp/current.log"
Enter
Sleep 2s
Show

# Open analysis dialog
Sleep 2s
Type "a"
Sleep 3s

# Sort by level to see errors first
Type "s"
Sleep 2s

# Scroll through groups
Down@300ms 3
Sleep 5s
