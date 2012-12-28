import weakref

from twisted.internet.defer import Deferred


class Alarm(object):
    def __init__(self, parent, callback, delta=None, date=None):
        self.twisted_timer = None
        self.timer_deferred = None
        self.called = False

        self.parent = parent
        self.callback_func = callback
        if delta is not None:
            self.delta = delta

        self.date = date

        self.root = None
        self.ready_root = None

    def _node_ready(self, root):
        self.root = root

    delta = property()

    @delta.setter
    def delta(self, newdelta):
        self.date = datetime.now() + delta

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, newdate):
        self._date = date
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
                and self.root.tracker.root is self.root)

    def update(self):
        if self.twisted_timer and self.twisted_timer.active():
            self.twisted_timer.cancel()
            self.twisted_timer = None

        if self.active:
            self._set_alarm()

    def _set_alarm(self):
        if not self.active:
            if not self._is_safe():
                self.warn("tried to set alarm, but was unsafe!")
            return

        timer, deferred = self.root.tracker._set_alarm(callback=self._callback,
                date=self.date)
        self.twisted_timer = timer
        self.timer_deferred = deferred

    def _go_live(self):
        self.ready_root = self.root
        self.update()

    def super_repr(self, obj):
        return {
            "id": id(obj),
            "repr": repr(obj),
            "str": str(obj),
            "type": type(obj)
        }

    def warn(self, message):
        log.msg("WARNING: %s %r" % (message, {
            "ready_root": self.super_repr(self.ready_root),
            "root": self.super_repr(self.root),
            "tracker_root": self.super_repr(self.root.tracker.root),
            "date": self.super_repr(self.date),
            "called": self.super_repr(self.called),
        }))

    def _callback(self, tracker):
        self.called = True
        if not self.active:
            self.warn("timer fired but alarm was inactive!")
            return

        self.callback_func()


class NodeMixin(object):
    def __init__(self):
        self.alarms = weakref.WeakSet()

    def _insertion_hook(self):
        if self.root is None:
            return

        for alarm in list(getattr(self, "alarms", [])):
            alarm._node_ready(root=self.root)
            self.root._add_alarm(alarm)

    def alarm(self, *args, **kwargs):
        result = Alarm(self, *args, **kwargs)
        self.alarms.add(result)
        if self.root is not None:
            result._node_ready(root=self.root)
            self.root._add_alarm(result)
        return result


class RootMixin(object):
    def __init__(self):
        self.alarms = weakref.WeakSet()
        self._alarm_ready = False

    def load_finished(self):
        if getattr(self.tracker, "_set_alarm", None) is not None:
            for alarm in list(self.alarms):
                alarm._go_live()
            self._alarm_ready = True

    def _add_alarm(self, alarm):
        self.alarms.add(alarm)
        if self._alarm_ready:
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
        self.timers = []

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

    def make_callback(self, original_callback):
        return self._make_callback(weakref.ref(original_callback),
                target_type=repr(type(original_callback)),
                target_repr=repr(original_callback),
                target_str=str(original_callback))

    def _make_callback(self, ref, target_type, target_repr, target_str):
        def proxy(tracker_ref):
            tracker = tracker_ref()
            if not self.alive:
                self.die()
                return result

            assert tracker is not None, ("should not have failed to resolve "
                    "tracker on a live ProxyCache")

            callback = ref()

            if callback is None:
                log.msg("callback fired, target didn't exist: %s %s %s" % (
                    target_type, target_repr, target_str))

            return callback(tracker)
        return proxy

    def add_timer(self, timer):
        self.timers.append(weakref.ref(timer))

    def die(self):
        for timer_ref in self.timers:
            timer = timer_ref()
            if timer_ref is None:
                continue
            try:
                timer.cancel()
            except ValueError:
                continue


class TrackerMixin(object):
    def __init__(self):
        self._alarm_proxy_caches = weakref.WeakKeyDictionary()

    def _set_alarm(self, callback=None, delta=None, date=None):
        deferred = Deferred()
        if callback is not None:
            deferred.addCallback(callback)

        if delta is None:
            current_time = datetime.datetime()
            if date <= current_time:
                raise Exception("wat? %r %r" % (date, current_time))
            delta = date - current_time

        seconds = delta.total_seconds()

        # weakref hack, weakref hacks everywhere
        # if you're just reading this code, you can
        # pretend that these next few lines are just:
        # reactor.callLater(seconds, deferred.callback, self)
        # this is only relevant if you're worried about reloading of self.root
        proxy = self._alarm_proxy_caches.setdefault(self.root,
                    ProxyCache(self.root, self))
        callback = proxy.make_callback(deferred.callback)
        timer = reactor.callLater(seconds, callback, weakref.ref(self))
        proxy.add_timer(timer)
        # and we return you to your regularly scheduled sanity

        return timer, deferred
