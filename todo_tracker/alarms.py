import weakref
import datetime
import logging
import uuid

from twisted.internet.defer import Deferred
from twisted.internet import reactor

logger = logging.getLogger(__name__)


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

    def _node_ready(self, root):
        self.root = root

    delta = property()

    @delta.setter
    def delta(self, newdelta):
        self.date = datetime.datetime.now() + newdelta

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, newdate):
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
        if self.twisted_timer and self.twisted_timer.active():
            self.twisted_timer.cancel()
            self.twisted_timer = None
            self.timer_deferred = None

        if not self.active:
            return

        self.parent.alarms.add(self)
        if self.date < datetime.datetime.now():
            self._callback(None)
        else:
            timer, deferred = self.root.tracker._set_alarm(
                    callback=self._callback,
                    date=self.date)
            self.twisted_timer = timer
            self.timer_deferred = deferred

    def _go_live(self):
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
        logger.warn("%s %r", message, data)

    def _callback(self, tracker):
        if not self.active:
            self.warn("timer fired but alarm was inactive!")
            return
        self.called = True

        # allow deallocation - no need to hold the reference once it's called
        # the callback can re-activate it though, which will pass through
        # self.update which will re-add it
        self.parent.alarms.remove(self)

        self.callback_func()


class NodeMixin(object):
    alarms = lazyproperty(set)

    def _insertion_hook(self):
        if self.root is None:
            return

        for alarm in list(self.alarms):
            alarm._node_ready(root=self.root)
            self.root._add_alarm(alarm)

    def alarm(self, *args, **kwargs):
        result = Alarm(self, *args, **kwargs)
        self.alarms.add(result)
        if getattr(self, "root", None) is not None:
            result._node_ready(root=self.root)
            self.root._add_alarm(result)
        return result


class RootMixin(object):
    _alarm_ready = lazyproperty(lambda: False)
    alarms = lazyproperty(weakref.WeakSet)

    def _tracker_support_available(self):
        return getattr(self.tracker, "_set_alarm", None) is not None

    def load_finished(self):
        if self._tracker_support_available():
            for alarm in list(self.alarms):
                alarm._go_live()
            self._alarm_ready = True

    def _add_alarm(self, alarm):
        self.alarms.add(alarm)
        if self._alarm_ready and self._tracker_support_available():
            alarm._go_live()


class ProxyCache(object):
    """
    Proxy for timers that will automatically unregister when a root is unloaded
    """
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
        self.timers.add(timer)

    def die(self):
        logger.info("Freeing Alarm Proxy Cache initialized at %r",
                self.init_time)
        for timer in list(self.timers):
            try:
                timer.cancel()
            except ValueError:
                continue


class TrackerMixin(object):
    _alarm_proxy_caches = lazyproperty(weakref.WeakKeyDictionary)

    def _set_alarm(self, callback=None, delta=None, date=None):
        """
        Set an alarm.
        IMPORTANT: you *must* retain a reference to the returned deferred!
        failure to do so can cause the callback to not fire. this function
        is normally called by an Alarm instance, which also must be held
        onto to stay live.
        """
        deferred = Deferred()
        if callback is not None:
            deferred.addCallback(callback)

        if delta is None:
            current_time = datetime.datetime.now()
            if date <= current_time:
                raise ValueError("wat? %r %r" % (date, current_time))
            delta = date - current_time

        seconds = delta.total_seconds()

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
