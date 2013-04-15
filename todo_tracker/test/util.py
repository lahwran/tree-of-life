from todo_tracker.nodes.node import _NodeCreatorTracker
from collections import defaultdict


class FakeNodeCreator(_NodeCreatorTracker):
    def __init__(self, create=None):
        _NodeCreatorTracker.__init__(self)
        if create is None:
            from todo_tracker.nodes.misc import GenericNode
            create = GenericNode
        self.creators = defaultdict(lambda: create)

    def exists(self, node_type):
        return True

    def values(self):
        return [self.create]
