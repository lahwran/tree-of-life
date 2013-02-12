import itertools

import pytest

from todo_tracker.nodes import GenericNode, GenericActivate
from todo_tracker.nodes.node import TreeRootNode
from todo_tracker.file_storage import serialize_to_str
from todo_tracker.test.util import FakeNodeCreator
from todo_tracker import exceptions

from todo_tracker.tracker import Tracker


class TestTracker(object):
    def test_load_basic(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator(),
                skeleton=False)
        lines = (
            "firstchild: args\n"
            "    secondchild: other args\n"
            "        @option: data\n"
            "        thirdchild: herp derp\n"
            "    fourthchild: ark dark\n"
        )
        tracker_obj.deserialize("str", lines)

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

    def test_load_bad_order(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator(),
                skeleton=False)

        lines = (
            "firstchild: args\n"
            "    secondchild: other args\n"
            "    @option: this won't work here\n"
        )
        with pytest.raises(exceptions.LoadError):
            tracker_obj.deserialize("str", lines)

    def test_load_continued_text(self):
        tracker = Tracker(skeleton=False)
        lines = (
            "_gennode: derp\n"
            "    - herp\n"
            "    - derp\n"
        )
        tracker.deserialize("str", lines)
        assert tracker.root.children.next_neighbor.text == "derp\nherp\nderp"

    def test_save_basic(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(),
                skeleton=False)

        node1 = GenericNode("node1", "node1_text", tracker.root)
        tracker.root.addchild(node1)
        node2 = GenericNode("node2", "node2_text", tracker.root)
        tracker.root.addchild(node2)
        node3 = GenericNode("node3", None, tracker.root)
        tracker.root.addchild(node3)

        node1_1 = GenericNode("node1_1", "node1_1_text", node1)
        node1_1.setoption("herp", "derp")
        node1.addchild(node1_1)

        node1_2 = GenericNode("node1_2", "node1_2_text", node1)
        node1_2.continue_text("herk derk")
        node1.addchild(node1_2)

        node2_1 = GenericNode("node2_1", "node2_1_text", node2)
        node2_1.setoption("hark", "dark")
        node2_1.continue_text('honk donk')
        node2.addchild(node2_1)

        class WriteTarget(object):
            def __init__(self):
                self.text = ""

            def write(self, text):
                self.text = text

        target = WriteTarget()
        tracker.serialize("file", target)
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

    def test_too_indented(self):
        tracker = Tracker(skeleton=False,
                nodecreator=FakeNodeCreator(GenericActivate))
        with pytest.raises(exceptions.LoadError):
            tracker.deserialize("str",
                "herp\n"
                "    derp\n"
                "            donk\n"
            )

    def test_unhandled_load_error(self):
        class ExcOnOptionNode(GenericNode):
            def setoption(self, option, value):
                raise Exception("test exception")

        tracker = Tracker(skeleton=False,
                nodecreator=FakeNodeCreator(ExcOnOptionNode))
        input_str = (
            "node1: node1\n"
            "node2: node2\n"
            "node3: node3\n"
            "    @someoption: boom\n"
        )
        try:
            tracker.deserialize("str", input_str)
        except exceptions.LoadError as e:
            result = str(e)
            assert "At line 4: UNHANDLED ERROR" in result
            assert "Exception: test exception" in result
        else:  # pragma: no cover
            assert False

    def test_roottype(self):
        class SubRootNode(TreeRootNode):

            target_variable = "present"

        tracker = Tracker(skeleton=False, roottype=SubRootNode)
        assert tracker.roottype is SubRootNode
        assert type(tracker.root) is SubRootNode

        tracker.deserialize("str", "")

        assert type(tracker.root) is SubRootNode
