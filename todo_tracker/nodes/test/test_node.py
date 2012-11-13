from itertools import izip_longest

import pytest

from todo_tracker.test.util import FakeNodeCreator
from todo_tracker.tracker import Tracker_Greppable_Fun
from todo_tracker.nodes.node import Node, _NodeListRoot, Option, _NodeMatcher
from todo_tracker.nodes.misc import GenericNode, GenericActivate
from todo_tracker import exceptions


class TestNode(object):
    def test_iter_parents(self):
        tracker = Tracker_Greppable_Fun(skeleton=False)

        input_str = (
            "_genactive: 0\n"
            "    _genactive: 1\n"
            "        _genactive: 2\n"
            "            _genactive: 3\n"
            "                @active"
        )

        tracker.deserialize("str", input_str)

        expected_pairs = [
            ("_genactive", "3"),
            ("_genactive", "2"),
            ("_genactive", "1"),
            ("_genactive", "0"),
            ("life", None)
        ]

        for expected, node in izip_longest(expected_pairs,
                tracker.root.active_node.iter_parents()):
            node_type, text = expected
            assert node_type == node.node_type
            assert text == node.text

    def tracker(self):
        return Tracker_Greppable_Fun(nodecreator=FakeNodeCreator(Node),
                skeleton=False)

    def test_multiline_init(self):
        tracker = self.tracker()

        class SubNode(Node):
            multiline = False

        with pytest.raises(exceptions.LoadError):
            SubNode("subnode", "text\nothertext", tracker.root)

    def test_multiline_continue(self):
        tracker = self.tracker()

        class SubNode(Node):
            multiline = False

        subnode = SubNode("subnode", "text", tracker.root)
        with pytest.raises(exceptions.LoadError):
            subnode.continue_text("line 2")

    def test_toplevel(self):
        tracker = self.tracker()

        class SubNode(Node):
            toplevel = True

        middle = SubNode("middle", None, tracker.root)

        node = SubNode("error", None, middle)
        with pytest.raises(exceptions.LoadError):
            node._validate()

    def test_textless(self):
        tracker = self.tracker()

        class SubNode(Node):
            textless = True

        success = SubNode("subnode", None, tracker.root)
        assert success

        with pytest.raises(exceptions.LoadError):
            SubNode("subnode", "unallowed text", tracker.root)

    def test_notext_continueline(self):
        tracker = self.tracker()

        class SubNode(Node):
            multiline = True

        node = SubNode("node", None, tracker.root)

        with pytest.raises(exceptions.LoadError):
            node.continue_text("error")

    def test_allowed_children(self):
        tracker = self.tracker()

        class ParentNode(Node):
            allowed_children = ("allowed",)

        parent = ParentNode("parent", None, tracker.root)

        child1 = Node("allowed", None, parent)
        parent.addchild(child1)

        child2 = Node("not-allowed", None, parent)
        with pytest.raises(exceptions.LoadError):
            parent.addchild(child2)

    def test_allowed_parents(self):
        tracker = self.tracker()

        class ChildNode(Node):
            children_of = ("allowed-parent",)

        allowed_parent = Node("allowed-parent", None, tracker.root)
        child1 = ChildNode("child1", None, allowed_parent)
        child1._validate()
        allowed_parent.addchild(child1)

        disallowed_parent = Node("some-other-node", None, tracker.root)
        child2 = ChildNode("child2", None, disallowed_parent)
        with pytest.raises(exceptions.LoadError):
            child2._validate()

    def test_remove_child(self):
        tracker = self.tracker()

        parent1 = Node("parent1", None, tracker.root)
        parent2 = Node("parent2", None, tracker.root)

        child = Node("child", None, parent1)
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
        node = Node("node", None, None)
        node.detach()

    def test_copy_new_tracker(self):
        tracker1 = self.tracker()
        tracker2 = self.tracker()

        node1 = Node("node", "text", tracker1.root)
        tracker1.root.addchild(node1)
        node1_child = Node("nodechild", None, node1)
        node1.addchild(node1_child)

        node2 = node1.copy(tracker2.root)
        tracker2.root.addchild(node2)

        assert node2.root is tracker2.root
        assert node2.parent is tracker2.root
        node2_child = node2.children.next_neighbor
        assert node2_child.root is tracker2.root
        assert node2_child.parent is node2

        assert node1.node_type == node2.node_type
        assert node1.text == node2.text
        assert node1_child.node_type == node2_child.node_type
        assert node1_child.text == node2_child.text

    def test_copy_sibling(self):
        tracker = self.tracker()

        node = Node("node", "text", tracker.root)
        tracker.root.addchild(node)
        newnode = node.copy()
        tracker.root.addchild(newnode)

        assert list(tracker.root.children) == [node, newnode]
        assert newnode.node_type == node.node_type
        assert newnode.text == node.text
        assert newnode.parent is node.parent
        assert newnode.root is node.root

    def test_copy_newplace(self):
        tracker = self.tracker()

        parent1 = Node("parent1", None, tracker.root)
        parent2 = Node("parent2", None, tracker.root)

        node = Node("node", None, parent1)

        newnode = node.copy(parent2)
        parent2.addchild(newnode)

        assert newnode.node_type == node.node_type
        assert newnode.text == node.text
        assert newnode.parent is parent2
        assert newnode.root is tracker.root

    def test_setoption(self):
        tracker = self.tracker()

        class OptionedNode(Node):
            options = (
                ("option1", Option()),
                ("option2", Option()),
                ("option3", Option(int, str))
            )

            def __init__(self, *a, **k):
                super(OptionedNode, self).__init__(*a, **k)
                self.option1 = None
                self.option2 = None
                self.option3 = None

        node = OptionedNode("node", None, tracker.root)

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

        class OptionNode(Node):
            options = (
                ("option1", option1),
                ("option2", option2)
            )

        tracker = self.tracker()
        node = OptionNode("node", None, tracker.root)

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
        parent = Node("parent", None, tracker.root)
        parent2 = Node("parent2", None, tracker.root)
        child = Node("child", None, parent)

        with pytest.raises(exceptions.LoadError):
            parent2.addchild(child)

    def test_str(self):
        tracker = self.tracker()
        node = Node("asdf", "fdsa", tracker.root)
        s = str(node)
        assert "asdf" in s
        assert "fdsa" in s

    def test_repr(self):
        tracker = self.tracker()
        node = Node("asdf", "fdsa", tracker.root)
        s = repr(node)
        assert "asdf" in s
        assert "fdsa" in s
        assert tracker.root.node_type in s
        assert "Node" in s

    def test_start_stop(self):
        class SimpleActivateNode(Node):
            can_activate = True

        tracker = Tracker_Greppable_Fun(skeleton=False,
                nodecreator=FakeNodeCreator(SimpleActivateNode))
        tracker.root.activate(tracker.root.createchild("node1"))
        tracker.root.create_after("node2")
        node3 = tracker.root.create_after("node3", activate=False)
        tracker.root.activate_next()

        assert node3.active

    def test_cant_activate(self):
        node = Node("herp", None, None)
        with pytest.raises(exceptions.LoadError):
            node.start()


class TestFindNode(object):
    def test_flatten(self):
        tracker = Tracker_Greppable_Fun(nodecreator=FakeNodeCreator(Node),
                skeleton=False)
        node1 = tracker.root.createchild("node1", "value1")
        node1.createchild("node3", "value3")
        node4 = node1.createchild("node4", "value4")
        target = node4.createchild("target", "value")
        tracker.root.createchild("node2", "value2")

        result = tracker.root.find_node(["**", "target"])
        assert result is target

    def test_empty_flatten(self):
        tracker = Tracker_Greppable_Fun(nodecreator=FakeNodeCreator(Node),
                skeleton=False)

        assert tracker.root.find_node(["**"]) is None

    def test_find_parents(self):
        tracker = Tracker_Greppable_Fun(nodecreator=FakeNodeCreator(Node),
                skeleton=False)
        target = tracker.root.createchild("target", "value1")
        target.createchild("node3", "value3")
        node4 = target.createchild("node4", "value4")
        node1 = node4.createchild("node1", "value")
        tracker.root.createchild("node2", "value2")

        result = node1.find_node(["<target"])
        assert result is target

    def test_empty_find_parents(self):
        tracker = Tracker_Greppable_Fun(nodecreator=FakeNodeCreator(Node),
                skeleton=False)
        node3 = tracker.root.createchild("node3", "value3")
        node2 = node3.createchild("node2", "value2")
        node1 = node2.createchild("node1", "value1")

        result = node1.find_node(["<nonexistant"])
        assert result is None

    def test_find_text(self):
        # FakeNodeCreator would interfere with this test as it always
        # returns 'existant'
        tracker = Tracker_Greppable_Fun(skeleton=False)
        value1 = tracker.root.createchild("comment", "value one")
        target = value1.createchild("comment", "value two")

        result = tracker.root.find_node(["value one", "value two"])

        assert result is target

    def test_orphaned_find(self):
        class AlwaysOrphanedNode(Node):
            toplevel = True
            children_of = ("life",)
        tracker = Tracker_Greppable_Fun(skeleton=False,
                nodecreator=FakeNodeCreator(AlwaysOrphanedNode))
        result = tracker.root.find_node([
            "this: had", "better: not", "make: things", "blow: up"])
        assert result is None


def test_get_missing_option():
    obj = object()
    option = Option()
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

        for found, expected in izip_longest(nodelist, forward):
            assert found is expected

        for found, expected in izip_longest(reversed(nodelist), reverse):
            assert found is expected


class TestRootNode(object):
    def test_activate_next(self):
        tracker = Tracker_Greppable_Fun(skeleton=False)
        sequence = [
            (
                "_genactive: 0\n"
                "    @deactivate\n"
                "    _genactive: 0.1\n"
                "        @deactivate\n"
                "        _genactive: 0.1.2\n"
                "            @deactivate\n"  # note: order matters; must have
                "            @active\n"      # deactivate before active
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

        tracker.deserialize("str", sequence[0])

        for num, output_str in enumerate(sequence[1:]):
            tracker.root.activate_next()
            asdf = tracker.serialize("str")
            assert asdf == output_str

    def test_random_insertion(self, monkeypatch):
        tracker = Tracker_Greppable_Fun(skeleton=False)

        input_str = (
            "_genactive: 0\n"
            "_genactive: 2\n"
            "    @active\n"
            "_genactive: 4\n"
        )

        tracker.deserialize("str", input_str)
        root = tracker.root

        root.create_before("_genactive", "1")
        root.create_after("_genactive", "1.5")

        root.activate_next()

        root.create_after("_genactive", "3")

        directions = (
            root.activate_next,
            root.activate_prev,
            root.activate_next
        )
        for move in directions:
            for i in range(30):
                active = root.active_node
                move()
                if active is root.active_node:
                    break
            else:  # pragma: no cover
                assert False, "failed to reach end in 30 tries"

        expected_str = (
            "_genactive: 0\n"
            "_genactive: 1\n"
            "_genactive: 1.5\n"
            "_genactive: 2\n"
            "_genactive: 3\n"
            "_genactive: 4\n"
            "    @active\n"
        )

        serialized = tracker.serialize("str")
        assert serialized == expected_str

    def test_create_nonactivate(self):
        tracker = Tracker_Greppable_Fun(skeleton=False)
        node = GenericActivate("herp", None, tracker.root)
        tracker.root.addchild(node)
        tracker.root.activate(node)
        tracker.root.create_after("_gennode", "honk", activate=False)
        assert tracker.root.active_node is node
        assert node.next_neighbor.text == "honk"

    def test_create_child(self):
        tracker = Tracker_Greppable_Fun(skeleton=False,
                nodecreator=FakeNodeCreator(GenericActivate))
        root = tracker.root
        node = GenericActivate("herp", "derp", tracker.root)
        root.addchild(node)
        root.activate(node)
        tracker.root.create_child("node1", "1", activate=False)
        assert root.active_node is node
        root.create_child("node2", "2")
        node1, node2 = tuple(node.children)
        assert root.active_node is node2
        assert node1.node_type == "node1"
        assert node2.node_type == "node2"

    def test_next_empty(self):
        tracker = Tracker_Greppable_Fun(skeleton=False)
        node = GenericActivate("herp", None, tracker.root)
        tracker.root.addchild(node)
        tracker.root.activate(node)

        tracker.root.activate_next()
        assert tracker.root.active_node is node