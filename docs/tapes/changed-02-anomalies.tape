# Scene 2: Spot the anomalies - toggle anomaly filter
# Continues from scene 1: logdelve is open with baseline, anomalies visible
Output docs/screenshots/changed-02-anomalies.gif

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
Down@100ms 5
Show

# Toggle anomaly filter off to see full context
Sleep 1s
Type "!"
Sleep 3s

# Toggle back to anomaly-only view
Type "!"
Sleep 3s

Type "q"
Sleep 0.5s
