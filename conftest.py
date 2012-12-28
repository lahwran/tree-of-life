
import pytest
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
        actual_args = []
        for arg in args:
            if getattr(arg, "datetime", None) is not None:
                targets.append(arg)
            else:
                actual_args.append(arg)

        _now = real_datetime(*actual_args, **kwargs)

        patches = {}
        def _add(f):
            patches[f.__name__] = f

        @_add
        @directcall
        def now():
            return _now

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
    return setdt

def pytest_addoption(parser):
    parser.addoption("--weakref", action="store_true",
        dest="weakref",
        help="run tests marked as weakref.")

def pytest_configure(config):
    # register an additional marker
    config.addinivalue_line("markers",
        "weakref: mark test as testing weakref code")

def pytest_runtest_setup(item):
    if ("weakref" in item.keywords
            and not item.config.getoption("weakref")):
        pytest.skip("not running weakref tests")
