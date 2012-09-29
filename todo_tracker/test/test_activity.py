import pytest

from todo_tracker import activity
from todo_tracker import exceptions
from todo_tracker.tracker import Tracker

class Test_makenode(object):
    def test_makenode_indent(self, monkeypatch):
        result = 1, False, "node_type", "text"
        monkeypatch.setattr(activity, "parse_line", lambda string: result)

        with pytest.raises(exceptions.InvalidInputError):
            activity._makenode("sentinel")
            
    def test_makenode_metadata(self, monkeypatch):
        result = 0, True, "node_type", "text"
        monkeypatch.setattr(activity, "parse_line", lambda string: result)

        with pytest.raises(exceptions.InvalidInputError):
            activity._makenode("sentinel")

    def test_makenode(self):
        assert activity._makenode("task: test") == ("task", "test")

class TestGenerateListing(object):
    def stuff(self):
        tracker = Tracker(auto_skeleton=False)
        tracker.root.createchild("_gennode", "herp")
        derp = tracker.root.createchild("_gennode", "derp")
        active = derp.createchild("_genactive", "honk")
        return tracker, derp, active

    def test_simple(self):
        tracker, derp, active = self.stuff()

        result = activity.generate_listing(active, tracker.root)

        assert result == [
            "  life",
            "      _gennode: herp",
            "      _gennode: derp",
            ">         _genactive: honk"
        ]