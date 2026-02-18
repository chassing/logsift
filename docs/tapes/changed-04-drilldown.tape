# Scene 4: Drill into a specific pattern
# Continues from scene 3: analysis dialog was just closed
Output docs/screenshots/changed-04-drilldown.gif

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
Type "a"
Down@300ms 2
Show

# Select it to create a filter
Sleep 3s
Type "f"
Sleep 3s

# Expand a line to see full JSON
Enter
Sleep 5s
