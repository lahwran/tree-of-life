import pytest

from zope.interface import implementer
from crow2.adapterutil import fakeimplementeds, IFile

from todo_tracker.tracker import  Tracker, GenericNode, LoadError
from todo_tracker.file_storage import serialize_to_str
from todo_tracker.test.util import FakeNodeCreator

class TestTrackerLoad(object):
    def test_basic(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator())
        lines = (
            "firstchild: args\n"
            "    secondchild: other args\n"
            "        @option: data\n"
            "        thirdchild: herp derp\n"
            "    fourthchild: ark dark\n"
        )
        tracker_obj.load(lines)

        root = tracker_obj.root
        root_child0 = root.children.next_neighbor
        assert root_child0.text == "args"
        assert root_child0.node_type == "firstchild"

        root_child0_child0 = root_child0.children.next_neighbor
        assert root_child0_child0.text == "other args"
        assert root_child0_child0.node_type == "secondchild"
        assert root_child0_child0.metadata["option"] == "data"

        root_child0_child0_child0 = root_child0_child0.children.next_neighbor
        assert root_child0_child0_child0.text == "herp derp"
        assert root_child0_child0_child0.node_type == "thirdchild"

        root_child0_child1 = root_child0_child0.next_neighbor
        assert root_child0_child1.text == "ark dark"
        assert root_child0_child1.node_type == "fourthchild"

    def test_bad_order(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator())

        lines = (
            "firstchild: args\n"
            "    secondchild: other args\n"
            "    @option: this won't work here\n"
        )
        with pytest.raises(LoadError):
            tracker_obj.load(lines)

    def test_continued_text(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator())
        lines = (
            "category: derp\n"
            "    - herp\n"
            "    - derp\n"
        )
        tracker_obj.load(lines)

class TestTrackerSave(object):
    def test_basic(self):
        tracker = Tracker(nodecreator=FakeNodeCreator())

        node1 = GenericNode("node1", "node1_text", tracker.root, tracker)
        tracker.root.addchild(node1)
        node2 = GenericNode("node2", "node2_text", tracker.root, tracker)
        tracker.root.addchild(node2)
        node3 = GenericNode("node3", None, tracker.root, tracker)
        tracker.root.addchild(node3)

        node1_1 = GenericNode("node1_1", "node1_1_text", node1, tracker)
        node1_1.setoption("herp", "derp")
        node1.addchild(node1_1)

        node1_2 = GenericNode("node1_2", "node1_2_text", node1, tracker)
        node1_2.continue_text("herk derk")
        node1.addchild(node1_2)

        node2_1 = GenericNode("node2_1", "node2_1_text", node2, tracker)
        node2_1.setoption("hark", "dark")
        node2_1.continue_text('honk donk')
        node2.addchild(node2_1)

        @implementer(IFile)
        class WriteTarget(object):
            def __init__(self):
                self.text = ""

            def write(self, text):
                self.text = text

        target = WriteTarget()
        tracker.save(target)
        assert target.text == (
            "node1: node1_text\n"
            "    node1_1: node1_1_text\n"
            "        @herp: derp\n"
            "    node1_2: node1_2_text\n"
            "        - herk derk\n"
            "node2: node2_text\n"
            "    node2_1: node2_1_text\n"
            "        - honk donk\n"
            "        @hark: dark\n"
            "node3\n"
        )


def test_life():
    tracker = Tracker()
    input_str = (
        "days\n"
        "    day: July 13, 2012\n"
        "        task: get up\n"
        "        event: work\n"
        "            @started: July 12, 2012 09:00 AM\n"
        "            event: standup\n"
        "            task: do stuff\n"
        "                @active\n"
        "            task: do other stuff\n"
        "        task: work on todo tracker\n"
    )
    tracker.load(input_str)

    asdf = serialize_to_str(tracker.root)
    assert asdf == input_str

def test_activate_next():
    tracker = Tracker()
    input_str = (
        "task: 0\n"
        "    task: 0.1\n"
        "        task: 0.1.2\n"
        "            @active\n"
        "    task: 0.2\n"
        "        task: 0.2.1\n"
    )
    output_str = (
        "task: 0\n"
        "    task: 0.1\n"
        "        task: 0.1.2\n"
        "    task: 0.2\n"
        "        task: 0.2.1\n"
        "            @active\n"
    )

    tracker.load(input_str)
    tracker.activate_next()
    asdf = serialize_to_str(tracker.root)
    print asdf
    print output_str
    assert asdf == output_str

def test_random_insertion(monkeypatch):
    tracker = Tracker()

    input_str = (
        "task: 0\n"
        "task: 2\n"
        "    @active\n"
        "task: 4\n"
    )

    tracker.load(input_str)

    tracker.create_before("task", "1")
    tracker.create_after("task", "1.5")

    tracker.activate_next()

    tracker.create_after("task", "3")

    while True:
        try:
            tracker.activate_next()
        except StopIteration:
            break

    while True:
        try:
            tracker.activate_prev()
        except StopIteration:
            break

    while True:
        try:
            tracker.activate_next()
        except StopIteration:
            break

    expected_str = (
        "task: 0\n"
        "task: 1\n"
        "task: 1.5\n"
        "task: 2\n"
        "task: 3\n"
        "task: 4\n"
        "    @active\n"
    )

    serialized = serialize_to_str(tracker.root)
    assert serialized == expected_str
