# Go to line feature demo
Output docs/screenshots/goto-line.gif

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

# Go to line
Type ":"
Sleep 0.5s
Type "500"
Enter
Sleep 1.5s

# Go to another line
Type ":"
Sleep 0.5s
Type "1000"
Enter
Sleep 1.5s

Type "q"
Sleep 0.5s
