from __future__ import unicode_literals, print_function

import time
import json
import logging
import datetime
import random
import string

from twisted.internet.protocol import Protocol, DatagramProtocol
from twisted.internet.task import LoopingCall
from treeoflife import syncdata

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

    def sendmessage(self, message):
        self.send_line(json.dumps(message))

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
            self.tracker.sync_commit()
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


class SyncProtocol(LineOnlyReceiver):
    """
    See /sync_protocol for more information
    """

    def __init__(self, datasource, reactor=None):
        self.datasource = datasource

        self.remote_hashes = None
        self.init_remote_hash = None
        self.init_remote_hash_index = None
        self.diverged = False
        self.reactor = reactor

        self.remote_name = None
        self.initializing = True

    def connectionMade(self):
        """
        send CURRENT HASH message
        """

        # REMEMBER: can't send binary hashes over line-based protocol, we'd
        #           have a ((256-1)/256) ** 32 chance of cutting the hash,
        #           about 11%, it'd break about one in 10
        protocolversions = b"1"
        self.command(b"connect", self.datasource.name.encode("utf-8")
                                + b" " + protocolversions)
        self.command(b"currenthash", self.datasource.hash_history[-1])

    def connectionLost(self, reason):
        if self.datasource.connections.get(self.remote_name, None) is self:
            del self.datasource.connections[self.remote_name]

    def send_line(self, line):
        LineOnlyReceiver.send_line(self, line)

    def command(self, command, data):
        assert type(command) == str
        assert type(data) == str
        self.send_line(b"%s %s" % (command, data))

    def init_finished(self, hashes=None):
        self.initializing = False
        if self.remote_name is None:
            # failure to send connect message
            self.disconnect("connect message missed")
            raise BadProtocolWhatever

        if hashes is not None:
            self.remote_hashes = hashes
        else:
            self.remote_hashes = self.datasource.hash_history[:]
            self.datasource.not_diverged(self)

    def line_received(self, line):
        command, space, data = line.partition(b' ')
        del line

        try:
            handler = getattr(self, "message_%s" % command)
        except AttributeError:
            logger.error("Unrecognized sync message: %s", line)
            return

        handler(data)

    # ======================================================================
    #
    #     MESSAGE HANDLERS
    #

    # TODO: reconnect. omg reconnect.
    #      - partially solved by local discovery
    # TODO: auto-timeout, pings, keepalive
    # TODO: relay, relay upgrade

    def message_connect(self, remote_info):
        remote_name, space, protocolversions = remote_info.partition(b' ')
        self.remote_name = remote_name.decode("utf-8")
        if self.remote_name == self.datasource.name:
            # oops, connected to self
            self.disconnect("connected to self")

        existing = self.datasource.connections.get(self.remote_name, None)
        if existing is not None:
            self.disconnect("connection already present")
            return
        else:
            self.datasource.connections[self.remote_name] = self

        # if ever needed: versions = protocolversions.split(',')
        # ... then do something with it ...

    def message_currenthash(self, remotehash):
        found_index = None

        for rindex, value in enumerate(reversed(self.datasource.hash_history)):
            if value == remotehash:
                found_index = len(self.datasource.hash_history) - (rindex + 1)
                break

        if found_index is None:
            self.command(b"please_send", remotehash)
        else:
            self.init_remote_hash_index = found_index
            self.init_remote_hash = remotehash
            self.init_finished()

    def message_please_send(self, localhash):
        if localhash != self.datasource.hash_history[-1]:
            # bad state. let reconnection and such handle it
            self.disconnect("data changed during init")
            return

        message = b""
        if self.init_remote_hash is not None:
            idx = self.init_remote_hash_index
            hashes = self.datasource.hash_history[idx:]
            assert hashes[0] == self.init_remote_hash
            message += b" ".join(hashes)
            del hashes

            self.init_finished()
        else:
            # diverged!
            self.diverged = True
            message += b" ".join(self.datasource.hash_history)

        message += b" "
        message += syncdata._encode_data(self.datasource.data)

        self.command(b"history_and_data", message)

    def _unpack_update(self, message):
        values = message.split(b' ')

        data = values[-1]
        hashes = values[:-1]

        return data, hashes

    def message_history_and_data(self, message):
        # this can use a lot of memory, careful
        data, hashes = self._unpack_update(message)
        uncompressed = syncdata._decode_data(data)

        h = syncdata.sha256(uncompressed)
        assert hashes[-1] == h, "the other end sent derped data"

        if not self.diverged:
            if hashes[0] != self.datasource.hash_history[-1]:
                assert 0, "what do we do here?"

            self.datasource.hash_history.extend(hashes[1:])
            self.init_finished()

            self.datasource.data = uncompressed
            self.datasource.updated_by_connection()
            # TODO: parse data into tree
        else:
            # TODO: save to diverged data dir, inform user, etc
            self.init_finished(hashes)
            self.datasource.record_diverge(self, uncompressed)

    def message_new_data(self, message):
        data, hashes = self._unpack_update(message)
        uncompressed = syncdata._decode_data(data)
        h = syncdata.sha256(uncompressed)

        if self.datasource.hash_history[-1] in hashes:
            self.datasource.not_diverged(self)

            self.datasource.hash_history.append(h)
            self.remote_hashes.append(h)

            self.datasource.data = uncompressed
            self.datasource.updated_by_connection()
        elif self.remote_hashes[-1] == h:
            return
        elif not self.diverged:
            # TODO: big flashy warning somewhere!
            self.disconnect("bad state - runtime diverge")
            return
        else:
            assert self.remote_hashes[-1] in hashes
            self.remote_hashes.append(h)
            self.datasource.record_diverge(self, uncompressed)

    def data_changed(self, parents):
        d = syncdata._encode_data(self.datasource.data)

        self.command(b"new_data",
                b" ".join(parents) + b" " + d)

    def disconnect(self, reason):
        print(self.datasource.name, "XX", self.remote_name, reason)
        self.transport.loseConnection()


class DiscoveryProtocol(DatagramProtocol):
    def __init__(self, syncdata, port, connect_callback, interval=2):
        self.syncdata = syncdata
        self.port = port
        self.connect_callback = connect_callback
        self.looping_call = LoopingCall(self.announce)
        self.interval = interval
        self.cooldown = {}

    def startProtocol(self):
        self.transport.setBroadcastAllowed(True)
        if not self.looping_call.running:
            self.looping_call.start(self.interval)

    def stopProtocol(self):
        self.looping_call.stop()

    def announce(self):
        self.command(b"<broadcast>", b"announce",
                b"%s %s" % (
                    self.syncdata.group.encode("utf-8"),
                    self.syncdata.name.encode("utf-8")))

    def command(self, address, command, data):
        assert all(type(x) == str for x in (address, command, data))
        mid = b"".join(random.choice(string.lowercase)
                for x in range(15))
        self.transport.write(
                b"%s %s %s\n" % (mid, command, data),
                (address, self.port))

    def datagramReceived(self, datagram, addr):
        mid, space, message = datagram.strip().partition(b' ')
        command, space, data = message.partition(b' ')

        try:
            handler = getattr(self, "message_%s" % command)
        except AttributeError:
            logger.error("Unrecognized sync-announce message: %s", datagram)
            return

        # ignore remote port, assume it's the same. if it's not, err...
        handler(addr[0], data)

    def discovered(self, address, remote_name):
        if remote_name in self.syncdata.connections:
            # TODO: this ignores relay-upgrade and connections going bad
            return
        last_attempt = self.cooldown.get((address, remote_name), 0)
        now = time.time()
        if last_attempt > now - 30:
            # this is an expected state, between the time a node is
            # discovered and the time it's connected and init is finished
            logger.debug("attempting to reconnect too fast: %s (%s): %f",
                remote_name, address, now - last_attempt)
            return

        self.cooldown[(address, remote_name)] = now

        self.connect_callback(address)

    def message_announce(self, address, data):
        group, _, remote_name = data.partition(b' ')
        group = group.decode("utf-8")
        remote_name = remote_name.decode("utf-8")

        if group != self.syncdata.group:
            # treeoflife node belonging to a different user
            return

        if remote_name == self.syncdata.name:
            # whoops, got our own message. this is normal
            return

        self.discovered(address, remote_name)

        self.command(address, b"announce_reply",
                self.syncdata.name.encode("utf-8"))

    def message_announce_reply(self, address, remote_name):
        remote_name = remote_name.decode("utf-8")

        self.discovered(address, remote_name)
