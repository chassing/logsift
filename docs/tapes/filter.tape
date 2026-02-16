# Filter in/out and level filter demo
Output docs/screenshots/filter.gif

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

# Filter in
Type "f"
Sleep 0.5s
Type "Connection refused"
Enter
Sleep 2s

# Add filter out
Shift+F
Sleep 0.5s
Type "retry"
Enter
Sleep 1.5s

# Manage filters
Type "m"
Sleep 1.5s

# Toggle first filter
Space
Sleep 0.5s

# Close
Escape
Sleep 1s

# Suspend all
Type "x"
Sleep 1.5s

# Restore
Type "x"
Sleep 1s

# Level filter
Type "e"
Sleep 1s
Type "e"
Sleep 1s
Type "e"
Sleep 1s

Type "q"
Sleep 0.5s
