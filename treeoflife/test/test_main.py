from __future__ import unicode_literals, print_function

import json

from twisted.internet.task import Clock
import pytest
import pprint

from treeoflife.main import JSONProtocol, RemoteInterface
from treeoflife import editor_launch
from treeoflife.test import util

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
        self.lineReceived(json.dumps(kw))

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
    tracker = RemoteInterface(Config, None, None, None,
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
    temp_protocol.lineReceived(tracker.edit_session.editor.json_data)
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

    temp_protocol.lineReceived(tracker.edit_session.editor.json_data)
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

    temp_protocol.lineReceived(tracker.edit_session.editor.json_data)
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

    temp_protocol.lineReceived(tracker.edit_session.editor.json_data)
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
    tracker = RemoteInterface(Config, None, None, None,
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
    protocol.lineReceived(response_message)
    protocol.accept_messages(
        {"editor_running": False},
        {"embedded_edit": None}
    )
    assert tracker.root.find(u"\xfcherp derp").one()
    assert not tracker.edit_session
