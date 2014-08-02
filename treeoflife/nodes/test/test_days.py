from __future__ import unicode_literals, print_function

from datetime import datetime, time, timedelta, date

import pytest

from treeoflife.test.util import match
from treeoflife.tracker import Tracker
from treeoflife.nodes.days import (Day, Sleep, Days,
        _parsehook_dayparse, _parsehook_dayabs)
from treeoflife.nodes.misc import GenericActivate
from treeoflife.exceptions import LoadError
from treeoflife.nodes import days
from treeoflife import searching
from treeoflife import navigation


def test_ordering(setdt):
    setdt(2012, 12, 22, 12)

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
        setdt(*dt)
        assert day.acceptable() == value, str(datetime(dt))


def test_acceptable_sleep(setdt):
    setdt(2012, 1, 1)
    sleep = Sleep("sleep", "December 22, 2012", None)

    values = {
        (2012, 12, 22, 8,  0):  0,
        (2012, 12, 22, 14, 35): 2,
        (2012, 12, 23, 3,  0):  2,
        (2012, 12, 23, 11, 0):  2,
        (2012, 12, 23, 13, 0):  0,
    }

    for dt, value in values.items():
        setdt(*dt)
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

        assert match(tracker.serialize()["life"], (
            "days#?????\n"
            "    day#?????: 1\n"
            "    day#?????: 2\n"
            "    day#?????: 3\n"
            "    day#?????: 4\n"
            "    day#?????: 5\n"
            "    day#?????: 6\n"
            "        @active\n"
            "    day#?????: 7\n"
            "    day#?????: 8\n"
        ))

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
        assert match(tracker.serialize()["life"], (
            "days#?????\n"
            "    day#?????: 1\n"
            "    day#?????: 2\n"
            "        generic#?????\n"
            "            target#?????\n"
            "                @active\n"
            "    day#?????: 3\n"
        ))

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
        assert match(tracker.serialize()["life"], (
            "days#?????\n"
            "    day#?????: 1\n"
            "    day#?????: 2\n"
            "        generic#?????\n"
            "            non-target#?????\n"
            "    day#?????: 3\n"
            "        @active\n"
        ))

    def test_no_acceptable_activate(self, setdt, monkeypatch):
        monkeypatch.setattr(Day, "_post_started", lambda self: None)

        tracker = Tracker(skeleton=False)
        days_node = Days("days", None, tracker.root)
        tracker.root.addchild(days_node)

        setdt(2012, 12, 22, 12)

        days_node.createchild("day", "December 19, 2012 (This should be "
                "ignored)")
        days_node.createchild("day", "December 20, 2012")
        days_node.createchild("day", "December 21, 2012")

        Days.make_skeleton(tracker.root)

        assert match(tracker.serialize()["life"], (
            "days#?????\n"
            "    day#?????: December 19, 2012 (Wednesday, 3 days ago)\n"
            "    day#?????: December 20, 2012 (Thursday, 2 days ago)\n"
            "    day#?????: December 21, 2012 (Friday, yesterday)\n"
            "    day#?????: December 22, 2012 (Saturday, today)\n"
            "        @started: December 22, 2012 12:00:00 PM\n"
            "        @active\n"
        ))


def test_out_of_order(setdt):
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    setdt(2013, 12, 29, 12)

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

    result = tracker.serialize()["life"]
    assert match(result, (
        "days#?????\n"
        "    day#?????: December 19, 2012 (Wednesday, *)\n"
        "    archived#?????: 19 a\n"
        "    archived#?????: 19 b\n"
        "    day#?????: December 20, 2012 (Thursday, *)\n"
        "    day#?????: December 21, 2012 (Friday, *)\n"
        "    archived#?????: 21 a\n"
        "    archived#?????: 21 b\n"

        # December 22 was moved back to before 23, leaving
        # its archived nodes behind
        "    day#?????: December 22, 2012 (Saturday, *)\n"
        "    day#?????: December 23, 2012 (Sunday, *)\n"
        "    archived#?????: 23 a\n"
        "    archived#?????: 23 b\n"

        "    archived#?????: 22 out of order a\n"
        "    archived#?????: 22 out of order b\n"
        "    archived#?????: 20 out of order a\n"
        "    archived#?????: 20 out of order b\n"
    ))


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

    setdt(2013, 12, 22, 12)

    days_node.createchild("day", "July 19, 2012")
    days_node.createchild("day", "July 21, 2012")
    days_node.createchild("day", "July 23, 2012")
    days_node.createchild("day", "July 22, 2012")
    days_node.createchild("day", "July 20, 2012")

    days_node.load_finished()
    tracker.root.loading_in_progress = False

    assert all(node.node_type == "archived" for node in days_node.children)
    assert match("\n".join(node.text for node in days_node.children), (
        "day#?????: July 19, 2012 (Thursday, *)\n"
        "day#?????: July 20, 2012 (Friday, *)\n"
        "day#?????: July 21, 2012 (Saturday, *)\n"
        "day#?????: July 22, 2012 (Sunday, *)\n"
        "day#?????: July 23, 2012 (Monday, *)"
    ))


def test_ui_dictify(setdt, monkeypatch):
    monkeypatch.setattr(Day, "_post_started", lambda self: None)
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    setdt(2012, 12, 22, 12)

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

    assert days_node.ui_dictify() == {
        "children": [node.id for node in after],
        "hidden_children": [node.id for node in before],
        "text": None,
        "type": "days",
        "id": "00001",
    }


def test_ui_dictify_existing():
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

    assert days_node.ui_dictify(existing) == {
        "children": existing_children,
        "hidden_children": existing_hidden_children,
        "text": None,
        "type": "days",
        "id": "00001",
    }


def test_ui_dictify_rollover(setdt, monkeypatch):
    monkeypatch.setattr(Day, "_post_started", lambda self: None)
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    setdt(2012, 12, 22, 12)

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
    setdt(2012, 12, 23, 12)

    assert days_node.ui_dictify() == {
        "children": [node.id for node in after],
        "hidden_children": [node.id for node in before],
        "text": None,
        "type": "days",
        "id": "00001",
    }


def test_ui_dictify_sleepnode(setdt, monkeypatch):
    monkeypatch.setattr(Day, "_post_started", lambda self: None)
    tracker = Tracker(skeleton=False)
    days_node = Days("days", None, tracker.root)
    tracker.root.addchild(days_node)

    setdt(2012, 12, 21, 23)

    before = [
        days_node.createchild("day", "December 19, 2012"),
        days_node.createchild("day", "December 20, 2012"),
        days_node.createchild("day", "December 21, 2012"),
    ]
    after = [
        days_node.createchild("sleep", "December 21, 2012"),
        days_node.createchild("day", "December 22, 2012"),
        days_node.createchild("day", "December 23, 2012"),
        days_node.createchild("day", "December 24, 2012"),
        days_node.createchild("day", "December 25, 2012"),
        days_node.createchild("day", "December 26, 2012"),
    ]
    tracker.root.activate(after[0])

    assert days_node.ui_dictify() == {
        "children": [node.id for node in after],
        "hidden_children": [node.id for node in before],
        "text": None,
        "type": "days",
        "id": "00001",
    }


@pytest.mark.xfail
class TestSleepNode(object):
    def test_properly_initialized(self, setdt):
        setdt(2013, 1, 30, 23)
        node = Sleep("sleep", "today", None)

        assert node.wake_alarm.date is None
        assert not node.wake_alarm.called
        assert node.canceller is None
        assert node.until_time is None
        assert node.until is None
        assert node.amount is None

    @pytest.mark.parametrize(("until", "until_dt"), [
        (time(22, 50), datetime(2013, 1, 31, 22, 50)),
        (time(23,  1), datetime(2013, 1, 30, 23, 01)),
        (time( 1,  0), datetime(2013, 1, 31,  1,  0)),
        (time( 7,  0), datetime(2013, 1, 31,  7,  0)),
        (time(12,  0), datetime(2013, 1, 31,  12, 0)),
        (time(12,  0), datetime(2013, 1, 31,  12, 0)),
    ])
    def test_combine_until(self, setdt, until, until_dt):
        setdt(2013, 1, 30, 23)
        node = Sleep("sleep", "today", None)

        assert node._combine_until(until) == until_dt

    @pytest.mark.parametrize('hour', [1, 13])
    def test_day_creation(self, setdt, hour):
        setdt(2013, 1, 30, hour)
        tracker = Tracker(skeleton=False)

        tracker.deserialize({"life":
            "days\n"
            "    day: today\n"
            "        @active\n"
        })

        days_node = tracker.root.children.next_neighbor
        node = days_node.find('sleep: today').one()
        assert node
        assert node.prev_neighbor.node_type == "day"

    def test_update(self, setdt):
        setdt(2013, 1, 30, 23)

        node = Sleep("sleep", "today", None)

        def _assert(up=None):
            if up:
                node_value.update(up)
            for name, value in node_value.items():
                if value is None:
                    assert getattr(node, name) is None
                else:
                    assert getattr(node, name) == value
        node_value = {}

        _assert({
            "amount": None,
            "until_time": None,
            "until": None
        })

        node._adjust_times()
        _assert()

        newuntil = datetime(2013, 1, 31, 12)
        node.update(until=newuntil)
        _assert({"until": newuntil})

        newuntil = time(7, 0)
        node.update(until=newuntil)
        _assert({
            "until": datetime(2013, 1, 31, 7, 0),
            "until_time": newuntil
        })

        node.update(amount=timedelta(hours=8))
        _assert({
            "until": None,
            "until_time": None,
            "amount": timedelta(hours=8)
        })

        node._adjust_times()
        _assert({
            "until": datetime(2013, 1, 31, 7, 0)
        })

    def test_activation_no_time(self):
        tracker = Tracker(skeleton=False)

        tracker.deserialize({"life":
            "days\n"
            "    day: today\n"
            "        @active\n"
        })

        tracker.root.activate_next()


def test_searchhooks(setdt, monkeypatch):
    monkeypatch.setattr(searching, "parsecreatefilters", [
        _parsehook_dayparse,
        _parsehook_dayabs
    ])
    setdt(2014, 2, 19, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize({"life":
        "task: something\n"
        "days\n"
        "    day: today\n"
        "    day: tomorrow\n"
        "    day: September 20, 2014\n"
    })

    something = tracker.root.find("something").one()
    assert something.find("today").one().date == date(2014, 2, 19)
    assert something.find("tomorrow").one().date == date(2014, 2, 20)
    assert something.find("sept 20, 2014").one().date == date(2014, 9, 20)
    assert not something.find("invalid date sept 20, 1995").first()

    # subject to change
    assert not something.find("sept 21, 2014").first()

    assert (searching.parse("day: today")
            == searching.Queries(searching.parse("today").queries[0]))

    setdt(2014, 2, 20, 12)
    assert something.find("today").one().date == date(2014, 2, 20)


def test_searchhooks_mincreate(setdt, monkeypatch):
    monkeypatch.setattr(searching, "parsecreatefilters", [
        _parsehook_dayparse,
        _parsehook_dayabs
    ])
    setdt(2014, 2, 19, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize({"life":
        "task: something\n"
        "days\n"
        "    day: today\n"
    })

    query = searching.parse("today > does not exist, cannot create")
    assert query(tracker.root).actions().list() is not None


def test_duplicate_day(setdt):
    setdt(2014, 3, 19, 19, 40)

    tracker = Tracker(skeleton=False)
    tracker.deserialize({"life":
        "days\n"
        "    day: today\n"
    })

    n = tracker.root.find("days").one()
    with pytest.raises(LoadError):
        n.createchild("day", "today")


def test_faroff_activate(setdt):
    setdt(2014, 3, 19, 20, 17)

    tracker = Tracker(skeleton=False)
    tracker.deserialize({"life":
        "days\n"
        "    day: today\n"
        "        @active\n"
        "    day: March 25, 2014\n"
    })

    navigation._cmd("create", tracker.root, "March 25, 2014 > task: something")

    navigation._cmd("activate", tracker.root, "March 25, 2014")

    with pytest.raises(searching.NoMatchesError):
        navigation._cmd("activate", tracker.root,
                "March 25, 2014 > task: something")

    assert tracker.root.active_node is tracker.root.find("today").one()
