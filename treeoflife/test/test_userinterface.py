from __future__ import unicode_literals, print_function

import pytest
from twisted.internet.task import Clock

from treeoflife import userinterface
from treeoflife import exceptions
from treeoflife.tracker import Tracker


class Test_makenode(object):
    def test_makenode_indent(self, monkeypatch):
        result = 1, False, u"abcde", u"\xfcnode_type", u"\xfctext"
        monkeypatch.setattr(userinterface, "parse_line", lambda string: result)

        with pytest.raises(exceptions.InvalidInputError):
            userinterface._makenode(u"\xfcsentinel")

    def test_makenode_metadata(self, monkeypatch):
        result = 0, True, u"abcde", u"node_type", u"text"
        monkeypatch.setattr(userinterface, "parse_line", lambda string: result)

        with pytest.raises(exceptions.InvalidInputError):
            userinterface._makenode(u"\xfcsentinel")

    def test_makenode(self):
        assert userinterface._makenode(u"\xfctask: \xfctest") == (
                u"\xfctask", u"\xfctest")


class TestGenerateListing(object):
    def stuff(self):
        tracker = Tracker(skeleton=False)
        tracker.root.createchild("_gennode", "herp")
        derp = tracker.root.createchild("_gennode", "derp")
        active = derp.createchild("task", "honk")
        return tracker, derp, active

    def test_simple(self):
        tracker, derp, active = self.stuff()

        result = userinterface.generate_listing(active, tracker.root)

        assert result == [
            "  life",
            "      _gennode: herp",
            "      _gennode: derp",
            ">         task: honk"
        ]


def test_command(monkeypatch):
    clock = Clock()
    interface = userinterface.CommandInterface(reactor=clock, skeleton=False)
    calls = []

    def testhandler(text, ui, command_name, root):
        calls.append(command_name)
        assert text == "this is my text"
        assert ui is interface
        assert root is ui.root

    class PreviewableHandler(userinterface.Command):
        def __init__(self, command_name, text, ui, root):
            assert type(self) == PreviewableHandler
            assert text == "this is my text"
            assert ui is interface
            assert root is ui.root
            self.command_name = command_name

        def preview(self):
            return {"command_name": self.command_name}

        def execute(self):
            calls.append(self.command_name)

    monkeypatch.setitem(userinterface.global_commands.handlers,
            "testhandler", testhandler)
    monkeypatch.setitem(userinterface.global_commands.handlers,
            "previewable", PreviewableHandler)

    command = interface.parse_command(None, "testhandler this is my text")
    assert command.preview() == {}
    assert command._full_preview() == {
        "name": "testhandler",
        "text": "this is my text",
        "data": {}
    }
    command.execute()

    command = interface.parse_command(None, "previewable this is my text")
    assert command.command_name
    assert command.preview() == {"command_name": "previewable"}
    assert command._full_preview() == {
        "name": "previewable",
        "text": "this is my text",
        "data": {"command_name": "previewable"}
    }
    command.execute()

    assert calls == ["testhandler", "previewable"]
