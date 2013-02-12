import weakref
import datetime
import logging
import uuid

from twisted.internet.defer import Deferred
from twisted.internet import reactor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lazyproperty(func):
    sentinel = object()
    f = "_lazyproperty_" + str(uuid.uuid4())

    def prop_get(self):
        result = getattr(self, f, sentinel)
        if result is sentinel:
            result = func()
            setattr(self, f, result)
        return result

    def prop_set(self, new):
        setattr(self, f, new)

    return property(prop_get, prop_set, doc=func.__doc__)


class Alarm(object):
    _alarms_logger = logging.getLogger(__name__ + ".Alarm")

    def __init__(self, parent, callback, delta=None, date=None):
        self.twisted_timer = None
        self.timer_deferred = None
        self.root = None
        self.ready_root = None
        self.called = False
        self.parent = parent

        self.callback_func = callback
        self._date = None
        if delta is not None:
            self.delta = delta

        if date is not None:
            self.date = date

        self._alarms_logger.debug("alarm %r created: %r, %r, %r, %r",
                self, parent, callback, delta, date)

    def _node_ready(self, root):
        self._alarms_logger.debug("ready: %r, %r", self, root)
        self.root = root

    delta = property()

    @delta.setter
    def delta(self, newdelta):
        date = datetime.datetime.now() + newdelta
        self._alarms_logger.debug("setting %r.delta to %r: %r", self, newdelta,
                date)
        self.date = date

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, newdate):
        self._alarms_logger.debug("setting %r.date to %r", self, newdate)
        self._date = newdate
        self.called = False
        self.update()

    @property
    def active(self):
        return (self._is_safe()
                and self.date is not None
                and not self.called)

    def _is_safe(self):
        return (self.ready_root is self.root
                and self.root is not None
                and self.root.tracker.root is self.root
                and self.parent._next_node is not None
                and self.parent._next_node._prev_node is self.parent)

    def update(self):
        self._alarms_logger.debug("%r.update()", self)
        if self.twisted_timer and self.twisted_timer.active():
            self._alarms_logger.debug("%r.update(): clearing previous timer",
                    self)
            self.twisted_timer.cancel()
            self.twisted_timer = None
            self.timer_deferred = None

        if not self.active:
            self._alarms_logger.debug("%r.update(): not active",
                    self)
            return

        self.parent.alarms.add(self)
        now = datetime.datetime.now()
        if self.date < now:
            self._alarms_logger.debug("%r.update(): callback %r in past, "
                    "firing", self, now - self.date)
#            timer, deferred = self.root.tracker._set_alarm(
#                    callback=self._callback,
#                    delta=datetime.timedelta())
            self._callback(None)
            return
        else:
            self._alarms_logger.debug("%r.update(): setting alarm",
                    self)
            timer, deferred = self.root.tracker._set_alarm(
                    callback=self._callback,
                    date=self.date)
        self.twisted_timer = timer
        self.timer_deferred = deferred

    def _go_live(self):
        self._alarms_logger.debug("%r._go_live(), root=%r",
                self, self.root)
        self.ready_root = self.root
        self.update()

    def super_repr(self, obj):
        return {
            "id": str(id(obj)),
            "repr": repr(obj),
            "str": str(obj),
            "type": repr(type(obj))
        }

    def warn(self, message):
        nn = self.parent._next_node
        data = {
            "ready_root": self.super_repr(self.ready_root),
            "root": self.super_repr(self.root),
            "tracker_root": self.super_repr(self.root.tracker.root),
            "date": self.super_repr(self.date),
            "called": self.super_repr(self.called),
            "parent": self.parent,
            "parent_next_node": nn,
            "parent_rev_link": nn._prev_node if nn is not None else None
        }
        self._alarms_logger.warn("%s: %s %r", self, message, data)

    def _callback(self, tracker):
        if not self.active:
            self.warn("timer fired but alarm was inactive!")
            return
        self._alarms_logger.debug("%s calling callback", self)
        self.called = True

        # allow deallocation - no need to hold the reference once it's called
        # the callback can re-activate it though, which will pass through
        # self.update which will re-add it
        self.parent.alarms.remove(self)

        self.callback_func()


class NodeMixin(object):
    _alarms_logger = logging.getLogger(__name__ + ".NodeMixin")
    alarms = lazyproperty(set)

    def _insertion_hook(self):
        if getattr(self.root, "_add_alarm", None) is None:
            self._alarms_logger.warn("%r node inserted, but %r root "
                    "does not support alarms", self, self.root)
            return
        else:
            self._alarms_logger.debug("%r insertion hook", self)

        for alarm in list(self.alarms):
            alarm._node_ready(root=self.root)
            self.root._add_alarm(alarm)

    def alarm(self, *args, **kwargs):
        result = Alarm(self, *args, **kwargs)
        self.alarms.add(result)
        possible_root = getattr(self, "root", None)
        if getattr(possible_root, "_add_alarm", None) is not None:
            self._alarms_logger.debug("%r creating alarm (%r, %r)",
                    self, args, kwargs)
            result._node_ready(root=self.root)
            self.root._add_alarm(result)
        elif possible_root is not None:
            self._alarms_logger.warn("%r node created an alarm (%r, %r), "
                    "but %r root does not support alarms",
                    self, args, kwargs, self.root)
        else:
            self._alarms_logger.debug("%r node created an alarm (%r, %r), "
                    "but root is not set",
                    self, args, kwargs)
        return result


class RootMixin(object):
    _alarms_logger = logging.getLogger(__name__ + ".RootMixin")

    _alarm_ready = lazyproperty(lambda: False)
    alarms = lazyproperty(weakref.WeakSet)

    def _tracker_support_available(self):
        return getattr(self.tracker, "_set_alarm", None) is not None

    def _alarm_hook(self):
        if self._tracker_support_available():
            self._alarms_logger.info("%r root load_finished", self)
            for alarm in list(self.alarms):
                alarm._go_live()
            self._alarm_ready = True
        else:
            self._alarms_logger.warn("%r root load_finished, but %r tracker "
                    "does not support alarms", self, self.tracker)

    def _add_alarm(self, alarm):
        self.alarms.add(alarm)
        if self._alarm_ready:
            if self._tracker_support_available():
                self._alarms_logger.debug("%r _add_alarm when live: %r",
                    self, alarm)
                alarm._go_live()
            else:
                self._alarms_logger.error("%r root already marked ready, but "
                    "tracker no longer supports alarms (%s)", self,
                    self.tracker)
        else:
            self._alarms_logger.debug("%r _add_alarm before ready: %r",
                    self, alarm)


class ProxyCache(object):
    """
    Proxy for timers that will automatically unregister when a root is unloaded
    """
    _alarms_logger = logging.getLogger(__name__ + ".ProxyCache")

    def __init__(self, root, tracker):
        """
        root: the root node this timerproxy is associated with. tracker.root
                may change, which would cause this timerproxy to free itself
        tracker: tracker.root will be compared with root each time, and if
                they are not identity, then the timerproxy will be freed
        """
        self.root_ref = weakref.ref(root)
        self.tracker_ref = weakref.ref(tracker)
        self.timers = weakref.WeakSet()
        self.init_time = datetime.datetime.now()

    @property
    def alive(self):
        root = self.root_ref()
        if root is None:
            return False

        tracker = self.tracker_ref()
        if tracker is None:
            return False

        if root is not tracker.root:
            return False

        return True

    def make_callback(self, deferred):
        self._alarms_logger.debug("making callback for deferred %s", deferred)
        return self._make_callback(weakref.ref(deferred))

    def _make_callback(self, ref):
        def proxy():
            tracker = self.tracker_ref()
            if not self.alive:
                self.die()
                return

            # won't EVER happen, but in case it does ...
            assert tracker is not None, "tracker went jesus"

            deferred = ref()

            if deferred is None:
                logger.warn("deferred fired, target didn't exist")
                return

            deferred.callback(tracker)
        return proxy

    def add_timer(self, timer):
        self._alarms_logger.debug("adding timer: %r", timer)
        self.timers.add(timer)

    def die(self):
        self._alarms_logger.info("Freeing Alarm Proxy Cache initialized at %r",
                self.init_time)
        for timer in list(self.timers):
            try:
                timer.cancel()
            except ValueError:
                continue


class TrackerMixin(object):
    _alarms_logger = logging.getLogger(__name__ + ".TrackerMixin")
    _alarm_proxy_caches = lazyproperty(weakref.WeakKeyDictionary)

    def _set_alarm(self, callback=None, delta=None, date=None):
        """
        Set an alarm.
        IMPORTANT: you *must* retain a reference to the returned deferred!
        failure to do so can cause the callback to not fire. this function
        is normally called by an Alarm instance, which also must be held
        onto to stay live.
        """
        self._alarms_logger.debug("setting alarm: %r, %r, %r", callback,
                delta, date)
        deferred = Deferred()
        if callback is not None:
            self._alarms_logger.debug("adding callback")
            deferred.addCallback(callback)

        if delta is None:
            current_time = datetime.datetime.now()
            if date <= current_time:
                raise ValueError("wat? %r %r" % (date, current_time))
            delta = date - current_time
            self._alarms_logger.debug("using date to calculate delta: %s",
                    delta)

        seconds = delta.total_seconds()
        self._alarms_logger.debug("setting alarm for %s seconds", seconds)

        # weakref hack, weakref hacks everywhere
        # if you're just reading this code, you can
        # pretend that these next few lines are just:
        # reactor.callLater(seconds, deferred.callback, self)
        # this is only relevant if you're worried about reloading of self.root
        proxy = self._alarm_proxy_caches.setdefault(self.root,
                    ProxyCache(self.root, self))
        callback = proxy.make_callback(deferred)
        timer = reactor.callLater(seconds, callback)
        proxy.add_timer(timer)
        # and we return you to your regularly scheduled sanity

        return timer, deferred
