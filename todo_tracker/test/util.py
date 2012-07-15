
from todo_tracker import tracker

class FakeNodeCreator(object):
    def __init__(self, create=tracker.GenericNode):
        self.create = create
