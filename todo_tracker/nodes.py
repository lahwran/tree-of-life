from todo_tracker.tracker import Tree

class Task(Tree):
    def __init__(self, node_type, text, parent, tree_data):
        super(Task, self).__init__(node_type, text, parent, tree_data)

        self.started = None
        self.finished = None

    @property
    def metadata(self):
        result = {}
        if self.started:
            result[started] = self.started


