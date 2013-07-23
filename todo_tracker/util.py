import logging
import os
import tempfile as _tempfile
import time
import functools
import __builtin__

logger = logging.getLogger(__name__)


def tempfile():
    fd, tmp = _tempfile.mkstemp()
    os.close(fd)
    return tmp


class HandlerList(object):
    name = "handlers"
    autodetect = True

    def __init__(self):
        setattr(self, self.name, {})

    def add(self, name=None):
        assert getattr(name, "__call__", None) is None

        def _inner(func):
            _name = name
            if _name is None:
                if self.autodetect:
                    _name = func.__name__
                else:
                    raise Exception("must provide name")
            getattr(self, self.name)[_name] = func
            return func
        return _inner


class Profile(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.started = time.time()

    def __exit__(self, x, y, z):
        self.finished = time.time()
        logger.debug("Profile %r finished in %r", self.name,
                self.finished - self.started)


def memoize(obj):
    cache = {}

    @functools.wraps(obj)
    def wrapper(*a, **kw):
        fs_kw = frozenset(kw.items())

        try:
            return cache[a, fs_kw]
        except KeyError:
            cache[a, fs_kw] = obj(*a, **kw)
            return cache[a, fs_kw]
    wrapper.cache = cache
    return wrapper

template = """
@property
def {0}(self):
    return self._hack_{0}

@{0}.setter
def {0}(self, newvalue):
    import logging
    logger = logging.getLogger("_monitor.{0}")
    logger.debug("writing: %s", newvalue)
    import traceback
    f = "".join(traceback.format_stack())
    print f
    self._hack_{0} = newvalue
"""


def setter(func):
    name = func.__name__

    @functools.wraps(func)
    def get(self):
        return getattr(self, "_real" + name)

    return property(get, func)


def _monitor(name):
    import inspect
    frames = inspect.stack()
    f = frames[1][0]
    render = template.format(name)
    exec(render, f.f_globals, f.f_locals)


def hasattr_(obj, name):
    sentinel = object()
    return getattr(obj, name, sentinel) is not sentinel

hasattr_.is_good_hasattr = True

__builtin__.hasattr = hasattr_
