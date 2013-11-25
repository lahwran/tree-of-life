from __future__ import unicode_literals, print_function

from datetime import timedelta, datetime
import weakref

import pytest
from twisted.internet.task import Clock
from twisted.internet.defer import Deferred

from treeoflife.nodes.node import TreeRootNode, Node
from treeoflife import alarms
from treeoflife.test.util import FakeNodeCreator
from treeoflife.tracker import Tracker
from treeoflife.util import _monitor


@pytest.fixture
def reactortime(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(alarms, "reactor", clock)
    return clock

#-------------------------------------------------------#
#                   utility classes                     #
#-------------------------------------------------------#


class _PresetTracker(Tracker):
    def __init__(self, roottype, nodetype):
        self.nodecreator = FakeNodeCreator(nodetype)
        self.roottype = roottype
        self.root = roottype(self, self.nodecreator)
        self.make_skeleton = False
        self.alarms = []


class DummyTracker(_PresetTracker):
    def _set_alarm(self, alarm):
        self.alarms.append(alarm)


class DummyTimer(object):
    def __init__(self):
        self.is_active = True

    def cancel(self):
        self.is_active = False

    def active(self):
        return self.is_active


class DummyAlarmTracker(Tracker):
    def _set_alarm(self, callback=None, delta=None, date=None):
        deferred = Deferred()
        timer = DummyTimer()
        alarm = {
            "deferred": deferred,
            "timer": timer,
            "data": {
                "callback": callback,
                "delta": delta,
                "date": date
            }
        }
        self.alarms.append(alarm)
        return timer, deferred


class SuperDummyTracker(_PresetTracker):
    @property
    def _set_alarm(self):
        raise AttributeError("I don't exist!")


class MixedTracker(alarms.TrackerMixin, _PresetTracker):
    pass


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


class MixedRoot(alarms.RootMixin, TreeRootNode):
    def __init__(self, *a, **kw):
        alarms.RootMixin.__init__(self)
        TreeRootNode.__init__(self, *a, **kw)


class InitAlarmNode(MixedNode):
    def __init__(self, *a, **kw):
        self.func_alarm = self.alarm(self.func)
        assert self.func_alarm.root is None

        MixedNode.__init__(self, *a, **kw)

    def func(self):
        pass

#-------------------------------------------------------#
#                        tests                          #
#-------------------------------------------------------#


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


class TestRootMixin(object):
    def test_already_loaded(self):
        tracker = DummyTracker(MixedRoot, MixedNode)
        root = tracker.root
        assert set(root.alarms) == set()
        assert root._alarm_ready

        alarm = DummyAlarm()
        assert not alarm.is_live

        root._add_alarm(alarm)

        assert alarm.is_live

    def test_load_alarm(self, monkeypatch):
        monkeypatch.setattr(alarms, "Alarm", DummyAlarm)
        tracker = DummyTracker(MixedRoot, InitAlarmNode)

        tracker.deserialize("str", u"node: test")

        node = tracker.root.children.next_neighbor
        assert node.func_alarm.root is node.root
        assert node.func_alarm.is_live

    def test_no_support_noop(self, monkeypatch):
        monkeypatch.setattr(alarms, "Alarm", DummyAlarm)
        tracker = SuperDummyTracker(MixedRoot, InitAlarmNode)
        tracker.deserialize("str", u"node: test")

        node = tracker.root.children.next_neighbor
        assert node.func_alarm.root is node.root
        assert not node.func_alarm.is_live

    @pytest.mark.weakref
    def test_thrown_away(self, monkeypatch):
        tracker = DummyTracker(MixedRoot, MixedNode)
        root = tracker.root
        assert set(root.alarms) == set()
        assert root._alarm_ready

        alarm = DummyAlarm()
        assert not alarm.is_live

        root._add_alarm(alarm)
        assert set(root.alarms) == set([alarm])
        ref = weakref.ref(alarm)
        del alarm
        import gc; gc.collect()
        assert not ref()

        assert set(root.alarms) == set()


class TestSetAlarm(object):
    def test_calling(self, reactortime):
        tracker = MixedTracker(TreeRootNode, Node)

        calls = []

        def callback(passed_tracker):
            assert passed_tracker is tracker
            calls.append(1)

        # anchor retains a reference to the deferred
        anchor = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=30))

        assert calls == []
        reactortime.advance(29.9)
        assert calls == []
        reactortime.advance(0.2)
        assert calls == [1]

    def test_delta_calculation(self, reactortime, setdt):
        tracker = MixedTracker(TreeRootNode, Node)
        setdt(2012, 12, 21)
        target = datetime(2012, 12, 21, 23, 59, 59)
        day_seconds = 60 * 60 * 24

        calls = []

        def callback(passed_tracker):
            assert passed_tracker is tracker
            calls.append(1)

        # anchor retains a reference to the deferred
        anchor = tracker._set_alarm(callback=callback, date=target)

        assert calls == []
        reactortime.advance(day_seconds - 1.1)
        assert calls == []
        reactortime.advance(0.2)
        assert calls == [1]

    def test_negative_delta(self, reactortime, setdt):
        tracker = MixedTracker(TreeRootNode, Node)
        setdt(2012, 12, 21)
        target = datetime(2012, 12, 20)
        day_seconds = 60 * 60 * 24

        with pytest.raises(ValueError):
            tracker._set_alarm(date=target)

    @pytest.mark.weakref
    def test_deleted_root(self, reactortime):
        tracker = MixedTracker(TreeRootNode, Node)

        def callback(passed_tracker):  # pragma: no cover
            assert False, "shouldn't have been called"

        # anchor retains a reference to the deferred
        anchor_1 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=30))
        anchor_2 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=60))

        # break the reference loop before throwing it away
        del tracker.root._root
        ref = weakref.ref(tracker.root)
        tracker.deserialize("str", u"node: somenode")
        import gc; gc.collect()
        assert not ref()

        root = tracker.root
        # to force an error should it not detect it via weakref
        del tracker.root

        reactortime.advance(31)
        assert not reactortime.getDelayedCalls()

    @pytest.mark.weakref
    def test_deleted_tracker(self, reactortime):
        tracker = MixedTracker(TreeRootNode, Node)

        def callback(passed_tracker):  # pragma: no cover
            assert False, "shouldn't have been called"

        # anchor retains a reference to the deferred
        anchor_1 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=30))
        anchor_2 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=60))

        # break the reference loop before throwing it away
        root_anchor = tracker.root
        vars(root_anchor).clear()

        tracker.deserialize("str", u"node: somenode")

        # to force an error should it not detect it via weakref
        vars(tracker).clear()
        ref = weakref.ref(tracker)
        del tracker
        import gc; gc.collect()
        assert not ref()

        reactortime.advance(31)
        assert not reactortime.getDelayedCalls()

    @pytest.mark.weakref
    def test_abandoned_deferred(self, reactortime):
        tracker = MixedTracker(TreeRootNode, Node)

        def callback(passed_tracker):  # pragma: no cover
            assert False, "shouldn't have been called"

        # anchor retains a reference to the deferred
        timer, deferred = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=30))
        timer_2, deferred_2 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=60))

        ref = weakref.ref(deferred)
        del deferred
        import gc; gc.collect()
        assert not ref()

        reactortime.advance(31)
        assert reactortime.getDelayedCalls() == [timer_2]

    def test_deterministic_fallback(self, reactortime):
        tracker = MixedTracker(TreeRootNode, Node)

        def callback(passed_tracker):  # pragma: no cover
            assert False, "shouldn't have been called"

        # anchor retains a reference to the deferred
        anchor_1 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=30))
        anchor_2 = tracker._set_alarm(callback=callback,
                delta=timedelta(seconds=60))

        # make sure to hold the reference
        old_root = tracker.root

        tracker.deserialize("str", u"node: somenode")
        import gc; gc.collect()

        reactortime.advance(31)
        assert not reactortime.getDelayedCalls()


class TestAlarm(object):
    def test_delta(self, setdt, reactortime):
        setdt(2012, 12, 29, 4, 33)

        class SomeNode(MixedNode):
            def __init__(self, *a, **kw):
                MixedNode.__init__(self, *a, **kw)
                self.the_alarm = self.alarm(self.callback,
                        delta=timedelta(seconds=30))
                self.callback_called = False

            def callback(self):
                self.callback_called = True

        tracker = MixedTracker(MixedRoot, SomeNode)
        node = tracker.root.createchild(u"some", u"node")
        assert not node.callback_called

        reactortime.advance(31)
        assert node.callback_called

    def test_alter(self, setdt, reactortime):
        setdt(2012, 12, 29, 5, 41)

        class SomeNode(MixedNode):
            def __init__(self, *a, **kw):
                MixedNode.__init__(self, *a, **kw)
                self.the_alarm = self.alarm(self.callback,
                        delta=timedelta(seconds=30))
                self.callback_called = False

            def callback(self):
                self.callback_called = True

        tracker = MixedTracker(MixedRoot, SomeNode)
        node = tracker.root.createchild(u"some", u"node")
        assert not node.callback_called

        reactortime.advance(29)
        setdt(2012, 12, 29, 5, 41, 29)
        assert not node.callback_called

        node.the_alarm.date = node.the_alarm.date + timedelta(seconds=30)
        reactortime.advance(2)
        assert not node.callback_called

        reactortime.advance(30)
        assert node.callback_called

    def test_in_past(self, setdt):
        setdt(2012, 12, 29, 5, 44)

        class SomeNode(MixedNode):
            def __init__(self, *a, **kw):
                MixedNode.__init__(self, *a, **kw)
                self.the_alarm = self.alarm(self.callback,
                        delta=timedelta(seconds=-30))
                self.callback_called = False

            def callback(self):
                self.callback_called = True

        tracker = MixedTracker(MixedRoot, SomeNode)
        node = tracker.root.createchild(u"some", u"node")
        assert node.callback_called
