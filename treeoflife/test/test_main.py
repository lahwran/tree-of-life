from __future__ import unicode_literals, print_function

import json

from twisted.internet.task import Clock
import pytest
import pprint

from treeoflife.main import JSONProtocol, RemoteInterface
from treeoflife import editor_launch
from treeoflife.test import util
from treeoflife import userinterface

# TODO: need to monkeypatch tempfile() to not clutter os temp directory


class NoIOProtocol(JSONProtocol):
    def __init__(self, *a, **kw):
        self.allowed = kw.pop("allowed")
        JSONProtocol.__init__(self, *a, **kw)
        self._is_transient_connection = True
        self.sent_messages = []
        self.accepted_messages = []
        self.do_raise = True
        self.transport = FakeTransport()

    def accept_messages(self, *messages):
        self.accepted_messages.extend(messages)
        assert self.sent_messages == self.accepted_messages

    def update(self):
        if "update" in self.allowed:
            return JSONProtocol.update(self)

    def update_all(self):
        if "update_all" in self.allowed:
            return JSONProtocol.update_all(self)

    def update_editor_running(self):
        if "update_editor_running" in self.allowed:
            return JSONProtocol.update_editor_running(self)

    def sendmessage(self, message):
        self.sent_messages.append(message)

    def receive(self, **kw):
        self.line_received(json.dumps(kw))

    def capture_error(self, e, message=None):
        if self.do_raise:
            raise
        else:
            JSONProtocol.capture_error(self, e, message)


@pytest.fixture
def tpc():
    class Config(object):
        editor = "test-editor"
        port = 12345

    clock = Clock()
    tracker = RemoteInterface(Config, None, None, None, False,
            reactor=clock)
    protocol = NoIOProtocol(tracker, clock, allowed={"update_editor_running"})
    tracker.listeners.append(protocol)

    assert not tracker.edit_session
    return tracker, protocol, clock


@editor_launch.editor_types.add("test-editor")
class EditorForTesting(editor_launch._TerminalLauncher):
    pass


class FakeTransport(object):
    def __init__(self):
        self.connected = True
        self.disconnecting = False

    def loseConnection(self):
        self.connected = False


def test_edit(tpc):
    tracker, protocol, clock = tpc

    protocol.receive(command="edit")

    protocol.accept_messages(
        {u"display": False},
        {u"editor_running": True}
    )
    assert tracker.edit_session.editor.command

    with open(tracker.edit_session.editor.tmp, "a") as writer:
        writer.write("\ncomment: \xfcherp derp\n".encode("utf-8"))

    temp_protocol = NoIOProtocol(tracker, clock, allowed=set())
    temp_protocol.line_received(tracker.edit_session.editor.json_data)
    assert not tracker.root.find(u"\xfcherp derp").first()
    protocol.accept_messages()
    assert not temp_protocol.transport.connected

    clock.advance(1)
    assert tracker.root.find(u"\xfcherp derp").one()
    assert not temp_protocol.sent_messages
    protocol.accept_messages(
        {u"editor_running": False},
        {u"display": True}
    )


def test_edit_nohide(tpc, monkeypatch):
    tracker, protocol, clock = tpc

    monkeypatch.setattr(EditorForTesting, "hide", False)

    protocol.receive(command="edit")

    protocol.accept_messages({u"editor_running": True})
    assert tracker.edit_session.editor.command

    with open(tracker.edit_session.editor.tmp, "a") as writer:
        writer.write("\ncomment: \xfcherp derp\n".encode("utf-8"))

    temp_protocol = NoIOProtocol(tracker, clock, allowed=set())

    temp_protocol.line_received(tracker.edit_session.editor.json_data)
    protocol.accept_messages()
    temp_protocol.accept_messages()
    assert not temp_protocol.transport.connected

    clock.advance(1)
    protocol.accept_messages({u"editor_running": False})


def test_edit_nochange(tpc, monkeypatch):
    tracker, protocol, clock = tpc
    root = tracker.root
    monkeypatch.setattr(EditorForTesting, "hide", False)
    protocol.receive(command="edit")

    protocol.accept_messages({u"editor_running": True})
    assert tracker.edit_session.editor.command

    temp_protocol = NoIOProtocol(tracker, clock, allowed=set())

    temp_protocol.line_received(tracker.edit_session.editor.json_data)
    protocol.accept_messages()
    temp_protocol.accept_messages()
    assert not temp_protocol.transport.connected

    clock.advance(1)
    protocol.accept_messages({u"editor_running": False})
    assert tracker.root is root


def test_edit_error(tpc):
    tracker, protocol, clock = tpc
    tracker.root.createchild("task", "test")
    protocol.receive(command="edit")

    assert protocol.sent_messages == [
        {u"display": False},
        {u"editor_running": True}
    ]
    protocol.sent_messages = []
    editor = tracker.edit_session.editor
    assert editor.command
    identifier = editor.identifier
    tmp = editor.tmp
    root = tracker.root

    with open(editor.tmp, "r") as reader:
        data = reader.read()
    with open(editor.tmp, "w") as writer:
        writer.write("\nday: dasfadsf\xfcherp derp\n".encode("utf-8"))
        writer.write(data)

    temp_protocol = NoIOProtocol(tracker, clock, allowed=set())
    temp_protocol.transport = FakeTransport()

    temp_protocol.line_received(tracker.edit_session.editor.json_data)
    assert not tracker.root.find(u"dasfadsf\xfcherp derp").first()
    assert not protocol.sent_messages
    assert not temp_protocol.transport.connected
    assert tracker.edit_session.editor.identifier == identifier
    assert tracker.edit_session.editor.tmp == tmp
    assert tracker.root is root

    protocol.do_raise = False
    clock.advance(1)
    assert not tracker.root.find(u"dasfadsf\xfcherp derp").first()
    assert tracker.edit_session.editor.identifier != identifier
    assert len(tracker.edit_session.editor.filenames) == 2
    assert tracker.edit_session.editor.error
    assert tracker.edit_session.editor.error_tmp
    assert tracker.root.find("test").one()
    assert not temp_protocol.sent_messages
    assert len(protocol.sent_messages) == 1
    assert protocol.sent_messages[0].keys() == ["error"]
    assert "LoadError" in protocol.sent_messages[0]["error"]


def test_edit_embedded():
    class Config(object):
        editor = "embedded"
        port = 12345

    clock = Clock()
    tracker = RemoteInterface(Config, None, None, None, False,
            reactor=clock)
    protocol = NoIOProtocol(tracker, clock, allowed={"update_editor_running"})
    tracker.listeners.append(protocol)

    protocol.receive(command="edit")
    protocol.accept_messages(
        {"embedded_edit": util.any},
        {"editor_running": True}
    )

    msg = dict(protocol.sent_messages[0]["embedded_edit"])
    assert msg["identifier"] == tracker.edit_session.editor.identifier
    data = msg["data"]
    assert data
    assert not msg["error"]

    data += "\ncomment: \xfcherp derp\n"

    response_message = json.dumps({
        "embedded_editor_finished": {
            "identifier": msg["identifier"],
            "data": data
        }
    })
    protocol.accept_messages()
    protocol.line_received(response_message)
    protocol.accept_messages(
        {"editor_running": False},
        {"embedded_edit": None}
    )
    assert tracker.root.find(u"\xfcherp derp").one()
    assert not tracker.edit_session


def test_receive_long_message():
    # long messages are used to transfer the entire life file.
    # they're allowed, darn you default twisted linereceiver

    length = 5000000  # 5MB
    called = []

    class Derp(NoIOProtocol):
        def message_huge(self, data):
            assert data == " " * length
            called.append(True)

    class Config(object):  # not really needed I think
        editor = "test-editor"
        port = 12345

    clock = Clock()
    tracker = RemoteInterface(Config, None, None, None, False,
            reactor=clock)
    protocol = Derp(tracker, clock, allowed={"update_editor_running"})

    protocol.dataReceived(json.dumps({"huge": " " * length}) + "\n")
    assert called == [True]


def test_stateful_command(tpc, monkeypatch):
    tracker, protocol, clock = tpc
    calls = []

    class TestCommand(userinterface.Command):
        def __init__(self, command_name, text, ui, root):
            assert type(self) == TestCommand
            assert text == "hello world" or text == "around the world"
            assert ui is tracker
            assert root is ui.root
            self.command_name = command_name
            self.text = text

        def preview(self):
            return {
                "preview": "something"
            }

        def execute(self):
            calls.append(self.text)

    monkeypatch.setitem(userinterface.global_commands.handlers,
            "testcommand", TestCommand)

    protocol.receive(input="testcommand hello world")
    assert protocol.parsed_command
    protocol.accept_messages({
        "command_preview": {
            "name": "testcommand",
            "text": "hello world",
            "data": {"preview": "something"}
        }
    })
    protocol.receive(command="testcommand hello world")
    assert not protocol.parsed_command
    protocol.accept_messages({
        "command_preview": None
    })

    protocol.receive(input="testcommand around the world")
    assert protocol.parsed_command
    protocol.accept_messages({
        "command_preview": {
            "name": "testcommand",
            "text": "around the world",
            "data": {"preview": "something"}
        }
    })
    protocol.receive(navigate="up")
    assert protocol.parsed_command
    protocol.accept_messages(
        {"input": "testcommand hello world"},
        {
            "command_preview": {
                "name": "testcommand",
                "text": "hello world",
                "data": {"preview": "something"}
            }
        }
    )
    protocol.receive(navigate="down")
    assert protocol.parsed_command
    protocol.accept_messages(
        {"input": "testcommand around the world"},
        {
            "command_preview": {
                "name": "testcommand",
                "text": "around the world",
                "data": {"preview": "something"}
            }
        }
    )
    protocol.receive(input="  ")
    assert not protocol.parsed_command
    protocol.accept_messages({
        "command_preview": None
    })

    assert calls == ["hello world"]


def test_update_event_queue_unique(tpc, setdt):
    setdt(2000, 1, 1, 1, 1)
    tracker, protocol, clock = tpc
    protocol.allowed = set()
    tracker.deserialize({"life":
        "event#herka: herp\n"
        "    @when: June 1 2011 3:30 AM\n"
        "task#doopa: herp\n"
        "    reference: #derpa\n"
        "    event#derka: derp"
        "        @when: June 1 2010 3:30 AM\n"
        "    event#asdfg: blah\n"
        "reference#derpa: #herka\n"
        "reference: #doopa\n"
    })

    protocol.allowed = {"update"}
    protocol.update()

    message = protocol.sent_messages[-1]
    assert message["event_queue"] == ["asdfg", "derka", "herka"]


def test_update_event_queue_finished(tpc, setdt):
    setdt(2000, 1, 1, 1, 1)
    tracker, protocol, clock = tpc
    protocol.allowed = set()
    tracker.deserialize({"life":
        "event#herka: herp\n"
        "    @when: June 1 2011 3:30 AM\n"
        "task#doopa: herp\n"
        "    event#derka: derp"
        "        @when: June 1 2010 3:30 AM\n"
        "    event#asdfg: blah\n"
        "        @finished\n"
    })

    protocol.allowed = {"update"}
    protocol.update()

    message = protocol.sent_messages[-1]
    assert message["event_queue"] == ["derka", "herka"]
