from crow2.events.hooktree import HookMultiplexer, CommandHook
from crow2.events.exceptions import NameResolutionError

from todo_tracker.file_storage import parse_line

def _makenode(string):
    indent, is_metadata, node_type, text = parse_line(string)
    if is_metadata:
        raise Exception("metadata not allowed")
    if indent > 0:
        raise Exception("plz 2 not indent")
    return node_type, text

command = HookMultiplexer(hook_class=CommandHook, childarg="command")

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
def vim(event):
    event.ui.vim()

#@command("list")
#def list_current(event):
#    pass

class CommandLineInterface(object):
    def __init__(self, tracker):
        self.tracker = tracker
        self.max_ps1_len = 47
        self.max_format_depth = 2
        self._default_command = "createchild"
    
    def _command(self, command_name, text):
        try:
            command.fire(tracker=self.tracker, command=command_name, text=text, ui=self)
        except NameResolutionError:
            self.errormessage("no such command %r" % command_name)

    def command(self, line):
        command_name, center, text = line.partition(" ")
        if not command_name:
            return

        if command_name.endswith(":"):
            text = line
            command_name = self._default_command

        self._command(command_name, text)


    def vim(self):
        import tempfile
        import os
        tmpfd0, tmp = tempfile.mkstemp()
        tmpfd1, tmp_backup = tempfile.mkstemp()
        print "tmp:", tmp
        print "tmp-backup:", tmp_backup

        self.tracker.save(open(tmp, "w"))
        self.tracker.save(open(tmp_backup, "w"))

        def callback():
            if open(tmp, "r").read() == open(tmp_backup, "r"):
                os.unlink(tmp)
                os.unlink(tmp_backup)
                print "text same, not loading"
                return

            self.tracker.load(open(tmp, "r"))

            os.unlink(tmp)
        self.term_subprocess(["vim", "--", tmp], callback)
    
    def _format_active(self):
        items = []
        result = ""
        for node in self.tracker.active_node.iter_parents():
            items.append(str(node))
            result = " > ".join(items[::-1])
            if len(items) >= self.max_ps1_len:
                break
            if len(result) > self.max_ps1_len:
                break
            
        minchar = min(0, len(result) - self.max_ps1_len)
        if minchar > 0:
            result = "..." + result[minchar:]

        return result

    def prompt(self):
        return "[%s] > " % self._format_active()

    def term_subprocess(self, args, callback):
        import subprocess
        process = subprocess.Popen(args)
        process.wait()
        callback()

    def errormessage(self, message):
        print message
