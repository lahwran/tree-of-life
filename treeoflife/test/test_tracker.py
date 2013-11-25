from __future__ import unicode_literals, print_function

import itertools

import pytest

from treeoflife.nodes.misc import GenericNode, GenericActivate
from treeoflife.nodes.node import TreeRootNode
from treeoflife.file_storage import serialize_to_str
from treeoflife.test.util import FakeNodeCreator, match
from treeoflife import exceptions

from treeoflife.tracker import Tracker


class TestTracker(object):
    def test_load_basic(self, tmpdir):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator(),
                skeleton=False)
        f = tmpdir.join('file')
        with f.open("wb") as w:
            w.write((
                "firstchild: \u2028args\n"
                "    secondchild: \u2028other args\n"
                "        @option: \u2028data\n"
                "        thirdchild: \u2028herp derp\n"
                "    fourthchild: \u2028ark dark\n"
            ).encode("utf-8"))
        tracker_obj.deserialize("file", f.open("rb"))

        root = tracker_obj.root
        root_child0 = root.children.next_neighbor
        assert root_child0.id in root.ids
        assert len(root_child0.id) == 5
        assert root_child0.text == "\u2028args"
        assert root_child0.node_type == "firstchild"

        root_child0_child0 = root_child0.children.next_neighbor
        assert root_child0_child0.id in root.ids
        assert len(root_child0_child0.id) == 5
        assert root_child0_child0.text == "\u2028other args"
        assert root_child0_child0.node_type == "secondchild"
        assert root_child0_child0.metadata["option"] == "\u2028data"

        root_child0_child0_child0 = root_child0_child0.children.next_neighbor
        assert root_child0_child0_child0.text == "\u2028herp derp"
        assert root_child0_child0_child0.node_type == "thirdchild"

        root_child0_child1 = root_child0_child0.next_neighbor
        assert root_child0_child1.text == "\u2028ark dark"
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

    def test_save_basic(self, tmpdir):
        tracker = Tracker(nodecreator=FakeNodeCreator(),
                skeleton=False)

        node1 = GenericNode("node1", "\u2665node1_text", tracker.root)
        tracker.root.addchild(node1)
        node2 = GenericNode("node2", "\u2665node2_text", tracker.root)
        tracker.root.addchild(node2)
        node3 = GenericNode("node3", None, tracker.root)
        tracker.root.addchild(node3)

        node1_1 = GenericNode("node1_1", "\u2665node1_1_text", node1)
        node1_1.setoption("herp", "\u2665derp")
        node1.addchild(node1_1)

        node1_2 = GenericNode("node1_2", "\u2665node1_2_text", node1)
        node1_2.continue_text("\u2665herk derk")
        node1.addchild(node1_2)

        node2_1 = GenericNode("node2_1", "\u2665node2_1_text", node2)
        node2_1.setoption("hark", "\u2665dark")
        node2_1.continue_text('\u2665honk donk')
        node2.addchild(node2_1)

        f = tmpdir.join("file")
        target = f.open("wb")
        with target:
            tracker.serialize("file", target)
        assert match(f.read("rb"), (
            "node1#?????: \u2665node1_text\n"
            "    node1_1#?????: \u2665node1_1_text\n"
            "        @herp: \u2665derp\n"
            "    node1_2#?????: \u2665node1_2_text\n"
            "        - \u2665herk derk\n"
            "node2#?????: \u2665node2_text\n"
            "    node2_1#?????: \u2665node2_1_text\n"
            "        - \u2665honk donk\n"
            "        @hark: \u2665dark\n"
            "node3#?????\n"
        ).encode("utf-8"))

    def test_empty_line(self):
        tracker = Tracker(skeleton=False)
        tracker.deserialize("str",
                "\n"
                "task#12345: whatever\n"
                "   \n"
                "    task#abcde: whatever again\n"
                "\n"
                "    task#hijkl: some other thing\n"
                "\n"
                "\n"
        )
        assert tracker.serialize("str") == (
                "\n"
                "task#12345: whatever\n"
                "    \n"
                "    task#abcde: whatever again\n"
                "        \n"
                "    task#hijkl: some other thing\n"
                "        \n"
                "        \n"
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
