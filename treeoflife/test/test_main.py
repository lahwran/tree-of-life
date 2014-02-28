from __future__ import unicode_literals, print_function

import json

from twisted.internet.task import Clock

from treeoflife.main import JSONProtocol, RemoteInterface
from treeoflife import editor_launch

# TODO: need to monkeypatch tempfile() to not clutter os temp directory


class NoIOProtocol(JSONProtocol):
    def __init__(self, *a, **kw):
        self.allowed = kw.pop("allowed")
        JSONProtocol.__init__(self, *a, **kw)
        self._is_transient_connection = True
        self.sent_messages = []

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
        raise


@editor_launch.editor_types.add("test-editor")
class EditorForTesting(editor_launch._TerminalLauncher):
    pass


class FakeTransport(object):
    def __init__(self):
        self.connected = True

    def loseConnection(self):
        self.connected = False


def test_edit():

    class Config(object):
        editor = "test-editor"
        port = 12345

    clock = Clock()
    tracker = RemoteInterface(Config, None, None, None,
            reactor=clock)
    protocol = NoIOProtocol(tracker, clock, allowed={"update_editor_running"})
    tracker.listeners.append(protocol)

    assert not tracker.edit_session

    protocol.receive(command="edit")

    assert protocol.sent_messages == [
        {u"display": False},
        {u"editor_running": True}
    ]
    protocol.sent_messages = []
    assert tracker.edit_session
    assert tracker.edit_session.editor
    assert tracker.edit_session.editor.command

    with open(tracker.edit_session.editor.tmp, "a") as writer:
        writer.write("\ncomment: \xfcherp derp\n".encode("utf-8"))

    temp_protocol = NoIOProtocol(tracker, clock, allowed=set())
    temp_protocol.transport = FakeTransport()

    temp_protocol.lineReceived(tracker.edit_session.editor.json_data)
    assert not tracker.root.find(u"\xfcherp derp").first()
    assert not protocol.sent_messages
    assert not temp_protocol.transport.connected

    clock.advance(1)
    assert tracker.root.find(u"\xfcherp derp").one()
    assert not temp_protocol.sent_messages
    assert protocol.sent_messages == [
        {u"editor_running": False},
        {u"display": True}
    ]
