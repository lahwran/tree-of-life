from __future__ import unicode_literals, print_function

import platform
import traceback
import os
import subprocess
from functools import partial
import datetime
import time
import logging
import inspect
import itertools
import glob

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


class Command(object):
    def _full_preview(self):
        return {
            "name": self.event.command_name,
            "text": self.event.text,
            "data": self.preview()
        }


class FunctionCommand(Command):
    def __init__(self, event, function, args):
        self.function = function
        self.args = args
        self.event = event

    def execute(self):
        self.function(**self.args)

    def preview(self):
        return {}


@command("previewtestcommand")
class TestingCommand(Command):
    def preview(self):
        return {"preview": "derp"}

    def execute(self):
        pass


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

    def _inject(self, callable_):
        isfunction = not hasattr(callable_, "execute")
        f = callable_ if isfunction else callable_.__init__
        if f == object.__init__:
            func_args = []
        else:
            func_args = inspect.getargs(f.__code__).args
        call = {}
        for arg in func_args:
            if arg == "self":
                continue
            call[arg] = getattr(self, arg)
        if isfunction:
            return FunctionCommand(self, callable_, call)
        else:
            result = callable_(**call)
            result.event = self
            return result


class MixedAlarmRoot(TreeRootNode, alarms.RootMixin):
    pass


class CommandInterface(Tracker, alarms.TrackerMixin):
    max_format_depth = 2
    _default_command = "createauto"

    def __init__(self, *args, **kwargs):
        kwargs["roottype"] = MixedAlarmRoot
        self._reactor = kwargs.pop("reactor")
        Tracker.__init__(self, *args, **kwargs)

    def parse_command(self, source, line):
        if not line.strip():
            return
        logger.debug("command parse and init: %s", repr(line))
        initial = time.time()

        command_name, center, command_text = line.partition(" ")
        if command_name not in global_commands.handlers:
            command_text = line
            command_name = self._default_command

        target = global_commands.handlers[command_name]

        event = Event(source, self.root, command_name, command_text, self)
        command = None
        try:
            command = event._inject(target)
        finally:
            final = time.time()
            logger.debug("command parse and init: %r -> %s", final - initial,
                    repr(command))
        return command

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

        self.binary = self._which("git")

    def _which(self, name):
        """
        Borrowed from twisted.python.procutils, but modified so I can edit PATH
        """
        flags = os.X_OK
        result = []
        exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
        path = [x for x in os.environ.get('PATH', '').split(os.pathsep) if x]

        if platform.system() == "Windows":
            directories = glob.glob("c:/*rogram*iles*/*git*/*bin*/")
            path.extend(directories)

        if not path:
            return []
        for p in path:
            p = os.path.join(p, name)
            if os.access(p, flags):
                result.append(p)
            for e in exts:
                pext = p + e
                if os.access(pext, flags):
                    result.append(pext)

        if not result:
            paths = "\n".join("    %s" % x for x in path)
            raise RuntimeError("Couldn't find %s in:\n%s" % (name, paths))

        return result[0]

    def init(self):
        if not os.path.isdir(os.path.join(self.path, ".git")):
            self._git("init")
            self._setcommitter()

    def gitignore(self, names):
        if not os.path.exists(os.path.join(self.path, ".gitignore")):
            with open(os.path.join(self.path, ".gitignore"), "w") as writer:
                for name in names:
                    writer.write("%s\n" % name)

    def add(self, *filenames):
        self._git("add", *filenames)

    def commit(self, message, was_retry=False):
        success = self._git("commit", "-m", message)
        if not success and not was_retry:
            self._setcommitter()
            self.commit(message, True)

    def _setcommitter(self):
        if not self._git("config", "user.name"):
            self._git("config", "user.name", "treeoflife-autocommit")
        if not self._git("config", "user.email"):
            self._git("config", "user.email", "treeoflife@localhost")

    def _git(self, *args):
        result = subprocess.call(
                [self.binary] + list(args), cwd=self.path)
        return result == 0


class SavingInterface(CommandInterface):

    # TODO: move this somewhere more sensible (it's fine here for a while)

    def __init__(self, directory, main_file, **kw):
        super(SavingInterface, self).__init__(**kw)

        if directory is None:
            self.save_dir = None
            return
        self.save_dir = os.path.realpath(os.path.expanduser(directory))

        self.last_auto_save = None
        self.last_full_save = None

        now = datetime.datetime.now()
        self.autosave_dir = os.path.join(
            self.save_dir,
            now.strftime("_autosave/%Y-%m-%d/%H.%M.%S/")
        )
        self.autosave_minutes = datetime.timedelta(minutes=5)

        self.git = Git(self.save_dir)

    def load(self):
        if self.save_dir is None:
            return

        return CommandInterface.load(self, self.save_dir)

    def save(self):
        if self.save_dir is None:
            return
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self.git.init()

        CommandInterface.save(self, self.save_dir)

        self.git.add("config.json")
        for filename in self.filenames:
            self.git.add(os.path.join(self.save_dir, filename))

        self.git.gitignore(["_*"])
        self.git.add(".gitignore")

        self.git.commit("Full save %s" %
                datetime.datetime.now().strftime("%A %B %d %H:%M:%S %Y"))
        self.last_full_save = datetime.datetime.now()

    def auto_save(self):
        if self.save_dir is None:
            return
        last = self.last_auto_save
        if last and datetime.datetime.now() < last + self.autosave_minutes:
            return

        if not os.path.exists(self.autosave_dir):
            os.makedirs(self.autosave_dir)

        CommandInterface.save(self, self.autosave_dir)

        self.last_auto_save = datetime.datetime.now()
