import traceback
import weakref

from twisted.internet.defer import Deferred

from todo_tracker.exceptions import LoadError
from todo_tracker.nodes.node import TreeRootNode, nodecreator
from todo_tracker.file_storage import loaders, serializers


class ErrorContext(object):
    def __init__(self):
        self.line = None


class AlarmProxyCache(object):
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
        def proxy(tracker_ref):
            tracker = tracker_ref()
            if not self.alive:
                self.die()
                return result

            assert tracker is not None, ("should not have failed to resolve "
                    "tracker on a live AlarmProxyCache")

            return original_callback(tracker)
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


class Tracker_Greppable_Fun(object):
    def __init__(self, skeleton=True, nodecreator=nodecreator):
        self.make_skeleton = skeleton
        self.nodecreator = nodecreator

        self.root = TreeRootNode(self, self.nodecreator)
        if self.make_skeleton:
            self.root.make_skeleton()

        self._alarm_proxy_caches = weakref.WeakKeyDictionary()

    def deserialize(self, format, reader):
        self.root = root = TreeRootNode(self, self.nodecreator)
        stack = []
        lastnode = root
        lastindent = -1
        metadata_allowed_here = False

        error_context = ErrorContext()  # mutable thingy

        try:
            parser = loaders.handlers[format](reader)
            parser.error_context = error_context
            for indent, is_metadata, node_type, text in parser:
                if indent > lastindent:
                    if indent > lastindent + 1:
                        raise LoadError("indented too far")
                    stack.append(lastnode)
                    metadata_allowed_here = True
                elif indent < lastindent:
                    stack = stack[:int(indent) + 1]
                lastindent = indent

                parent = stack[-1]

                if is_metadata:
                    if not metadata_allowed_here:
                        raise LoadError('metadata in the wrong place')
                    parent.setoption(node_type, text)
                    lastnode = None
                else:
                    if node_type != "-":
                        metadata_allowed_here = False

                    node = self.nodecreator.create(node_type, text, parent)
                    if node is not None:
                        parent.addchild(node)
                    lastnode = node
        except LoadError as e:
            e.error_context = error_context
            raise
        except Exception as e:
            new_e = LoadError("UNHANDLED ERROR:\n %s" % traceback.format_exc())
            new_e.error_context = error_context
            raise new_e

        if self.make_skeleton:
            root.make_skeleton()

        for depth, node in root.iter_flat_children():
            node.load_finished()

    def serialize(self, format, *args, **keywords):
        serializer = serializers.handlers[format]
        return serializer(self.root, *args, **keywords)

    def start_editor(self):
        raise NotImplementedError

    def set_alarm(self, callback=None, delta=None, date=None):
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
                    AlarmProxyCache(self.root, self))
        callback = proxy.make_callback(deferred.callback)
        timer = reactor.callLater(seconds, callback, weakref.ref(self))
        proxy.add_timer(timer)
        # and we return you to your regularly scheduled sanity

        return timer, deferred
