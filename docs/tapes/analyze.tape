# Message analysis and field grouping demo
Output docs/screenshots/analyze.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 80ms

Hide
Type "uv run python scripts/gen_demo_logs.py current > /tmp/demo.log"
Enter
Sleep 1s
Show

Type "uv run logdelve inspect --no-tail /tmp/demo.log"
Enter
Sleep 2s

# Open analyze
Type "a"
Sleep 2s

# Scroll through message groups
Down@200ms 3
Sleep 1s

# Sort by level
Type "s"
Sleep 1.5s

# Switch to fields mode
Type "m"
Sleep 2s

# Scroll fields
Down@200ms 3
Sleep 1s

# Select a field to filter
Enter
Sleep 2s

# Show filtered result
Sleep 1s

Type "q"
Sleep 0.5s
