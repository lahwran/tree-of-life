from __future__ import unicode_literals, print_function

import traceback
import os
import json
import subprocess
from functools import partial
import datetime
import time
import logging
import inspect
import itertools

from treeoflife.file_storage import parse_line
from treeoflife.nodes.node import nodecreator, TreeRootNode
from treeoflife.tracker import Tracker
from treeoflife.exceptions import InvalidInputError
from treeoflife.util import tempfile, HandlerDict, Profile
from treeoflife.parseutil import Grammar
from treeoflife import timefmt
from treeoflife import alarms

logger = logging.getLogger(__name__)


def _makenode(string):
    indent, is_metadata, nodeid, node_type, text = parse_line(string)
    if is_metadata:
        raise InvalidInputError("metadata not allowed")
    if indent > 0:
        raise InvalidInputError("plz 2 not indent")
    return node_type, text


global_commands = HandlerDict()
command = global_commands.add


import treeoflife.navigation


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
        generate_listing(active, child, lines, indent + 1)
    return lines


class Event(object):
    def __init__(self, source, root, command_name, text, ui):
        self.source = source
        self.root = root
        self.command_name = command_name
        self.text = text
        self.ui = ui
        self.event = self

    def _inject(self, function):
        func_args = inspect.getargs(function.__code__).args
        call = {}
        for arg in func_args:
            call[arg] = getattr(self, arg)
        return function(**call)


class MixedAlarmRoot(TreeRootNode, alarms.RootMixin):
    pass


class CommandInterface(Tracker, alarms.TrackerMixin):
    max_format_depth = 2
    _default_command = "createauto"

    def __init__(self, *args, **kwargs):
        kwargs["roottype"] = MixedAlarmRoot
        self._reactor = kwargs.pop("reactor")
        Tracker.__init__(self, *args, **kwargs)

    def _command(self, source, command_name, text):
        logger.info("command begin: %r, %r, %r", source, command_name, text)
        initial = time.time()
        try:
            target = global_commands.handlers[command_name]
        except KeyError:
            self.errormessage(source, "no such command %r" % command_name)
        else:
            event = Event(source, self.root, command_name, text, self)
            event._inject(target)
            final = time.time()
            logger.info("command took: %r", final - initial)

    def command(self, source, line):
        if not line.strip():
            return

        command_name, center, command_text = line.partition(" ")
        if command_name not in global_commands.handlers:
            command_text = line
            command_name = self._default_command

        self._command(source, command_name, command_text)

    def errormessage(self, source, message):
        logger.error(message)

    def display_lines(self, lines):
        pass

    def displaychain(self, limit=True):
        if limit:
            return [x[0] for x in zip(self.root.active_node.iter_parents(),
                                      range(self.max_format_depth))]
        else:
            return list(self.root.active_node.iter_parents())

    def tree_context(self, max_lines=55):
        active = self.root.active_node
        current = active.find("<day").one()
        days = current.parent
        root = self.root

        lines = []
        lines.append(_listing_node(active, days, 0))
        if current.prev_neighbor:
            lines.append(_listing_node(None, "...", 1))
        while len(lines) < max_lines and current:
            generate_listing(active, current, lines, indent=1)
            current = current.next_neighbor
        return lines


class Git(object):
    def __init__(self, path):
        self.path = path

    def init(self):
        if not os.path.isdir(os.path.join(self.path, ".git")):
            self._git("init")

    def gitignore(self, names):
        if not os.path.exists(os.path.join(self.path, ".gitignore")):
            with open(os.path.join(self.path, ".gitignore"), "w") as writer:
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
    def __init__(self, directory, main_file,
            config_file="config.json",
            autosave_template="_{main_file}_autosave_{time}",
            backup_template="_{main_file}_backup_{time}", **kw):
        super(SavingInterface, self).__init__(**kw)

        if directory is None:
            self.save_dir = None
            return
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

    def _load_file(self, filename, callback):
        try:
            reader = open(os.path.realpath(filename), "r")
        except IOError:
            return None
        else:
            return callback(reader)

    def load(self):
        if self.save_dir is None:
            return
        config = self._load_file(self.config_file, json.load)
        if config:
            self.config = config
        self._load_file(self.save_file, partial(self.deserialize, "file"))

    def full_save(self):
        if self.save_dir is None:
            return
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self.git.init()

        with open(self.config_file, "w") as writer:
            json.dump(self.config, writer, sort_keys=True,
                    indent=4)
        self.git.add(self.config_file)

        with open(self.save_file, "w") as writer:
            self.serialize("file", writer)
        self.git.add(self.save_file)

        self.git.gitignore(["_*"])
        self.git.add(".gitignore")

        self.git.commit("Full save %s" %
                datetime.datetime.now().strftime(self.timeformat))
        self.last_full_save = datetime.datetime.now()

    def auto_save(self):
        if self.save_dir is None:
            return
        self._special_save(self.autosave_file, self.autosave_id,
                self.autosave_minutes, "last_auto_save")

    def _special_save(self, name_format, time, freq, lastname):
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        last = getattr(self, lastname)
        if last and datetime.datetime.now() < last + datetime.timedelta(
                                                        minutes=freq):
            return

        filename = name_format.format(main_file=self.main_file, time=int(time))
        with open(filename, "w") as writer:
            self.serialize("file", writer)
        setattr(self, lastname, datetime.datetime.now())
