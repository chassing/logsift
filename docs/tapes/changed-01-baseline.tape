# Scene 1: Load with baseline comparison
Output docs/screenshots/changed-01-baseline.gif

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
Type "uv run python scripts/gen_promo_logs.py baseline"
Enter
Sleep 1s
Type "uv run python scripts/gen_promo_logs.py current-slow"
Enter
Sleep 1s
Type "clear"
Enter
Show

# Launch with baseline comparison
Type "uv run logdelve inspect --baseline /tmp/baseline.log /tmp/current.log"
Enter
Sleep 3s

# Scroll to see anomaly markers
Down@300ms 5
Sleep 5s
