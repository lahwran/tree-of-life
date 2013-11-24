from datetime import datetime

import pytest

from todo_tracker.tracker import Tracker
from todo_tracker.nodes.days import Day, Sleep, Days, approx_delta
from todo_tracker.nodes.misc import GenericActivate
from todo_tracker.nodes import days


def test_ordering():
    day1 = Day("day", "December 22, 2012", None)
    sleep1 = Sleep("sleep", "December 22, 2012", None)
    day2 = Day("day", "December 23, 2012", None)
    sleep2 = Sleep("sleep", "December 23, 2012", None)

    assert day1 < day2
    assert day2 > day1

    assert day1 < sleep1
    assert sleep1 > day1

    assert sleep1 < day2
    assert day2 > sleep1

    assert sleep1 < sleep2
    assert sleep2 > sleep1

    assert day2 < sleep2
    assert sleep2 > day2

    assert sleep2 > day1
    assert day1 < sleep2


def test_acceptable_day(setdt):
    day = Day("day", "December 22, 2012", None)

    values = {
        (2012, 12, 21, 0,  0,  0):  0,
        (2012, 12, 21, 23, 59, 59): 0,

        (2012, 12, 22, 0,  0,  0):  1,
        (2012, 12, 22, 3,  0,  0):  1,
        (2012, 12, 22, 6,  0,  0):  1,

        (2012, 12, 22, 6,  0,  1):  3,
        (2012, 12, 22, 14, 35, 0):  3,
        (2012, 12, 22, 23, 59, 59): 3,

        (2012, 12, 23, 0,  0,  0):  1,
        (2012, 12, 23, 3,  0,  0):  1,
        (2012, 12, 23, 6,  0,  0):  1,

        (2012, 12, 23, 6,  0,  1):  0,
    }
    for dt, value in values.items():
        setdt(days, *dt)
        assert day.acceptable() == value, str(datetime(dt))


def test_acceptable_sleep(setdt):
    sleep = Sleep("sleep", "December 22, 2012", None)

    values = {
        (2012, 12, 22, 8,  0):  0,
        (2012, 12, 22, 14, 35): 2,
        (2012, 12, 23, 3,  0):  2,
        (2012, 12, 23, 11, 0):  2,
        (2012, 12, 23, 13, 0):  0,
    }

    for dt, value in values.items():
        setdt(days, *dt)
        assert sleep.acceptable() == value, str(datetime(dt))


class _Sortnode(GenericActivate):
    def __init__(self, sort, acceptable):
        super(_Sortnode, self).__init__("day", str(sort), None)
        self._acceptable = acceptable
        self.date = sort
        self.sort = sort

    def __gt__(self, other):
        return self.sort > other.sort

    def __lt__(self, other):
        return self.sort < other.sort

    def acceptable(self):
        return self._acceptable


def should_never_run():
    assert False, "should not have been called"


class TestMakeSkeleton(object):
    def test_acceptability_selection(self):
        tracker = Tracker(skeleton=False)
        days_node = Days("days", None, tracker.root)
        tracker.root.addchild(days_node)

        days_node.addchild(_Sortnode(1, 0))
        days_node.addchild(_Sortnode(2, 0))
        days_node.addchild(_Sortnode(3, 1))
        days_node.addchild(_Sortnode(4, 2))
        days_node.addchild(_Sortnode(5, 2))
        target = _Sortnode(6, 2)
        days_node.addchild(target)
        days_node.addchild(_Sortnode(7, 1))
        days_node.addchild(_Sortnode(8, 0))

        Days.make_skeleton(tracker.root)

        assert tracker.root.active_node is target

        assert tracker.serialize("str") == (
            "days\n"
            "    day: 1\n"
            "    day: 2\n"
            "    day: 3\n"
            "    day: 4\n"
            "    day: 5\n"
            "    day: 6\n"
            "        @active\n"
            "    day: 7\n"
            "    day: 8\n"
        )

    def test_acceptable_parent(self, monkeypatch):
        tracker = Tracker(skeleton=False)
        days_node = Days("days", None, tracker.root)
        tracker.root.addchild(days_node)

        days_node.addchild(_Sortnode(1, 0))
        parent = _Sortnode(2, 1)
        days_node.addchild(parent)
        days_node.addchild(_Sortnode(3, 2))

        midchild = GenericActivate("generic", None, parent)
        parent.addchild(midchild)

        target = GenericActivate("target", None, midchild)
        midchild.addchild(target)
        tracker.root.activate(target)

        monkeypatch.setattr(tracker.root, "activate", should_never_run)

        Days.make_skeleton(tracker.root)

        assert tracker.root.active_node is target
        assert tracker.serialize("str") == (
            "days\n"
            "    day: 1\n"
            "    day: 2\n"
            "        generic\n"
            "            target\n"
            "                @active\n"
            "    day: 3\n"
        )

    def test_unacceptable_parent(self, monkeypatch):
        tracker = Tracker(skeleton=False)
        days_node = Days("days", None, tracker.root)
        tracker.root.addchild(days_node)

        days_node.addchild(_Sortnode(1, 0))
        parent = _Sortnode(2, 0)
        days_node.addchild(parent)
        target = _Sortnode(3, 1)
        days_node.addchild(target)

        midchild = GenericActivate("generic", None, parent)
        parent.addchild(midchild)

        non_target = GenericActivate("non-target", None, midchild)
        midchild.addchild(non_target)
        tracker.root.activate(non_target)

        Days.make_skeleton(tracker.root)

        assert tracker.root.active_node is target
        assert tracker.serialize("str") == (
            "days\n"
            "    day: 1\n"
            "    day: 2\n"
            "        generic\n"
            "            non-target\n"
            "    day: 3\n"
            "        @active\n"
        )

    def test_no_acceptable_activate(self, setdt):
        tracker = Tracker(skeleton=False)
        days_node = Days("days", None, tracker.root)
        tracker.root.addchild(days_node)

        from todo_tracker.nodes import tasks
        setdt(days, tasks, 2012, 12, 22, 12)

        days_node.createchild("day", "December 19, 2012")
        days_node.createchild("day", "December 20, 2012")
        days_node.createchild("day", "December 21, 2012")

        Days.make_skeleton(tracker.root)

        assert tracker.serialize("str") == (
            "days\n"
            "    day: December 19, 2012 (Wednesday, 3 days ago)\n"
            "    day: December 20, 2012 (Thursday, 2 days ago)\n"
            "    day: December 21, 2012 (Friday, yesterday)\n"
            "    day: December 22, 2012 (Saturday, today)\n"
            "        @started: December 22, 2012 12:00:00 PM\n"
            "        @active\n"
        )

    def test_edge_cases(self, setdt):
        tracker = Tracker(skeleton=False)
        days_node = Days("days", None, tracker.root)
        tracker.root.addchild(days_node)

        from todo_tracker.nodes import tasks
        setdt(days, tasks, 2012, 12, 21, 12)

        days_node.createchild("day", "December 19, 2012")
        days_node.addchild(GenericActivate("archived", "herp derp"))
        days_node.createchild("day", "December 20, 2012")
        stucknode = days_node.createchild("day", "December 21, 2012")
        stucknode.started = datetime(2012, 12, 21, 7)
        stucknode.finished = datetime(2012, 12, 21, 8)

        Days.make_skeleton(tracker.root)

        result = tracker.serialize("str")
        print result
        assert result == (
            "days\n"
            "    day: December 19, 2012 (Wednesday, 2 days ago)\n"
            "    archived: herp derp\n"
            "    day: December 20, 2012 (Thursday, yesterday)\n"
            "    day: December 21, 2012 (Friday, today)\n"
            "        @finished: 1h after December 21, 2012 07:00:00 AM\n"
            "    day: December 21, 2012 (Friday, today)\n"
            "        @started: December 21, 2012 12:00:00 PM\n"
            "        @active\n"
        )


def test_out_of_order(setdt):
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    from todo_tracker.nodes import tasks
    setdt(days, tasks, 2013, 12, 29, 12)

    days_node.createchild("day", "December 19, 2012")
    days_node.addchild(GenericActivate("archived", "19 a"))
    days_node.addchild(GenericActivate("archived", "19 b"))

    ignoreme = days_node.createchild("day", "December 21, 2012")
    days_node.addchild(GenericActivate("archived", "21 a"))
    days_node.addchild(GenericActivate("archived", "21 b"))

    days_node.createchild("day", "December 23, 2012", before=ignoreme)
    days_node.addchild(GenericActivate("archived", "23 a"))
    days_node.addchild(GenericActivate("archived", "23 b"))

    days_node.createchild("day", "December 22, 2012")
    days_node.addchild(GenericActivate("archived", "22 out of order a"))
    days_node.addchild(GenericActivate("archived", "22 out of order b"))

    days_node.createchild("day", "December 20, 2012")
    days_node.addchild(GenericActivate("archived", "20 out of order a"))
    days_node.addchild(GenericActivate("archived", "20 out of order b"))

    result = tracker.serialize("str")
    assert result == (
        "days\n"
        "    day: December 19, 2012 (Wednesday, 1 year ago)\n"
        "    archived: 19 a\n"
        "    archived: 19 b\n"
        "    day: December 20, 2012 (Thursday, 1 year ago)\n"
        "    day: December 21, 2012 (Friday, 1 year ago)\n"
        "    archived: 21 a\n"
        "    archived: 21 b\n"

        # December 22 was moved back to before 23, leaving
        # its archived nodes behind
        "    day: December 22, 2012 (Saturday, 1 year ago)\n"
        "    day: December 23, 2012 (Sunday, 1 year ago)\n"
        "    archived: 23 a\n"
        "    archived: 23 b\n"

        "    archived: 22 out of order a\n"
        "    archived: 22 out of order b\n"
        "    archived: 20 out of order a\n"
        "    archived: 20 out of order b\n"
    )


def test_bad_child():
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    with pytest.raises(Exception):
        days_node.addchild(GenericActivate("herp derp", "herk derk"))


def test_archiving(setdt):
    tracker = Tracker(skeleton=False)
    tracker.root.loading_in_progress = True
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    from todo_tracker.nodes import tasks
    setdt(days, tasks, 2013, 12, 22, 12)

    days_node.createchild("day", "July 19, 2012")
    days_node.createchild("day", "July 21, 2012")
    days_node.createchild("day", "July 23, 2012")
    days_node.createchild("day", "July 22, 2012")
    days_node.createchild("day", "July 20, 2012")

    days_node.load_finished()
    tracker.root.loading_in_progress = False

    assert all(node.node_type == "archived" for node in days_node.children)
    assert [node.text for node in days_node.children] == [
        "day: July 19, 2012 (Thursday, 1 year ago)",
        "day: July 20, 2012 (Friday, 1 year ago)",
        "day: July 21, 2012 (Saturday, 1 year ago)",
        "day: July 22, 2012 (Sunday, 1 year ago)",
        "day: July 23, 2012 (Monday, 1 year ago)",
    ]


def test_ui_serialize(setdt):
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    from todo_tracker.nodes import tasks
    setdt(days, tasks, 2012, 12, 22, 12)

    before = [
        days_node.createchild("day", "December 19, 2012"),
        days_node.createchild("day", "December 20, 2012"),
        days_node.createchild("day", "December 21, 2012"),
    ]
    after = [
        days_node.createchild("day", "December 22, 2012"),
        days_node.createchild("day", "December 23, 2012"),
        days_node.createchild("day", "December 24, 2012"),
        days_node.createchild("day", "December 25, 2012"),
        days_node.createchild("day", "December 26, 2012"),
    ]

    Days.make_skeleton(tracker.root)

    assert days_node.ui_serialize() == {
        "children": [node.ui_serialize() for node in after],
        "hidden_children": [node.ui_serialize() for node in before],
        "text": None,
        "type": "days"
    }


def test_ui_serialize_existing(setdt):
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)
    Days.make_skeleton(tracker.root)

    existing_children = object()
    existing_hidden_children = object()

    existing = {
        "children": existing_children,
        "hidden_children": existing_hidden_children,
    }

    assert days_node.ui_serialize(existing) == {
        "children": existing_children,
        "hidden_children": existing_hidden_children,
        "text": None,
        "type": "days"
    }


def test_ui_serialize_rollover(setdt):
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    from todo_tracker.nodes import tasks
    setdt(days, tasks, 2012, 12, 22, 12)

    before = [
        days_node.createchild("day", "December 19, 2012"),
        days_node.createchild("day", "December 20, 2012"),
        days_node.createchild("day", "December 21, 2012"),
    ]
    after = [
        days_node.createchild("day", "December 22, 2012"),
        days_node.createchild("day", "December 23, 2012"),
        days_node.createchild("day", "December 24, 2012"),
        days_node.createchild("day", "December 25, 2012"),
        days_node.createchild("day", "December 26, 2012"),
    ]

    Days.make_skeleton(tracker.root)
    setdt(days, tasks, 2012, 12, 23, 12)

    assert days_node.ui_serialize() == {
        "children": [node.ui_serialize() for node in after],
        "hidden_children": [node.ui_serialize() for node in before],
        "text": None,
        "type": "days"
    }


def test_approx_delta():
    from datetime import date
    now = date(2012, 12, 26)
    assert approx_delta(now, date(2012, 12, 31)) == '5 days'
    assert approx_delta(now, date(2013, 12, 31)) == '1+ year'
    assert approx_delta(now, date(2013, 1, 31)) == '1+ month'
    assert approx_delta(now, date(2013, 4, 7)) == '3+ months'
    assert approx_delta(now, date(2013, 3, 21)) == '2+ months'
    assert approx_delta(now, date(2013, 1, 15)) == '2+ weeks'
    assert approx_delta(now, date(2012, 12, 27)) == 'tomorrow'
    assert approx_delta(now, date(2012, 12, 26)) == 'today'
    assert approx_delta(now, date(2012, 12, 25)) == 'yesterday'
    assert approx_delta(now, date(2011, 12, 25)) == '1 year ago'
    assert approx_delta(now, date(2011, 12, 26)) == '1 year ago'
    assert approx_delta(now, date(2011, 12, 27)) == '12 months ago'
    assert approx_delta(now, date(2012, 12, 20)) == '6 days ago'
    assert approx_delta(now, date(2012, 12, 19)) == '1 week ago'
