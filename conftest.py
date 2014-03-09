
import py
import pytest
import time
import datetime
import functools


real_datetime = datetime.datetime

try:
    import __pypy__
    running_on_pypy = True
except ImportError:
    running_on_pypy = False

class directcall(object):
    def __init__(self, func):
        self.func = func
        functools.wraps(func)(self)

    def __call__(self, *args, **kwargs):
        return self.func()

@pytest.fixture
def setdt(monkeypatch):
    def setdt(*args, **kwargs):
        targets = [datetime]

        if "dt" in kwargs:
            _now = kwargs["dt"]
        else:
            _now = real_datetime(*args, **kwargs)

        patches = {}
        def _add(f):
            patches[f.__name__] = f

        @_add
        @directcall
        def now():
            return _now

        monkeypatch.setattr(time, "time",
                lambda: time.mktime(_now.timetuple()))

        if running_on_pypy:
            for patch in patches:
                monkeypatch.setattr(real_datetime, patch, patches[patch])

            return real_datetime
        else:
            @functools.wraps(real_datetime)
            def patcheddatetime(*args, **kwargs):
                return real_datetime(*args, **kwargs)

            for name in vars(real_datetime):
                value = getattr(real_datetime, name)
                setattr(patcheddatetime, name, value)

            for name in patches:
                setattr(patcheddatetime, name, patches[name])

            for target in targets:
                monkeypatch.setattr(target, "datetime", patcheddatetime)

            return patcheddatetime

    def increment(*a, **kw):
        prev = datetime.datetime.now()
        delta = datetime.timedelta(*a, **kw)
        setdt(dt=prev + delta)

    setdt.increment = increment

    return setdt

def pytest_addoption(parser):
    parser.addoption("--weakref", action="store_true",
        dest="weakref",
        help="run tests marked as weakref.")


def patch_pudb(config):
    class PudbShortcuts(object):
        @property
        def db(self):
            capman = config.pluginmanager.getplugin("capturemanager")
            out, err = capman.suspendcapture()

            import sys
            import pudb
            dbg = pudb._get_debugger()

            dbg.set_trace(sys._getframe().f_back)

    import __builtin__
    __builtin__.__dict__["pu"] = PudbShortcuts()


def pytest_configure(config):
    # register an additional marker
    try:
        import pudb
        patch_pudb(config)
    except ImportError:
        errmsg = ("\n\n\n\n"
            "    No pudb installed. install for fancy debugging in tests :)\n"
            "    once installed, can be used simply by putting 'pu.db' on a line\n"
            "    and passing -s to py.test.\n\n\n\n")
        import sys
        sys.stdout.write(errmsg)
        sys.stdout.flush()

    config.addinivalue_line("markers",
        "weakref: mark test as testing weakref code")

def pytest_runtest_setup(item):
    if ("weakref" in item.keywords
            and not item.config.getoption("weakref")):
        pytest.skip("not running weakref tests")
