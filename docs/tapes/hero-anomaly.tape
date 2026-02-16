# Hero 2: Anomaly detection with baseline comparison
Output docs/screenshots/hero-anomaly.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1400
Set Height 800
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 80ms

# Setup (hidden)
Hide
Type "export LOGDELVE_DEMO=anomaly"
Enter
Type "uv run python scripts/gen_demo_logs.py baseline > /tmp/baseline.log 2>/dev/null"
Enter
Type "uv run python scripts/gen_demo_logs.py current > /tmp/current.log 2>/dev/null"
Enter
Sleep 2s
Type "clear"
Enter
Show

# Start with baseline comparison
Type "uv run logdelve inspect --baseline /tmp/baseline.log --no-tail /tmp/current.log"
Enter
Sleep 3s

# Label 0: "🔍 Anomaly Detection"
Ctrl+B
Sleep 3s

# Scroll through anomalies
Down@200ms 4
Sleep 2s

# Toggle off to see context
Type "!"
Sleep 3s

# Toggle back
Type "!"
Sleep 2s

# Label 1: "📊 Analyzing patterns"
Ctrl+B
Sleep 2s

Type "a"
Sleep 3s

Escape
Sleep 1s

# Level filter
Type "e"
Sleep 2s

# Suspend all
Type "x"
Sleep 2s

# Restore
Type "x"
Sleep 2s

# Label 2: "github.com/chassing/logdelve"
Ctrl+B
Sleep 4s

Type "q"
Sleep 0.5s
