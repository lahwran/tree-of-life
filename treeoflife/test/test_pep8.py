from __future__ import unicode_literals, print_function

import pep8
import os
import sys

parent_dir = os.path.dirname(__file__)
root_package = os.path.dirname(parent_dir)
root = os.path.dirname(root_package)
paths = [
    os.path.relpath(filename) for filename in
    [root_package]
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
    "E265",  # comment must start "# " - I generally like that, but I ignore
             # it in some placse
    "E131",  # line continuation alignment - I'm pretty free with this
]


def test_pep8():
    styleguide = pep8.StyleGuide(paths=paths, ignore=ignore,
            show_source=True, show_pep8=False)
    report = styleguide.check_files()
    assert not report.total_errors
