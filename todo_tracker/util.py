import os
import tempfile as _tempfile

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
