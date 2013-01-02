import logging
import os
import tempfile as _tempfile
import time

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

template = """
@property
def {0}(self):
    return self._hack_{0}

@{0}.setter
def {0}(self, newvalue):
    print
    print
    print
    print
    print "writing to {0}: %s" % newvalue
    import traceback
    f = "".join(traceback.format_stack())
    print f
    self._hack_{0} = newvalue
"""


def _monitor(name):
    import inspect
    frames = inspect.stack()
    f = frames[1][0]
    render = template.format(name)
    exec(render, f.f_globals, f.f_locals)
