import itertools

import pytest
from zope.interface import implementer
from crow2.adapterutil import fakeimplementeds, IFile

from todo_tracker.nodes import GenericNode, GenericActivate
from todo_tracker.file_storage import serialize_to_str
from todo_tracker.test.util import FakeNodeCreator
from todo_tracker import exceptions

from todo_tracker.tracker import Tracker, _NodeListRoot, Tree, SimpleOption, _NodeMatcher

class TestTracker(object):
    def test_load_basic(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator(), auto_skeleton=False)
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

    def test_load_bad_order(self):
        tracker_obj = Tracker(nodecreator=FakeNodeCreator(), auto_skeleton=False)

        lines = (
            "firstchild: args\n"
            "    secondchild: other args\n"
            "    @option: this won't work here\n"
        )
        with pytest.raises(exceptions.LoadError):
            tracker_obj.load(lines)

    def test_load_continued_text(self):
        tracker_obj = Tracker(auto_skeleton=False)
        lines = (
            "_gennode: derp\n"
            "    - herp\n"
            "    - derp\n"
        )
        tracker_obj.load(lines)
        assert tracker_obj.root.children.next_neighbor.text == "derp\nherp\nderp"

    def test_save_basic(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(), auto_skeleton=False)

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

    def test_activate_next(self):
        tracker = Tracker(auto_skeleton=False)
        sequence = [
            (
                "_genactive: 0\n"
                "    @deactivate\n"
                "    _genactive: 0.1\n"
                "        @deactivate\n"
                "        _genactive: 0.1.2\n"
                "            @deactivate\n" # note: order matters
                "            @active\n"     #  must have deactivate before active
                "    _genactive: 0.2\n"
                "        @deactivate\n"
                "        _genactive: 0.2.1\n"
                "            @deactivate\n"
            ),
            (
                "_genactive: 0\n"
                "    _genactive: 0.1\n"
                "        @active\n"
                "        _genactive: 0.1.2\n"
                "            @locked\n"
                "    _genactive: 0.2\n"
                "        @deactivate\n"
                "        _genactive: 0.2.1\n"
                "            @deactivate\n"
            ),
            (
                "_genactive: 0\n"
                "    _genactive: 0.1\n"
                "        @locked\n"
                "        _genactive: 0.1.2\n"
                "            @locked\n"
                "    _genactive: 0.2\n"
                "        @active\n"
                "        _genactive: 0.2.1\n"
                "            @deactivate\n"
            ),
            (
                "_genactive: 0\n"
                "    _genactive: 0.1\n"
                "        @locked\n"
                "        _genactive: 0.1.2\n"
                "            @locked\n"
                "    _genactive: 0.2\n"
                "        _genactive: 0.2.1\n"
                "            @active\n"
            ),
            (
                "_genactive: 0\n"
                "    _genactive: 0.1\n"
                "        @locked\n"
                "        _genactive: 0.1.2\n"
                "            @locked\n"
                "    _genactive: 0.2\n"
                "        @active\n"
                "        _genactive: 0.2.1\n"
                "            @locked\n"
            ),
            (
                "_genactive: 0\n"
                "    @active\n"
                "    _genactive: 0.1\n"
                "        @locked\n"
                "        _genactive: 0.1.2\n"
                "            @locked\n"
                "    _genactive: 0.2\n"
                "        @locked\n"
                "        _genactive: 0.2.1\n"
                "            @locked\n"
            ),
        ]

        tracker.load(sequence[0])

        for num, output_str in enumerate(sequence[1:]):
            tracker.activate_next()
            asdf = serialize_to_str(tracker.root)
            assert asdf == output_str

    def test_random_insertion(self, monkeypatch):
        tracker = Tracker(auto_skeleton=False)

        input_str = (
            "_genactive: 0\n"
            "_genactive: 2\n"
            "    @active\n"
            "_genactive: 4\n"
        )

        tracker.load(input_str)

        tracker.create_before("_genactive", "1")
        tracker.create_after("_genactive", "1.5")

        tracker.activate_next()

        tracker.create_after("_genactive", "3")

        for move in (tracker.activate_next, tracker.activate_prev, tracker.activate_next):
            for i in range(30):
                active = tracker.active_node
                move()
                if active is tracker.active_node:
                    break
            else:
                assert False # pragma: no cover

        expected_str = (
            "_genactive: 0\n"
            "_genactive: 1\n"
            "_genactive: 1.5\n"
            "_genactive: 2\n"
            "_genactive: 3\n"
            "_genactive: 4\n"
            "    @active\n"
        )

        serialized = serialize_to_str(tracker.root)
        print serialized
        assert serialized == expected_str

    def test_auto_skeleton(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(GenericActivate))
        serialized = serialize_to_str(tracker.root)
        assert serialized == (
            "days\n"
            "    day: today\n"
            "        @active\n"
            "todo bucket\n"
        )

    def test_auto_skeleton_load(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(GenericActivate))
        tracker.load(
            "days\n"
            "    day: yesterday\n"
            "        @active\n"
        )

        serialized = serialize_to_str(tracker.root)
        assert serialized == (
            "days\n"
            "    day: yesterday\n"
            "    day: today\n"
            "        @active\n"
            "todo bucket\n"
        )

    def test_auto_skeleton_load_integration(self):
        tracker = Tracker()
        tracker.load(
            "days\n"
            "    day: today\n"
            "todo bucket"
        )
        today = tracker.active_node.text
        tracker.active_node.started = None
        assert serialize_to_str(tracker.root) == (
            "days\n"
            "    day: %s\n"
            "        @active\n"
            "todo bucket\n"
        ) % today

    def test_auto_skeleton_day_active(self):
        tracker = Tracker()
        tracker.load(
            "days\n"
            "    day: today\n"
            "        @started: September 23, 2012 11:00 AM\n"
            "        _genactive: something\n"
            "            @active\n"
            "todo bucket"
        )
        today = tracker.root.find_node(["days", "day: today"])
        tracker.active_node.started = None
        assert serialize_to_str(tracker.root) == (
            "days\n"
            "    day: %s\n"
            "        @started: September 23, 2012 11:00 AM\n"
            "        _genactive: something\n"
            "            @active\n"
            "todo bucket\n"
        ) % today.text

    def test_too_indented(self):
        tracker = Tracker(auto_skeleton=False, nodecreator=FakeNodeCreator(GenericActivate))
        with pytest.raises(exceptions.LoadError):
            tracker.load(
                "herp\n"
                "    derp\n"
                "            donk\n"
            )

    def test_next_empty(self):
        tracker = Tracker(auto_skeleton=False)
        node = GenericActivate("herp", None, tracker.root, tracker)
        tracker.root.addchild(node)
        tracker.activate(node)

        tracker.activate_next()
        assert tracker.active_node is node

    def test_create_nonactivate(self):
        tracker = Tracker(auto_skeleton=False)
        node = GenericActivate("herp", None, tracker.root, tracker)
        tracker.root.addchild(node)
        tracker.activate(node)
        tracker.create_after("_gennode", "honk", activate=False)
        assert tracker.active_node is node
        assert node.next_neighbor.text == "honk"

    def test_create_child(self):
        tracker = Tracker(auto_skeleton=False, nodecreator=FakeNodeCreator(GenericActivate))
        node = GenericActivate("herp", "derp", tracker.root, tracker)
        tracker.root.addchild(node)
        tracker.activate(node)
        tracker.create_child("node1", "1", activate=False)
        assert tracker.active_node is node
        tracker.create_child("node2", "2")
        node1, node2 = tuple(node.children)
        assert tracker.active_node is node2
        assert node1.node_type == "node1"
        assert node2.node_type == "node2"

    def test_activate_cant_activate(self):
        tracker = Tracker(auto_skeleton=False, nodecreator=FakeNodeCreator(GenericNode))
        node = tracker.root.createchild("herp", "derp")

        with pytest.raises(exceptions.CantStartNodeError):
            tracker.activate(node)

    def test_unhandled_load_error(self):
        class ExcOnOptionNode(GenericNode):
            def setoption(self, option, value):
                raise Exception("test exception")

        tracker = Tracker(auto_skeleton=False, nodecreator=FakeNodeCreator(ExcOnOptionNode))
        input_str = (
            "node1: node1\n"
            "node2: node2\n"
            "node3: node3\n"
            "    @someoption: boom\n"
        )
        try:
            tracker.load(input_str)
        except exceptions.LoadError as e:
            assert str(e) == "At line 4: UNHANDLED ERROR: Exception: test exception"
        else: # pragma: no cover
            assert False


class TestNode(object):
    def test_iter_parents(self):
        tracker = Tracker(auto_skeleton=False)

        input_str = (
            "_genactive: 0\n"
            "    _genactive: 1\n"
            "        _genactive: 2\n"
            "            _genactive: 3\n"
            "                @active"
        )

        tracker.load(input_str)

        expected_pairs = [
            ("_genactive", "3"),
            ("_genactive", "2"),
            ("_genactive", "1"),
            ("_genactive", "0"),
            ("life", None)
        ]

        for expected, node in itertools.izip_longest(expected_pairs, tracker.active_node.iter_parents()):
            node_type, text = expected
            assert node_type == node.node_type
            assert text == node.text

    def tracker(self):
        return Tracker(nodecreator=FakeNodeCreator(Tree), auto_skeleton=False)

    def test_multiline_init(self):
        tracker = self.tracker()

        class SubNode(Tree):
            multiline = False

        with pytest.raises(exceptions.LoadError):
            SubNode("subnode", "text\nothertext", tracker.root, tracker)

    def test_multiline_continue(self):
        tracker = self.tracker()

        class SubNode(Tree):
            multiline = False

        subnode = SubNode("subnode", "text", tracker.root, tracker)
        with pytest.raises(exceptions.LoadError):
            subnode.continue_text("line 2")

    def test_toplevel(self):
        tracker = self.tracker()

        class SubNode(Tree):
            toplevel = True

        middle = SubNode("middle", None, tracker.root, tracker)

        node = SubNode("error", None, middle, tracker)
        with pytest.raises(exceptions.LoadError):
            node._validate()

    def test_textless(self):
        tracker = self.tracker()

        class SubNode(Tree):
            textless = True

        success = SubNode("subnode", None, tracker.root, tracker)
        assert success

        with pytest.raises(exceptions.LoadError):
            SubNode("subnode", "unallowed text", tracker.root, tracker)

    def test_notext_continueline(self):
        tracker = self.tracker()

        class SubNode(Tree):
            multiline = True

        node = SubNode("node", None, tracker.root, tracker)

        with pytest.raises(exceptions.LoadError):
            node.continue_text("error")

    def test_allowed_children(self):
        tracker = self.tracker()

        class ParentNode(Tree):
            allowed_children = ("allowed",)

        parent = ParentNode("parent", None, tracker.root, tracker)

        child1 = Tree("allowed", None, parent, tracker)
        parent.addchild(child1)

        child2 = Tree("not-allowed", None, parent, tracker)
        with pytest.raises(exceptions.LoadError):
            parent.addchild(child2)

    def test_allowed_parents(self):
        tracker = self.tracker()

        class ChildNode(Tree):
            children_of = ("allowed-parent",)

        allowed_parent = Tree("allowed-parent", None, tracker.root, tracker)
        child1 = ChildNode("child1", None, allowed_parent, tracker)
        child1._validate()
        allowed_parent.addchild(child1)

        disallowed_parent = Tree("some-other-node", None, tracker.root, tracker)
        child2 = ChildNode("child2", None, disallowed_parent, tracker)
        with pytest.raises(exceptions.LoadError):
            child2._validate()

    def test_remove_child(self):
        tracker = self.tracker()

        parent1 = Tree("parent1", None, tracker.root, tracker)
        parent2 = Tree("parent2", None, tracker.root, tracker)

        child = Tree("child", None, parent1, tracker)
        parent1.addchild(child)
        assert list(parent1.children) == [child]
        assert child.parent is parent1

        child.detach()
        assert child.parent is None
        assert list(parent1.children) == []

        child.parent = parent2
        parent2.addchild(child)
        assert list(parent2.children) == [child]
        assert child.parent is parent2

    def test_detach_noop(self):
        node = Tree("node", None, None, None)
        node.detach()

    def test_copy_new_tracker(self):
        tracker1 = self.tracker()
        tracker2 = self.tracker()


        node1 = Tree("node", "text", tracker1.root, tracker1)
        tracker1.root.addchild(node1)
        node1_child = Tree("nodechild", None, node1, tracker1)
        node1.addchild(node1_child)

        node2 = node1.copy(tracker2.root, tracker2)
        tracker2.root.addchild(node2)

        assert node2.tracker is tracker2
        assert node2.parent is tracker2.root
        node2_child = node2.children.next_neighbor
        assert node2_child.tracker is tracker2
        assert node2_child.parent is node2

        assert node1.node_type == node2.node_type
        assert node1.text == node2.text
        assert node1_child.node_type == node2_child.node_type
        assert node1_child.text == node2_child.text

    def test_copy_sibling(self):
        tracker = self.tracker()

        node = Tree("node", "text", tracker.root, tracker)
        tracker.root.addchild(node)
        newnode = node.copy()
        tracker.root.addchild(newnode)

        assert list(tracker.root.children) == [node, newnode]
        assert newnode.node_type == node.node_type
        assert newnode.text == node.text
        assert newnode.parent is node.parent
        assert newnode.tracker is node.tracker

    def test_copy_newplace(self):
        tracker = self.tracker()

        parent1 = Tree("parent1", None, tracker.root, tracker)
        parent2 = Tree("parent2", None, tracker.root, tracker)

        node = Tree("node", None, parent1, tracker)

        newnode = node.copy(parent2)
        parent2.addchild(newnode)

        assert newnode.node_type == node.node_type
        assert newnode.text == node.text
        assert newnode.parent is parent2
        assert newnode.tracker is tracker

    def test_copy_tracker_sameparent(self):
        tracker1 = self.tracker()
        tracker2 = self.tracker()

        node = Tree("node", None, tracker1.root, tracker1)

        with pytest.raises(exceptions.LoadError):
            node.copy(tracker=tracker2)

    def test_setoption(self):
        tracker = self.tracker()

        class OptionedNode(Tree):
            options = (
                ("option1", SimpleOption(str)),
                ("option2", SimpleOption(str)),
                ("option3", SimpleOption(int))
            )
            def __init__(self, *a, **k):
                super(OptionedNode, self).__init__(*a, **k)
                self.option1 = None
                self.option2 = None
                self.option3 = None

        node = OptionedNode("node", None, tracker.root, tracker)

        with pytest.raises(exceptions.LoadError):
            node.setoption("nonexistant", "error")

        node.setoption("option1", "text")
        node.setoption("option2", "othertext")
        node.setoption("option3", "2")

        assert node.option1 == "text"
        assert node.option2 == "othertext"
        assert node.option3 == 2

        with pytest.raises(ValueError):
            node.setoption("option3", "ten")

    def test_option_values(self):
        class FakeOption(object):
            def __init__(self, provideout):
                self.incoming = None
                self.outgoing = None
                self.provideout = provideout

            def set(self, parent, option, value):
                self.incoming = (parent, option, value)

            def get(self, parent, option):
                self.outgoing = (parent, option)
                return self.provideout

        option1_sentinel = object()
        option1 = FakeOption((True, option1_sentinel))
        option2_sentinel = object()
        option2 = FakeOption((False, option2_sentinel))

        class OptionNode(Tree):
            options = (
                ("option1", option1),
                ("option2", option2)
            )

        tracker = self.tracker()
        node = OptionNode("node", None, tracker.root, tracker)

        node.setoption("option1", "option1_value")
        node.setoption("option2", "option2_value")
        
        assert node.option_values() == [
            ("option1", option1_sentinel, True),
            ("option2", option2_sentinel, False)
        ]

        assert option1.incoming == (node, "option1", "option1_value")
        assert option2.incoming == (node, "option2", "option2_value")
        assert option1.outgoing == (node, "option1")
        assert option2.outgoing == (node, "option2")

    def test_add_unexpected_child(self):
        tracker = self.tracker()
        parent = Tree("parent", None, tracker.root, tracker)
        parent2 = Tree("parent2", None, tracker.root, tracker)
        child = Tree("child", None, parent, tracker)

        with pytest.raises(exceptions.LoadError):
            parent2.addchild(child)

    def test_str(self):
        tracker = self.tracker()
        node = Tree("asdf", "fdsa", tracker.root, tracker)
        s = str(node)
        assert "asdf" in s
        assert "fdsa" in s

    def test_repr(self):
        tracker = self.tracker()
        node = Tree("asdf", "fdsa", tracker.root, tracker)
        s = repr(node)
        assert "asdf" in s
        assert "fdsa" in s
        assert tracker.root.node_type in s
        assert "Tree" in s

    def test_start_stop(self):
        class SimpleActivateNode(Tree):
            can_activate = True

        tracker = Tracker(nodecreator=FakeNodeCreator(SimpleActivateNode), auto_skeleton=False)
        tracker.activate(tracker.root.createchild("node1"))
        tracker.create_after("node2")
        node3 = tracker.create_after("node3", activate=False)
        tracker.activate_next()

        assert node3.active

    def test_cant_activate(self):
        node = Tree("herp", None, None, None)
        with pytest.raises(exceptions.LoadError):
            node.start()


class TestFindNode(object):
    def test_flatten(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(Tree), auto_skeleton=False)
        node1 = tracker.root.createchild("node1", "value1")
        node1.createchild("node3", "value3")
        node4 = node1.createchild("node4", "value4")
        target = node4.createchild("target", "value")
        tracker.root.createchild("node2", "value2")

        result = tracker.root.find_node(["**", "target"])
        assert result is target

    def test_empty_flatten(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(Tree), auto_skeleton=False)

        assert tracker.root.find_node(["**"]) == None

    def test_find_parents(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(Tree), auto_skeleton=False)
        target = tracker.root.createchild("target", "value1")
        target.createchild("node3", "value3")
        node4 = target.createchild("node4", "value4")
        node1 = node4.createchild("node1", "value")
        tracker.root.createchild("node2", "value2")

        result = node1.find_node(["<target"])
        assert result is target

    def test_empty_find_parents(self):
        tracker = Tracker(nodecreator=FakeNodeCreator(Tree), auto_skeleton=False)
        node3 = tracker.root.createchild("node3", "value3")
        node2 = node3.createchild("node2", "value2")
        node1 = node2.createchild("node1", "value1")

        result = node1.find_node(["<nonexistant"])
        assert result is None

    def test_find_text(self):
        tracker = Tracker(auto_skeleton=False) # FakeNodeCreator would interfere with this test
        value1 = tracker.root.createchild("comment", "value one")
        target = value1.createchild("comment", "value two")

        result = tracker.root.find_node(["value one", "value two"])

        assert result is target

    def test_orphaned_find(self):
        class AlwaysOrphanedNode(Tree):
            toplevel = True
            children_of = ("life",)
        tracker = Tracker(nodecreator=FakeNodeCreator(AlwaysOrphanedNode), auto_skeleton=False)
        result = tracker.root.find_node(["this: had", "better: not", "make: things", "blow: up"])
        assert result is None

def test_get_missing_option():
    obj = object()
    option = SimpleOption(str)
    assert option.get(obj, "somename") == (False, None)

class TestNodeList(object):
    def test_insert_errors(self):
        nodelist = _NodeListRoot()

        node1 = GenericNode('node1')
        node2 = GenericNode('node2')
        loosenode = GenericNode('loosenode')

        nodelist.insert(node1)
        oldnext = node1._next_node
        node1._next_node = loosenode

        with pytest.raises(exceptions.ListIntegrityError):
            nodelist.insert(node2)

        node1._next_node = oldnext
        node1._prev_node = loosenode

        with pytest.raises(exceptions.ListIntegrityError):
            nodelist.insert(node2, after=nodelist)

    def test_misspecified_neighbors(self):
        nodelist = _NodeListRoot()

        node1 = GenericNode('node1')
        node2 = GenericNode('node2')
        node3 = GenericNode('node3')
        toinsert = GenericNode('toinsert')

        nodelist.insert(node1)
        nodelist.insert(node2)
        nodelist.insert(node3)

        with pytest.raises(exceptions.ListIntegrityError):
            nodelist.insert(toinsert, after=node1, before=node3)

    def test_insert_remove(self):
        nodelist1 = _NodeListRoot()
        nodelist2 = _NodeListRoot()

        node_before = GenericNode('node_before')
        node1 = GenericNode('node1')
        node_after = GenericNode('node_after')

        nodelist1.insert(node_before)
        nodelist1.insert(node1)
        nodelist1.insert(node_after)

        assert nodelist1._next_node is node_before
        assert node_before._prev_node is nodelist1
        assert node_before._next_node is node1
        assert node1._prev_node is node_before
        assert node1._next_node is node_after
        assert node_after._prev_node is node1
        assert node_after._next_node is nodelist1
        assert nodelist1._prev_node is node_after

        nodelist1.remove(node1)

        assert nodelist1._next_node is node_before
        assert node_before._prev_node is nodelist1
        assert node_before._next_node is node_after
        assert node_after._prev_node is node_before
        assert node_after._next_node is nodelist1
        assert nodelist1._prev_node is node_after

        nodelist2.insert(node1)

        assert nodelist2._next_node is node1
        assert node1._prev_node is nodelist2
        assert node1._next_node is nodelist2
        assert nodelist2._prev_node is node1

    def test_neighbors(self):
        nodelist = _NodeListRoot()
        node1 = GenericNode('node1')
        node2 = GenericNode('node2')
        nodelist.insert(node1)
        nodelist.insert(node2)

        assert nodelist.prev_neighbor is node2
        assert nodelist._prev_node is node2
        assert nodelist.next_neighbor is node1
        assert nodelist._next_node is node1

    def test_empty_neighbors(self):
        nodelist = _NodeListRoot()

        assert nodelist.prev_neighbor is None
        assert nodelist.next_neighbor is None
        assert nodelist._next_node is nodelist
        assert nodelist._prev_node is nodelist

    def test_iteration(self):
        nodelist = _NodeListRoot()

        node1 = GenericNode('node1')
        node2 = GenericNode('node2')
        node3 = GenericNode('node3')
        nodelist.insert(node1)
        nodelist.insert(node2)
        nodelist.insert(node3)

        forward = [node1, node2, node3]
        reverse = [node3, node2, node1]

        for foundnode, expectednode in itertools.izip_longest(nodelist, forward):
            assert foundnode is expectednode

        for foundnode, expectednode in itertools.izip_longest(reversed(nodelist), reverse):
            assert foundnode is expectednode
