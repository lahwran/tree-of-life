#!/usr/bin/python

import subprocess
from todo_tracker.util import tempfile
import sys

port = 18082

replace_command = "exec bash -c '%s'\n"
args = []
for arg in sys.argv[1:]:
    if "'" in arg:
        raise Exception("Can't put quotes in args! sorry")
    args.append("'%s'" % arg)

inner_command = "vim %s; echo done | nc 127.0.0.1 %d" % (" ".join(args), port)
remote_command = replace_command % inner_command.replace("\\'", "'\"'\"'")
print remote_command

temp_command = tempfile()
writer = open(temp_command, "w")
writer.write(remote_command)
writer.close()
print temp_command

temp_code = tempfile()
code_writer = open(temp_code, "w")
code_writer.write("""
tell application "iTerm"
    activate
    set myterm to (make new terminal)
    tell myterm
        set number of columns to 140
        set number of rows to 150

        launch session "Default Session"

        tell the last session
            write contents of file "{tempfile}"
        end tell
    end tell
end tell
""".format(tempfile=temp_command))
code_writer.close()
print code_writer

subprocess.call(["osascript", temp_code])
print "osascript done"
subprocess.call(["nc", "-l", str(port)], stdout=open("/dev/null"))
print "nc done"
