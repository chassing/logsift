# Search feature demo
Output docs/screenshots/search.gif

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

# Forward search
Type "/"
Sleep 0.5s
Type "error"
Enter
Sleep 1.5s

# Navigate matches
Type "n"
Sleep 0.5s
Type "n"
Sleep 0.5s
Type "n"
Sleep 1s

# Backward search
Type "?"
Sleep 0.5s
# Shows previous search pre-filled
Enter
Sleep 1s

Type "N"
Sleep 0.5s
Type "N"
Sleep 1.5s

Type "q"
Sleep 0.5s
