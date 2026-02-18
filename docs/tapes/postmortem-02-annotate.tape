# Scene 2: Annotate your findings
# Continues from scene 1: logdelve is open, errors filtered, some lines bookmarked
Output docs/screenshots/postmortem-02-annotate.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state: open logdelve, filter errors, bookmark a line
Hide
Type "uv run python scripts/gen_promo_logs.py incident"
Enter
Sleep 2s
Type "clear"
Enter
Type "uv run logdelve inspect /tmp/incident.log"
Enter
Sleep 2s
Type "e"
Sleep 1s
Type "b"
Sleep 0.5s
Show

# Annotate the bookmarked line
Sleep 2s
Shift+A
Sleep 1s
Type "Root cause: DB connection pool exhausted"
Enter
Sleep 3s

# Navigate down, bookmark and annotate another
Down@300ms 5
Sleep 1s
Type "b"
Sleep 1s
Shift+A
Sleep 1s
Type "First ECONNREFUSED occurrence"
Enter
Sleep 3s
