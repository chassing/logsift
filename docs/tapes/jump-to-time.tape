# Jump to timestamp feature demo
Output docs/screenshots/jump-to-time.gif

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
Type "clear"
Enter
Show

Type "uv run logdelve inspect /tmp/demo.log"
Enter
Sleep 2s

# Jump to timestamp
Type "@"
Sleep 0.5s
Type "14:30"
Enter
Sleep 1.5s

# Jump to another timestamp
Type "@"
Sleep 0.5s
Type "5m"
Enter
Sleep 1.5s

Type "q"
Sleep 0.5s
