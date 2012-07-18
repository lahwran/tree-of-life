from crow2.events.hooktree import HookMultiplexer, CommandHook
from crow2.events.exceptions import NameResolutionError

from todo_tracker.tracker import Tracker
from todo_tracker.file_storage import parse_line

def _makenode(string):
    indent, is_metadata, node_type, text = parse_line(string)
    if is_metadata:
        raise Exception("metadata not allowed")
    if indent > 0:
        raise Exception("plz 2 not indent")
    return node_type, text

hook_factory = lambda *args, **keywords: CommandHook(stop_exceptions=True, *args, **keywords)
command = HookMultiplexer(hook_class=hook_factory, childarg="command")

@command
def done(event):
    event.tracker.activate_next(ascend=False, descend=True)

@command
def activate_next(event):
    event.tracker.activate_next()

@command
def after(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_after(node_type, text, activate=False)

@command
def before(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_before(node_type, text, activate=True)

@command
def createchild(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_child(node_type, text, activate=True)

@command
def pdb(event):
    import pdb; pdb.set_trace()

@command
def quit(event):
    event.tracker.save(open("activities", "w"))
    event.quit = True

max_ps1_len = 47
max_format_depth = 2

def format_active(tracker):
    items = []
    result = " > "
    for node in tracker.active_node.iter_parents():
        items.append(str(node))
        result = " > ".join(items[::-1]) + " > "
        if len(items) >= max_ps1_len:
            break
        if len(result) > max_ps1_len:
            break
        
    minchar = min(0, len(result) - max_ps1_len)
    if minchar > 0:
        result = "..." + result[minchar:]

    return result

@command
def vim(event):
    import subprocess
    import tempfile
    import os
    tmpfd0, tmp = tempfile.mkstemp()
    tmpfd1, tmp_backup = tempfile.mkstemp()
    print "tmp:", tmp
    print "tmp-backup:", tmp_backup

    event.tracker.save(open(tmp, "w"))
    event.tracker.save(open(tmp_backup, "w"))

    vim_process = subprocess.Popen(["vim", "--", tmp])
    vim_process.wait()

    if open(tmp, "r").read() == open(tmp_backup, "r"):
        os.unlink(tmp)
        os.unlink(tmp_backup)
        print "text same, not loading"
        return

    event.tracker.load(open(tmp, "r"))

    os.unlink(tmp)

@command("list")
def list_current(event):
    pass


def main():
    tracker = Tracker()
    try:
        activities = open("activities", "r")
    except IOError:
        pass
    else:
        tracker.load(activities)

    quit = False

    while not quit:
        line = raw_input(format_active(tracker)).strip()
        command_name, center, text = line.partition(" ")
        if not command_name:
            continue

        try:
            event = command.fire(command=command_name, text=text, quit=False, tracker=tracker)
        except NameResolutionError:
            print "no such command"
        else:
            quit = event.quit

if __name__ == "__main__":
    main()
