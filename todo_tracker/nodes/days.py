from datetime import datetime, date, time, timedelta
import logging

from todo_tracker.nodes.node import Node, nodecreator, BooleanOption
from todo_tracker import timefmt
from todo_tracker.nodes.tasks import BaseTask
from todo_tracker.nodes.misc import Archived
from todo_tracker import alarms
from todo_tracker import alarmclock

logger = logging.getLogger(__name__)

task_types = ("day", "sleep")


class DateTask(BaseTask):
    chidren_of = ("days",)
    text_required = True

    @property
    def can_activate(self):
        return super(DateTask, self).can_activate and self.acceptable()

    @property
    def text(self):
        date_str = timefmt.date_to_str(self.date)
        delta = timefmt.approx_delta(datetime.now().date(), self.date)
        date_str += ' (%s, %s)' % (self.date.strftime('%A'), delta)
        return date_str

    @text.setter
    def text(self, new):
        if "(" in new:
            new = new[:new.index('(')]
            new = new.strip()

        self.date = timefmt.str_to_date(new)

    def start(self):
        BaseTask.start(self)
        if self.root.loading_in_progress:
            self.load_finished = self._post_started
        else:
            self._post_started()

    def _post_started(self):
        if self.load_finished == self._post_started:
            del vars(self)["load_finished"]
        self.post_started()

    def post_started(self):
        pass

    def ui_serialize(self, result=None):
        if result is None:
            result = {}

        prev = self.prev_neighbor
        if getattr(prev, "date", None) is None:
            result["prefix_delta"] = 0
        else:
            delta = self.date - prev.date
            result["prefix_delta"] = delta.days * 4

        return super(DateTask, self).ui_serialize(result)

    def search_texts(self):
        types, texts = BaseTask.search_texts(self)
        texts.add(timefmt.approx_delta(datetime.now().date(), self.date))
        texts.add(self.date.strftime('%A'))

        return types, texts


@nodecreator("day")
class Day(DateTask):
    def __gt__(self, other):
        return self.date > other.date

    def __lt__(self, other):
        if other.node_type == "sleep":
            return self.date <= other.date
        return self.date < other.date

    def acceptable(self):
        """
        Returns level of acceptable-ness of activating this day
        """
        now = datetime.now()
        origin = datetime.combine(self.date, time.min)
        start = origin + timedelta(hours=6)
        end = origin + timedelta(days=1)
        morning = end + timedelta(hours=6)
        if now < origin or now > morning:
            return 0
        if now >= end or now <= start:
            return 1
        return 3

    def post_started(self):
        self.parent.prep_sleep(sleep_day=self.date)


def pick_best(func, options, target):
    results = []
    for option in options:
        result = func(option)
        result = result - target
        results.append((abs(result), option))

    results = sorted(results, key=lambda x: x[0])
    result, option = results[0]

    return option


@nodecreator("sleep")
class Sleep(DateTask, alarms.NodeMixin):
    options = (
        timefmt.TimeOption("until_time"),
        timefmt.DatetimeOption("until"),
        timefmt.TimedeltaOption("amount"),
        BooleanOption("sleep_music_played")
    )

    def __init__(self, *a, **kw):
        self.wake_alarm = None  # self.alarm(self.wakeup_music)
        self.sleep_music_alarm = None  # self.alarm(self.sleep_music)
        self.canceller = None
        self.amount = None
        self.until_time = None
        self.until = None
        self.sleep_music_played = False

        DateTask.__init__(self, *a, **kw)

#    def load_finished(self):
#        assert self.config

    def __gt__(self, other):
        if other.node_type == "day":
            return self.date >= other.date
        return self.date > other.date

    def __lt__(self, other):
        return self.date < other.date

    def acceptable(self):
        # because sleep is shifted forwards
        if (datetime.now() - timedelta(hours=12)).date() == self.date:
            return 2
        return 0

    def initialize(self, date, amount=None, until=None):
        self.date = date
        self.update(amount=amount, until=until)

    def _combine_until(self, until):
        assert False, "sleep node is deactivated, please don't run me"
        now = datetime.now()

        def evaluate(date):
            dt = datetime.combine(date, until)
            td = dt - now
            if td < timedelta():
                return timedelta(days=1000)
            return td

        best = pick_best(evaluate,
                set([self.date,
                    self.date + timedelta(days=1),
                    self.date + timedelta(days=2)]),
                timedelta(hours=8))
        until = datetime.combine(best, until)
        assert until > now

        return until

    def update(self, amount=None, until=None):
        logger.error("sleep node is deactivated, please don't run me: %s, %s",
                amount, until)
        return
        assert not self.active, "can't update an active sleep node"
        # can't do both at once
        assert amount is None or until is None, (
                "can't set conflicting times for sleep node")
        # if doing neither, don't erase previous
        if amount is None and until is None:
            return

        if amount is not None:
            self.amount = amount
        else:
            self.amount = None

        if isinstance(until, time):
            self.until_time = until
            until = self._combine_until(until)
        else:
            self.until_time = None

        if until is not None:
            self.until = until
        else:
            self.until = None
        logger.debug("setting %r until %r", self, self.until)

    def _adjust_times(self):
        assert False, "sleep node is deactivated, please don't run me"
        if self.amount is not None:
            self.until = datetime.now() + self.amount

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, active):
        if 0:
            assert False, "sleep node is deactivated, please don't run me"
            self._adjust_times()
            if not self.until:
                self.update(until=time(7, 0))

            self.wake_alarm.date = self.until
            self.sleep_music()

            logger.debug("marking %r active until %r", self, self.until)
        #else:
        #    self.wake_alarm.date = None
        #    logger.debug("marking %r inactive", self)
        self._active = active

    def finish(self):
        DateTask.finish(self)
        if self.canceller:
            assert False, "sleep node is deactivated, please don't run me"
            self.canceller.cancel()
        self.sleep_music_played = False

    @property
    def config(self):
        assert False, "sleep node is deactivated, please don't run me"
        config = self.root.tracker.config.setdefault("sleep", {})
        config.setdefault("evening_music", [])
        config.setdefault("wakeup_music", [])
        return config

    def sleep_music(self):
        assert False, "sleep node is deactivated, please don't run me"
        if self.sleep_music_played:
            return
        self.sleep_music_played = True

        if self.canceller is not None:
            self.canceller.cancel()

        alarmclock.set_volume(1)
        canceller = alarmclock._StopPlaying()
        canceller.add_monitor(self)
        canceller, deferred = alarmclock.play_list(
                self.config["evening_music"],
                canceller=canceller)
        self.canceller = canceller

    def wakeup_music(self):
        assert False, "sleep node is deactivated, please don't run me"
        if self.canceller is not None:
            self.canceller.cancel()

        self.fader = alarmclock.VolumeFader(alarmclock.default_curve,
                seconds=600)
        canceller, deferred = play_list(self.config["wakeup_music"],
                canceller=self.fader.canceller)
        canceller.add_monitor(self)
        self.canceller = canceller
        deferred.addCallback(self.wakeup_complete)

    def _stop_playing_trigger(self):
        assert False, "sleep node is deactivated, please don't run me"
        return self.root.tracker.root is not self.root

    def wakeup_complete(self, cancelled):
        assert False, "sleep node is deactivated, please don't run me"
        self.root.activate_next()


@nodecreator("days")
class Days(Node):
    textless = True
    toplevel = True
    allowed_children = [
        "day",
        "archived",
        "unarchive",
        "sleep"
    ]

    def __init__(self, *args):
        super(Days, self).__init__(*args)
        self.day_children = {}
        self.archive_date = (datetime.now() - timedelta(days=31)).date()

    def active_child(self):
        for parent in self.root.active_node.iter_parents():
            if parent.parent is self:
                return parent
        return None

    def active_day(self):
        child = self.active_child()
        if child is not None and child.node_type != "day":
            return None
        return child

    def active_sleep(self):
        child = self.active_child()
        if child is not None and child.node_type != "sleep":
            return None
        return child

    def prep_sleep(self, amount=None, until=None, sleep_day=None):
        current = self.active_child()
        if current.node_type == "sleep":
            raise Exception("already sleeping")

        assert current.node_type == "day"

        if sleep_day is None:
            sleep_day = (datetime.now() - timedelta(hours=4)).date()
        warn_skip = []
        sleep_node = None

        iterator = current.iter_forward()
        for node in iterator:
            if node.node_type in task_types:
                if node.date > sleep_day:
                    sleep_node = None
                    break
                elif node.node_type == "sleep" and node.date == sleep_day:
                    sleep_node = node
                    break
                else:
                    warn_skip.append(node)

        if sleep_node is None:
            sleep_node = Sleep("sleep", "today", self)
            sleep_node.initialize(date=sleep_day, amount=amount, until=until)
            self.addchild(sleep_node)
        else:
            sleep_node.update(amount=amount, until=until)

        for node in warn_skip:
            message = "WARNING: skipped %r" % node
            if not sleep_node.find_node(["comment: %s" % message]):
                sleep_node.createchild("comment", message)

        return sleep_node

    def sleep(self, amount=None, until=None):
        if not sleep_node.can_activate:
            raise Exception("Couldn't activate sleep node")
        prev_active = self.root.active_node
        self.root.activate(sleep_node)

        for node in prev_active.iter_parents():
            node.finish()
            if node is current:
                break

    def wakeup(self):
        sleep = self.active_sleep
        if not sleep:
            raise Exception("Already awake")

    @classmethod
    def make_skeleton(cls, root):
        root.days = root.find_node(["days"]) or root.createchild('days')

        do_activate = False
        if root.active_node is None:
            do_activate = True
        else:
            for parent in root.active_node.iter_parents():
                if (parent.node_type in task_types and
                        parent.acceptable()):
                    break
            else:
                do_activate = True

        if do_activate:
            acceptables = []
            for child in root.days.children:
                if child.node_type in task_types:
                    acceptability = child.acceptable()
                    if acceptability:
                        if not child.can_activate:
                            logger.warn("node was acceptable but"
                                " could not activate: %r", child)
                            continue
                        acceptables.append((acceptability, child))

            if acceptables:
                acceptables = sorted(acceptables, key=lambda x: x[0])
                root.activate(acceptables[-1][1])
            else:
                today = root.days.createchild("day", "today")
                root.activate(today)

    def addchild(self, child, before=None, after=None):
        if child.node_type in task_types:
            if before is not None or after is not None:
                logger.warn("attempted to specify position of days-sorted "
                        "node")

            before = None
            after = None
            for existing_child in reversed(self.children):
                if existing_child.node_type not in task_types:
                    continue

                if (existing_child.node_type == child.node_type and
                        existing_child.date == child.date):
                    logger.warn("duplicate nodes added: %r and %r",
                            existing_child, child)
                elif existing_child < child:
                    break
                else:
                    before = existing_child
        if child.node_type not in self.allowed_children:
            raise Exception("node %s cannot be child of %r" % (
                child._do_repr(parent=False), self))

        ret = super(Days, self).addchild(child, before=before, after=after)
        if child.node_type == "day":
            self.day_children[child.date] = child
        return ret

    def load_finished(self):
        for child in self.children:
            if child.node_type == "day" and child.date < self.archive_date:
                prev_node = child.prev_neighbor
                next_node = child.next_neighbor
                child.detach()
                self.addchild(Archived.fromnode(child, parent=self),
                        before=next_node, after=prev_node)

    def ui_serialize(self, result=None):
        if result is None:
            result = {}

        today = self.active_child()
        past_days = []
        future_days = []
        current = past_days
        for node in self.children:
            if node is today:
                current = future_days
            current.append(node)

        if "hidden_children" not in result and past_days:
            hidden = [child.ui_serialize() for child in past_days]
            result["hidden_children"] = hidden
        if "children" not in result and future_days:
            children = [child.ui_serialize() for child in future_days]
            result["children"] = children

        return super(Days, self).ui_serialize(result)
