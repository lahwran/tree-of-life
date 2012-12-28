
import pytest
from todo_tracker.nodes.node import TreeRootNode, Node
from todo_tracker import alarms
from todo_tracker.test.util import FakeNodeCreator


class DummyTracker(object):
    def __init__(self, roottype, nodetype):
        self.nodecreator = FakeNodeCreator(nodetype)
        self.root = roottype(self, self.nodecreator)
        self.alarms = []

    def _set_alarm(self, alarm):
        self.alarms.append(alarm)


class AlarmCollectorRoot(TreeRootNode):
    def __init__(self, tracker, nodecreator):
        TreeRootNode.__init__(self, tracker, nodecreator)
        self.alarms = []

    def _add_alarm(self, alarm):
        self.alarms.append(alarm)


class MixedNode(Node, alarms.NodeMixin):
    def __init__(self, *args, **kw):
        Node.__init__(self, *args, **kw)
        alarms.NodeMixin.__init__(self)


class DummyAlarm(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.root = None
        self.is_live = False

    def _node_ready(self, root):
        self.root = root

    def _go_live(self):
        self.is_live = True


class TestNodeMixin(object):
    def test_already_registered(self, monkeypatch):
        tracker = DummyTracker(AlarmCollectorRoot, MixedNode)
        node = MixedNode("node", None, tracker.root)
        tracker.root.addchild(node)
        assert set(node.alarms) == set()

        monkeypatch.setattr(alarms, "Alarm", DummyAlarm)

        argsentinel = object()
        alarm = node.alarm(argsentinel, 1, 2, 3, herp="derp")
        assert alarm.args == (node, argsentinel, 1, 2, 3)
        assert alarm.kwargs == {"herp": "derp"}
        assert alarm.root is node.root
        assert node.root is tracker.root
        assert tracker.root.alarms == [alarm]

    def test_not_registered(self, monkeypatch):
        tracker = DummyTracker(AlarmCollectorRoot, MixedNode)
        node = MixedNode("node", None, None)
        assert set(node.alarms) == set()

        monkeypatch.setattr(alarms, "Alarm", DummyAlarm)

        argsentinel = object()
        alarm = node.alarm(argsentinel, 1, 2, 3, herp="derp")
        assert alarm.args == (node, argsentinel, 1, 2, 3)
        assert alarm.kwargs == {"herp": "derp"}
        assert alarm.root is None
        assert tracker.root.alarms == []

        tracker.root.addchild(node)

        assert alarm.root is node.root
        assert node.root is tracker.root
        assert tracker.root.alarms == [alarm]

    @pytest.mark.weakref
    def test_thrown_away(self, monkeypatch):
        tracker = DummyTracker(AlarmCollectorRoot, MixedNode)
        node = MixedNode("node", None, None)
        assert set(node.alarms) == set()

        monkeypatch.setattr(alarms, "Alarm", DummyAlarm)
        node.alarm()

        tracker.root.addchild(node)

        assert tracker.root.alarms == []


class MixedRoot(alarms.RootMixin, TreeRootNode):
    def __init__(self, *a, **kw):
        alarms.RootMixin.__init__(self)
        TreeRootNode.__init__(self, *a, **kw)


class TestRootMixin(object):
    def test_already_loaded(self):
        tracker = DummyTracker(MixedRoot, MixedNode)
        root = tracker.root
        #assert not root._alarm_ready
        assert set(root.alarms) == set()
        #root.load_finished()
        assert root._alarm_ready

        alarm = DummyAlarm()
        assert not alarm.is_live

        root._add_alarm(alarm)

        assert alarm.is_live
