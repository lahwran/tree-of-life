from __future__ import unicode_literals, print_function

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
    "E127",  # E127 is "visual indent mismatch"
    "E126",  # E126 is "over-indented"
    "E124",  # Closing bracket does not match visual indentation
    "E202",  # Whitespace before ) - used for Good Reason in test_time
    "E241",  # Too much whitespace after : or ,
    "E702",  # Multiple statements on one line (get over yourself, I know when
             #     to use this)
    "E121",  # stfu about continued comment on previous line in this file
    "E201",  # whitespace after ( in function call - used for vertical time
             # alignment
]

try:
    import __pypy__
except ImportError:
    __pypy__ = None


def test_pep8():
    styleguide = pep8.StyleGuide(paths=paths, ignore=ignore,
            show_source=True, show_pep8=False)
    if __pypy__ is None:  # pragma: no branch
        report = styleguide.check_files()
        assert not report.total_errors
    else:
        print("WARNING: did not run test due to pypy")  # pragma: no cover
