import pep8
import os

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


def test_pep8():
    styleguide = pep8.StyleGuide(paths=paths, ignore=ignore,
            show_source=True, show_pep8=False)
    report = styleguide.check_files()
    assert not report.total_errors
