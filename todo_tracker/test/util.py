from todo_tracker import nodes


class FakeNodeCreator(object):
    def __init__(self, create=nodes.GenericNode):
        self.create = create

    def exists(self, node_type):
        return True

    def values(self):
        return [self.create]
