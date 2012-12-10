import pep8
import os
import sys

parent_dir = os.path.dirname(__file__)
root_package = os.path.dirname(parent_dir)
root = os.path.dirname(root_package)
files = [os.path.join(root, filename) for filename in [
    "activities.py",
    "cocoa.py"
]]
paths = [
    os.path.relpath(filename) for filename in
    [root_package] + files
]
ignore = [
    "E128",  # E128 is "under-indented"
    "E126",  # E126 is "over-indented"
    "E124",  # Closing bracket does not match visual indentation
    "E202",  # Whitespace before ) - used for Good Reason in test_time
]


class ShutPypyUp(object):
    """
    Workaround for pypy's jit having its head up its
    """
    def __init__(self):
        self.done = False
        sys.settrace(self.trace)

    def trace(self, x, y, z):
        if self.done:
            return None
        return self.trace

try:
    import __pypy__
except ImportError:
    __pypy__ = None


def test_pep8():
    styleguide = pep8.StyleGuide(paths=paths, ignore=ignore,
            show_source=True, show_pep8=False)
    if __pypy__ is not None:
        x = ShutPypyUp()
    else:
        x = None
    report = styleguide.check_files()
    if x:
        x.done = True
    assert not report.total_errors
