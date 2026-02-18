# Scene 3: Save your investigation as a session
# Continues from scene 2: logdelve has error filter and bookmarks with annotations
Output docs/screenshots/postmortem-03-session.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state: open logdelve, filter errors
Hide
Type "uv run python scripts/gen_promo_logs.py incident"
Enter
Sleep 2s
Type "export LOGDELVE_CONFIG_DIR=/tmp/logdelve-demo-config"
Enter
Type "rm -rf /tmp/logdelve-demo-config"
Enter
Type "clear"
Enter
Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 2s
Type "e"
Sleep 1s
Type "r"
Sleep 1s
Shift+A
Sleep 1s
Type "We need to tackle this error later!"
Enter
Sleep 0.5s
Show

# Open session manager and rename session
Sleep 3s
Type "s"
Sleep 1s
Down@100ms 1
Type "r"
Sleep 1s
Type "incident-trace"
Enter
Sleep 2s
Type "q"
Sleep 1s

# Quit
Type "q"
Sleep 1s

# Second run: reload the session
Type "uv run logdelve inspect --session incident-trace /tmp/incident.log"
Enter
Sleep 3s

# Filters are restored
Down@300ms 3
Sleep 3s

# Quit
Type "q"
Sleep 1s
