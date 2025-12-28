#!/bin/zsh
osascript <<'APPLESCRIPT'
tell application "Terminal"
    activate
    set newTab to do script ""
    do script "cd /Users/debprakash/Documents/GitHub/MyPaperAgent; ./run_my_paper_agent.sh" in newTab
end tell
APPLESCRIPT
