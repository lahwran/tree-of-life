from crow2.events.hooktree import HookMultiplexer, CommandHook
from crow2.events.exceptions import NameResolutionError

from todo_tracker.file_storage import parse_line
from todo_tracker.tracker import nodecreator

def _makenode(string):
    indent, is_metadata, node_type, text = parse_line(string)
    if is_metadata:
        raise Exception("metadata not allowed")
    if indent > 0:
        raise Exception("plz 2 not indent")
    return node_type, text

command = HookMultiplexer(hook_class=CommandHook, childarg="command")

@command
@command("finished")
@command("next")
def done(event):
    event.tracker.activate_next()

@command
@command("donext")
@command(">")
def after(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_after(node_type, text, activate=False)

@command
@command("dofirst")
@command("<")
def before(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_before(node_type, text, activate=True)

@command
def createchild(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_child(node_type, text, activate=True)

@command
@command("edit")
def vim(event):
    event.ui.vim()

@command
def todo(event):
    if event.text:
        event.tracker.todo.createchild("todo", event.text)
    else:
        event.ui.display_lines([str(child) for child in event.tracker.todo.children])

def generate_listing(active, root, node, lines=None, indent=0):
    if lines is None:
        lines = []

    indent_text = " " * 4
    if active is node:
        prefix = "> "
    else:
        prefix = "  "

    if node is root:
        indent = -1
    else:
        lines.append(prefix + (indent_text * indent) + str(node))

    for child in node.children:
        generate_listing(active, root, child, lines, indent+1)
    return lines

class CommandInterface(object):
    max_format_depth = 2
    _default_command = "createchild"

    def __init__(self, tracker):
        self.tracker = tracker
    
    def _command(self, source, command_name, text):
        try:
            command.fire(source=source, tracker=self.tracker, command=command_name, text=text, ui=self)
        except NameResolutionError:
            self.errormessage(source, "no such command %r" % command_name)

    def command(self, source, line):
        if not line.strip():
            return

        node_type, separator, text = line.partition(": ")
        if node_type in nodecreator.creators:
            command_text = line
            command_name = self._default_command
        else:
            command_name, center, command_text = line.partition(" ")
            if not command_name:
                return

        self._command(source, command_name, command_text)

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

    def term_subprocess(self, args, callback):
        raise NotImplementedError

    def errormessage(self, source, message):
        print message

    def display_lines(self, lines):
        pass

    def displaychain(self, limit=True):
        if limit:
            return [x[0] for x in zip(self.tracker.active_node.iter_parents(), range(self.max_format_depth))]
        else:
            return list(self.tracker.active_node.iter_parents())

    def tree_context(self):
        active = self.tracker.active_node
        root = self.tracker.root
        lines = generate_listing(active, root, self.displaychain()[-1])
        return lines
