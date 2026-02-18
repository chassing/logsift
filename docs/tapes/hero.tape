# Hero 1: JSON log viewing, filtering, and search
Output docs/screenshots/hero.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1024
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Setup (hidden)
Hide
Type "export LOGDELVE_DEMO=hero"
Enter
Type "uv run python scripts/gen_demo_logs.py current > /tmp/demo.log 2>/dev/null"
Enter
Sleep 2s
Type "clear"
Enter
Show

# Start app
Type "uv run logdelve inspect /tmp/demo.log"
Enter
Sleep 1s

# Welcome message
Ctrl+B
Sleep 4s

# Scroll to see different log levels
Ctrl+B
Sleep 3s
Down@400ms 5
Sleep 2s


# Label: "📋 expand log line"
Ctrl+B
Sleep 3s
Enter
Sleep 3s
Down@600ms 5
Sleep 1s
Enter
Sleep 1s

# Toggle JSON pretty-print
Ctrl+B
Sleep 3s
Type "j"
Sleep 3s

# Back to compact
Type "j"
Sleep 2s

# Label 1: "🎛️ Filtering by pattern"
Ctrl+B
Sleep 3s

# Filter in via JSON suggestions
Type "f"
Sleep 3s
Down@300ms 4
Sleep 1s
Space
Enter
Ctrl+B
Sleep 4s

# toggle filter
Ctrl+B
Sleep 3s
Type "x"
Sleep 3s
Type "x"
Sleep 2s

# clear filter
Ctrl+B
Sleep 3s
Type "m"
Sleep 2s
Type "c"
Sleep 2s
Escape
Sleep 1s

# Label 2: "🔎 Searching logs"
Ctrl+B
Sleep 3s

Type "/"
Sleep 1s
Type "orders"
Sleep 2s
Enter
Sleep 2s

# Navigate matches
Type "n"
Sleep 0.5s
Type "n"
Sleep 0.5s
Type "n"
Sleep 2s

# Label 3: "github.com/chassing/logdelve"
Ctrl+B
Sleep 4s

Type "q"
Sleep 0.5s
