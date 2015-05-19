from __future__ import unicode_literals, print_function

import traceback
import subprocess
import os
import logging
import uuid
import json

from treeoflife.userinterface import command
from treeoflife.util import tempfile, Profile, HandlerDict

logger = logging.getLogger(__name__)


editor_types = HandlerDict()


@command()
def editpudb(ui, source):  # pragma: no cover
    import pudb
    pudb.set_trace()
    edit(ui, source)


@command()
def edit(ui, source):
    ui.edit_session = EditSession(ui, source)


class EditSession(object):
    def __init__(self, ui, source):
        self.ui = ui
        self.source = source
        name = ui.run_config.editor
        self.EditorType = editor_types.handlers[name]

        if self.EditorType.hide:
            ui.hide_all_clients()

        self.exceptions = []
        self.original_data = ui.serialize()
        self.old_root = self.ui.root

        self.editor = self.EditorType(self, self.original_data["life"])

    def editor_done(self, edited_text):
        if edited_text == self.original_data["life"]:
            logger.info("text same, not loading")
            self.succeeded()
            return True

        try:
            with Profile("deserialize"):
                data = dict(self.original_data)
                data["life"] = edited_text
                self.ui.deserialize(data)
        except Exception as e:
            logger.exception("Failure loading")
            self.source.capture_error(e)
            formatted = traceback.format_exc()
            self.ui.root = self.old_root
            self.editor = self.EditorType(self, edited_text, error=formatted)
        else:
            logger.info("loaded; new active: %r", self.ui.root.active_node)
            self.succeeded()
            return True
        return False

    def succeeded(self):
        self.editor = None
        self.ui.edit_session = None
        self.ui.update_all()
        self.ui.optimize_and_commit()
        if self.EditorType.hide:
            self.ui.show_client(self.source)


class _TerminalLauncher(object):
    hide = True
    outer_command = b'exec bash -c "%s"\n'

    base_inner_command = (b"vim %s;echo '%s' "
                b"| base64 --decode| nc 127.0.0.1 %d")

    def __init__(self, session, contents, error=None):
        self.session = session
        self.filenames = []
        self.tmp = tempfile()
        self.tmp_backup = tempfile()
        self.filenames.append(self.tmp)
        port = session.ui.run_config.port

        data = contents.encode("utf-8")
        with open(self.tmp, "w") as writer:
            writer.write(data)
        with open(self.tmp_backup, "w") as writer:
            writer.write(data)

        self.error = error
        if error is not None:
            self.error_tmp = tempfile()
            with open(self.error_tmp, "w") as writer:
                writer.write(error.encode("utf-8"))
            self.filenames.append(self.error_tmp)

        args = self.shell_escape([b"-o", b"--"] + list(self.filenames))

        self.identifier = str(uuid.uuid4())
        self.json_data = json.dumps({
            "file_editor_finished": self.identifier}) + "\n"
        b64_data = self.json_data.encode("base64")
        b64_data = b64_data.replace(b" ", b"").replace(b"\n", b"")

        inner_command = self.base_inner_command % (
                b" ".join(args), b64_data, port)
        inner_command = inner_command.replace(b"\\'", b"'\"'\"'")
        self.command = self.outer_command % inner_command
        logger.info("Starting terminal editor with id %r: %s",
                self.identifier, self.command)

    def shell_escape(self, args):
        # Yes, I'm trying to do shell escaping. restricted inputs, so I'm not
        # too concerned; user input will never be passed to this.
        wrapped_args = []
        for arg in args:
            assert "'" not in arg, ("Can't put quotes in args! (sorry, "
                                "I know it's awkward and hacky)")
            wrapped_args.append(b"'%s'" % arg)
        return wrapped_args

    def done(self):
        with open(self.tmp, "r") as reader:
            data = reader.read().decode("utf-8")
        self.session.editor_done(data)

    def command_attempted(self):
        pass

    def source_died(self):
        pass


@editor_types.add("vim-iterm")
class ItermLauncher(_TerminalLauncher):  # pragma: no cover
    """
    Tell iterm2 to open a new window, then run a command that runs $EDITOR;
    after $EDITOR finishes, the command will send a json message to the main
    port
    """

    applescript = b"""
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
    """

    def __init__(self, *a, **kw):
        _TerminalLauncher.__init__(self, *a, **kw)

        self.tempfile = tempfile()
        with open(self.tempfile, "w") as temp_writer:
            temp_writer.write(self.command)

        self.osascript(self.applescript.format(tempfile=self.tempfile))

    def command_attempted(self):
        self.osascript(
            b'tell application "iTerm"\n'
            b'    activate\n'
            b'end tell\n'
        )

    def osascript(self, code):
        temp_code = tempfile()
        with open(temp_code, "w") as code_writer:
            code_writer.write(code)
        subprocess.call([b"osascript", temp_code])
        os.unlink(temp_code)


@editor_types.add("embedded")
class EmbeddedEditor(object):
    hide = False

    def __init__(self, session, contents, error=None):
        self.session = session
        self.identifier = str(uuid.uuid4())

        self.message = {
            "embedded_edit": {
                "identifier": self.identifier,
                "data": contents,
                "error": error
            }
        }
        self.logfile = tempfile()
        with open(self.logfile, "a") as writer:
            writer.write(json.dumps(self.message))
            writer.write('\n')
        logger.info("Starting embedded editor (logfile %s)",
                self.logfile)
        self.session.source.sendmessage(self.message)

    def done(self, data):
        with open(self.logfile, "a") as writer:
            writer.write(json.dumps(data))
            writer.write('\n')
        if data is None:
            data = self.session.original_data["life"]
        logger.info("attempting to stop embedded editor")
        if self.session.editor_done(data):
            self.session.source.sendmessage({"embedded_edit": None})

    def command_attempted(self):
        pass

    def source_died(self):
        self.session.succeeded()
