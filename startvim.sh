#!/bin/bash

TARGETFILE="$(readlink -f "$1")"
TEMPFILE="$(mktemp)"
VIMRUNPORT=18082

echo "exec bash -c \"vim -- '$TARGETFILE'; echo done | nc 127.0.0.1 $VIMRUNPORT \"" >> "$TEMPFILE"

osascript << END
tell application "iTerm"
    activate
    set myterm to (make new terminal)
    tell myterm
        set number of columns to 140
        set number of rows to 150

        launch session "Default Session"

        tell the last session
            write text "$TEMPFILE"
            write contents of file "$TEMPFILE"
        end tell
    end tell
end tell
END

nc -l $VIMRUNPORT > /dev/null
