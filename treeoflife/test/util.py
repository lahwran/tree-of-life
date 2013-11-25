from __future__ import unicode_literals, print_function

from todo_tracker.nodes.node import _NodeCreatorTracker
from collections import defaultdict
from fnmatch import fnmatchcase
from difflib import ndiff


def match(string, pattern):
    matches = fnmatchcase(string, pattern)
    if not matches:
        diff = ndiff(string.splitlines(1), pattern.splitlines(1))
        print("".join(diff))
    return matches


class FakeNodeCreator(_NodeCreatorTracker):
    def __init__(self, create=None):
        _NodeCreatorTracker.__init__(self)
        if create is None:
            from todo_tracker.nodes.misc import GenericNode
            create = GenericNode
        self.creators = defaultdict(lambda: create)

    def exists(self, node_type):
        return True  # pragma: no cover

    def values(self):
        return [self.create]  # pragma: no cover
