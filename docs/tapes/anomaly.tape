# Anomaly detection / baseline comparison demo
Output docs/screenshots/anomaly.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 80ms

Hide
Type "uv run python scripts/gen_demo_logs.py baseline > /tmp/baseline.log"
Enter
Type "uv run python scripts/gen_demo_logs.py current > /tmp/current.log"
Enter
Sleep 1s
Show

# Show the command
Type "uv run logdelve inspect --baseline /tmp/baseline.log --no-tail /tmp/current.log"
Enter
Sleep 3s

# Anomaly filter is auto-enabled — scroll through anomalies
Down@200ms 5
Sleep 1.5s

# Toggle off to see context
Type "!"
Sleep 2s

# Scroll to see normal lines around anomalies
Down@100ms 3
Sleep 1s

# Toggle back
Type "!"
Sleep 1.5s

# Analyze anomalies
Type "a"
Sleep 2s
Escape
Sleep 1s

Type "q"
Sleep 0.5s
