from __future__ import unicode_literals, print_function

import time
import json
import logging
import datetime
from twisted.internet.protocol import Protocol

logger = logging.getLogger(__name__)


class LineOnlyReceiver(Protocol):
    """
    Copied-and-edited version of twisted LineOnlyReceiver.
    I DON'T WANT A LENGTH LIMIT
    """
    _buffer = b''
    delimiter = b'\n'

    def dataReceived(self, data):
        """Translates bytes into lines, and calls line_received."""
        lines = (self._buffer + data).split(self.delimiter)
        self._buffer = lines.pop(-1)
        for line in lines:
            if self.transport.disconnecting:
                # this is necessary because the transport may be told to lose
                # the connection by a line within a larger packet, and it is
                # important to disregard all the lines in that packet following
                # the one that told it to close.
                return
            self.line_received(line)

    def line_received(self, line):
        """Override this for when each line is received.
        """
        raise NotImplementedError

    def send_line(self, line):
        """Sends a line to the other end of the connection.
        """
        return self.transport.writeSequence((line, self.delimiter))


class JSONProtocol(LineOnlyReceiver):
    def error(self, message):
        pass

    def capture_error(self, err, message):
        pass

    def line_received(self, line):
        try:
            document = json.loads(line)
        except ValueError:
            logger.exception("Error loading line: %r", line)
            self.error("exception, see console")
            return

        for key, value in document.items():
            try:
                handler = getattr(self, "message_%s" % key)
            except AttributeError:
                logger.info("unrecognized message: %s = %s", key, value)
                self.error("exception, see console")
                continue
            try:
                handler(value)
            except Exception as e:
                logger.exception("error running handler")
                self.capture_error(e, "UNEXPECTED, SEE CONSOLE")


class UIProtocol(JSONProtocol):
    def __init__(self, tracker, reactor):
        self.tracker = tracker
        self._is_transient_connection = False
        self.command_history = [""]
        self.command_index = 0
        self.update_timeout = None
        self.reactor = reactor
        self.parsed_command_text = None
        self.parsed_command = None
        self.current_preview = None

    def connectionLost(self, reason):
        if not self._is_transient_connection:
            if (self.tracker.edit_session
                    and self.tracker.edit_session.source is self):
                self.tracker.edit_session.editor.source_died()
            try:
                self.tracker.listeners.remove(self)
            except ValueError:
                logger.exception("Error removing listener from listeners")
            logger.info("connection lost: %r", reason)

    def sendmessage(self, message):
        self.send_line(json.dumps(message))

    def update(self):
        if self.update_timeout is not None and self.update_timeout.active():
            self.update_timeout.cancel()
        self.update_timeout = self.reactor.callLater(600, self.update)
        self.update_editor_running()

        try:
            reversed_displaychain = self.tracker.displaychain()[::-1]
            root = self.tracker.root
            pool = root.ui_graph()
            active_ref = getattr(root.active_node, "_px_root", None)
            todo = getattr(root, "todo", None)
            if todo is not None:
                todo_id = todo.id
            else:
                todo_id = None
            pool["ids"] = {
                "root": root.id,
                "days": "00001",
                "active": root.active_node.active_id,
                "active_ref": active_ref.id if active_ref else None,
                "todo_bucket": todo_id
            }
            upcoming_events = {
                    event.id: event for event in root.find("** > event")
                    if (not event.when
                        or event.when >= datetime.datetime.now())
                        and not event.finished
            }
            upcoming_events = sorted(upcoming_events.values(),
                    key=lambda event: (int(bool(event.when)), event.when)
            )
            self.sendmessage({
                "promptnodes": [node.id for node in reversed_displaychain],
                "pool": pool,
                "event_queue": [event.id for event in upcoming_events],
            })
            self.tracker.auto_save()
        except Exception:
            logger.exception("Error updating")
            try:
                self.sendmessage({
                    "prompt": ["** see console **", " ** update error **"],
                })
            except Exception:
                logger.exception("Error sending update notification")
                self.error("exception")

    def update_editor_running(self):
        self.sendmessage({
            "editor_running": self.tracker.edit_session is not None
        })

    def error(self, new_error):
        self.sendmessage({"error": new_error})

    def capture_error(self, e, message=None):
        stred = str(e)
        name = type(e).__name__
        if name != "Exception" and stred:
            formatted = "%s: %s" % (name, stred)
        elif stred:
            formatted = stred
        else:
            formatted = name
        if message is not None:
            formatted = message + " " + formatted
        self.error(formatted)

    def message_input(self, text_input):
        prev = self.command_history[self.command_index]
        self.command_history[self.command_index] = text_input
        self._update_command()

    def message_navigate(self, direction):
        shift = -1 if direction == "up" else 1

        prev = self.command_index
        self.command_index += shift

        if self.command_index < 0:
            self.command_index = 0
        elif self.command_index >= len(self.command_history):
            self.command_index = len(self.command_history) - 1

        logger.info("navigate history: %s - %s", self.command_index,
                self.command_history[self.command_index])
        if prev == self.command_index:
            return

        self.sendmessage({"input": self.command_history[self.command_index]})
        self._update_command()

    def _update_command(self, preview=True):
        text = self.command_history[self.command_index]
        old = self.parsed_command_text
        if text == old:
            return

        if text is None:
            self.parsed_command = None
        else:
            command = self.tracker.parse_command(self, text)
            self.parsed_command = command

        if not preview:
            return

        if self.parsed_command is None:
            value = None
        else:
            value = command._full_preview()
        old_preview = self.current_preview
        self.current_preview = value
        if old_preview == value:
            return
        self.sendmessage({"command_preview": value})

    def message_command(self, command):
        self.command_history[self.command_index] = command
        self._update_command(preview=False)
        logger.info("command commit: %r -> %s",
                command,
                repr(self.parsed_command))
        initial = time.time()
        self.command_index = len(self.command_history)
        self.command_history.append("")
        try:
            self.parsed_command.execute()
        except Exception as e:
            logger.exception("Error running command")
            self.capture_error(e)
        else:
            final = time.time()
            logger.debug("command commit took: %r", final - initial)
            self.tracker.update_all()
        self._update_command()

    def message_display(self, is_displayed):
        pass

    def message_file_editor_finished(self, identifier):
        self._is_transient_connection = True
        self.reactor.callLater(0, self.tracker._editor_finished,
                identifier=identifier)
        self.transport.loseConnection()

    def message_embedded_editor_finished(self, info):
        self.tracker._embedded_editor_finished(
                info["identifier"], info["data"])

    def message_ui_connected(self, ignoreme):
        self._is_transient_connection = False
        try:
            self.sendmessage({
                "max_width": self.tracker.config["max_width"]
            })
            self.sendmessage({
                "display": True
            })
            self.update()
            self.tracker.listeners.append(self)
        except Exception:
            logger.exception("Error sending info on connection")
