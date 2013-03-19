from todo_tracker import nodes
from todo_tracker.nodes.node import _NodeCreatorTracker
from collections import defaultdict


class FakeNodeCreator(_NodeCreatorTracker):
    def __init__(self, create=nodes.GenericNode):
        _NodeCreatorTracker.__init__(self)
        self.creators = defaultdict(lambda: create)

    def exists(self, node_type):
        return True

    def values(self):
        return [self.create]
