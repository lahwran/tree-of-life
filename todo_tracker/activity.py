from __future__ import absolute_import

import traceback
import os
import json
import subprocess
from datetime import datetime, timedelta
import time


from twisted.python import log

from todo_tracker.file_storage import parse_line
from todo_tracker.tracker import nodecreator
from todo_tracker.exceptions import InvalidInputError
from todo_tracker.util import tempfile

def _makenode(string):
    indent, is_metadata, node_type, text = parse_line(string)
    if is_metadata:
        raise InvalidInputError("metadata not allowed")
    if indent > 0:
        raise InvalidInputError("plz 2 not indent")
    return node_type, text

class CommandList(object):
    def __init__(self):
        self.commands = {}

    def add(self, name=None):
        def _inner(func):
            _name = name
            if _name is None:
                _name = func.__name__
            self.commands[_name] = func
            return func
        return _inner

global_commands = CommandList()
command = global_commands.add

@command()
@command("finished")
@command("next")
def done(event):
    event.tracker.activate_next()

@command()
@command("donext")
@command(">")
def after(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_after(node_type, text, activate=False)

@command()
@command("dofirst")
@command("<")
def before(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_before(node_type, text, activate=True)

@command()
def createchild(event):
    node_type, text = _makenode(event.text)
    event.tracker.create_child(node_type, text, activate=True)

@command()
@command("edit")
def vim(event):
    event.ui.vim(event.source)

@command()
def todo(event):
    if event.text:
        event.tracker.todo.createchild("todo", event.text)
    else:
        event.ui.display_lines([str(child) for child in event.tracker.todo.children])

def _listing_node(active, node, indent):
    indent_text = " " * 4
    if active is node:
        prefix = "> "
    else:
        prefix = "  "
    return prefix + (indent_text * indent) + str(node)

def generate_listing(active, node, lines=None, indent=0):
    if lines is None:
        lines = []

    lines.append(_listing_node(active, node, indent))

    for child in node.children:
        generate_listing(active, child, lines, indent+1)
    return lines

class Event(object):
    def __init__(self, source, tracker, command_name, text, ui):
        self.source = source
        self.tracker = tracker
        self.command_name = command_name
        self.text = text
        self.ui = ui

class CommandInterface(object):
    max_format_depth = 2
    _default_command = "createchild"

    def __init__(self, tracker):
        self.tracker = tracker
        self.config = {}

    def _command(self, source, command_name, text):
        try:
            target = global_commands.commands[command_name]
        except KeyError:
            self.errormessage(source, "no such command %r" % command_name)
        else:
            event = Event(source, self.tracker, command_name, text, self)
            target(event)

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

    def vim(self, source, **keywords):
        import os
        tmp = tempfile()
        tmp_backup = tempfile()
        exceptions = []
        # USER MESSAGE
        print "tmp:", tmp
        # USER MESSAGE
        print "tmp-backup:", tmp_backup

        self.tracker.save(open(tmp, "w"))
        self.tracker.save(open(tmp_backup, "w"))

        def callback():
            if open(tmp, "r").read() == open(tmp_backup, "r").read():
                os.unlink(tmp)
                os.unlink(tmp_backup)
                # USER MESSAGE
                print "text same, not loading"
                return True

            try:
                self.tracker.load(open(tmp, "r"))
            except Exception:
                # USER MESSAGE NEEDED
                log.err()
                formatted = traceback.format_exc()
                tmp_exception = tempfile()
                writer = open(tmp_exception, "w")
                writer.write(formatted)
                writer.close()
                exceptions.append(tmp_exception)
                self.tracker.load(open(tmp_backup, "r"))
                self._run_vim(source, callback, tmp, tmp_exception, **keywords)
                return False
            else:
                # USER MESSAGE
                print "loaded"
                # LOGGING
                print "new active: %r" % self.tracker.active_node

                #os.unlink(tmp)
                # TODO: unlink temp file?
                for exc_temp in exceptions:
                    os.unlink(exc_temp)
                return True

        self._run_vim(source, callback, tmp, **keywords)

    def _run_vim(self, source, callback, extra, *filenames, **keywords):
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

    def tree_context(self, max_lines=55):
        active = self.tracker.active_node
        current = active.find_node(["<day"])
        days = current.parent
        root = self.tracker.root
        
        lines = []
        lines.append(_listing_node(active, days, 0))
        if current.prev_neighbor:
            lines.append(_listing_node(None, "...", 1))
        while len(lines) < max_lines and current:
            generate_listing(active, current, lines, indent=1)
            current = current.next_neighbor
        if len(lines) >= max_lines:
            lines = lines[:max_lines]
            lines[-1] = _listing_node(None, "...", 2)
        return lines

class Git(object):
    def __init__(self, path):
        self.path = path

    def init(self):
        if not os.path.isdir(os.path.join(self.path, ".git")):
            self._git("init")

    def gitignore(self, names):
        if not os.path.exists(os.path.join(self.path, ".gitignore")):
            writer = open(os.path.join(self.path, ".gitignore"), "w")
            for name in names:
                writer.write("%s\n" % name)
            

    def add(self, *filenames):
        self._git("add", *filenames)

    def commit(self, message):
        self._git("commit", "-m", message)

    def _git(self, *args):
        process = subprocess.Popen(["git"] + list(args), cwd=self.path)
        return process.wait()

class SavingInterface(CommandInterface):
    def __init__(self, tracker, directory, main_file,
            config_file="config.json",
            autosave_template="_{main_file}_autosave_{time}",
            backup_template="_{main_file}_backup_{time}"):
        super(SavingInterface, self).__init__(tracker)

        self.save_dir = os.path.realpath(os.path.expanduser(directory))
        self.main_file = main_file
        self.save_file = os.path.join(self.save_dir, main_file)
        self.config_file = os.path.join(self.save_dir, config_file)
        self.autosave_file = os.path.join(self.save_dir, autosave_template)
        self.backup_file = os.path.join(self.save_dir, backup_template)
        self.timeformat = "%A %B %d %H:%M:%S %Y"

        self.last_auto_save = None
        self.last_backup_save = None
        self.last_full_save = None

        self.autosave_id = time.time()
        self.autosave_minutes = 5
        self.backup_minutes = 30

        self.git = Git(self.save_dir)

    def _load(self, filename, callback):
        try:
            reader = open(os.path.realpath(filename), "r")
        except IOError:
            return None
        else:
            return callback(reader)

    def load(self):
        try:
            reader = open(os.path.realpath(self.save_file), "r")
        except IOError:
            # what do?
            pass
        else:
            self.tracker.load(reader)
        self._load(self.save_file, self.tracker.load)
        config = self._load(self.config_file, json.load)
        if config:
            self.config = config

    def full_save(self):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self.git.init()

        json.dump(self.config, open(self.config_file, "w"), sort_keys=True, indent=4)
        self.git.add(self.config_file)

        self.tracker.save(open(self.save_file, "w"))
        self.git.add(self.save_file)

        self.git.gitignore(["_*"])
        self.git.add(".gitignore")

        self.git.commit("Full save %s" % datetime.now().strftime(self.timeformat))
        self.last_full_save = datetime.now()

    def auto_save(self):
        self._special_save(self.autosave_file, self.autosave_id, self.autosave_minutes, "last_auto_save")

        self.backup_save()

    def backup_save(self):
        self._special_save(self.backup_file, time.time(), self.backup_minutes, "last_backup_save")

    def _special_save(self, name_format, time, freq, lastname):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        last = getattr(self, lastname)
        if last and datetime.now() < last + timedelta(minutes=freq):
            return

        filename = name_format.format(main_file=self.main_file, time=int(time))
        writer = open(filename, "w")

        self.tracker.save(writer)
        writer.close()
        setattr(self, lastname, datetime.now())

