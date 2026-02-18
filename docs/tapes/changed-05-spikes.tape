# Scene 5: Check frequency spikes with field analysis
# Continues from scene 4: a filter is active from drilldown
Output docs/screenshots/changed-05-spikes.gif

Require logdelve

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 768
Set Padding 10
Set Theme "Dracula"
Set TypingSpeed 60ms

# Replay previous state
Hide
Type "uv run python scripts/gen_promo_logs.py baseline"
Enter
Sleep 1s
Type "uv run python scripts/gen_promo_logs.py current-slow"
Enter
Sleep 1s
Type "clear"
Enter
Type "uv run logdelve inspect --baseline /tmp/baseline.log /tmp/current.log"
Enter
Sleep 2s
Show

# Open analysis
Sleep 3s
Type "a"
Sleep 2s

# Switch to fields mode
Type "m"
Sleep 3s

# Scroll through field value distributions
Down@300ms 5
Sleep 3s

Escape
Sleep 1s

Type "q"
Sleep 0.5s
