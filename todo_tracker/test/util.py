
from todo_tracker import nodes

class FakeNodeCreator(object):
    def __init__(self, create=nodes.GenericNode):
        self.create = create
