from todo_tracker.nodes.node import Node, nodecreator
from todo_tracker.nodes.tasks import BaseTask

#######################
### generic nodes

@nodecreator("_gennode")
class GenericNode(Node):
    multiline = True

    def __init__(self, node_type="_gennode", text=None, parent=None):
        super(GenericNode, self).__init__(node_type, text, parent)
        self.metadata = {}

    def setoption(self, option, value):
        self.metadata[option] = value

    def option_values(self, adapter=None):
        return [(x, y, True) for x, y in self.metadata.items()]

@nodecreator("_genactive")
class GenericActivate(GenericNode):
    def __init__(self, node_type="_genactive", text=None, parent=None):
        super(GenericActivate, self).__init__(node_type, text, parent)
        self.deactivate = False

    def setoption(self, option, value):
        if option == "active":
            self.root.activate(self)
        super(GenericActivate, self).setoption(option, value)

    @property
    def active(self):
        return "active" in self.metadata

    @active.setter
    def active(self, newvalue):
        if "active" in self.metadata:
            del self.metadata["active"]

        if newvalue:
            self.metadata["active"] = None

    def start(self):
        if "deactivate" in self.metadata:
            del self.metadata["deactivate"]
            self.deactivate = True

    def finish(self):
        if self.deactivate:
            self.metadata["locked"] = None

    @property
    def can_activate(self):
        return not "locked" in self.metadata

#######################
### comments

@nodecreator("comment")
@nodecreator("IGNORE")
class Comment(Node):
    multiline = True

#######################
### todo

@nodecreator("todo")
class TodoItem(Node):
    children_of = ["todo bucket"]
    allowed_children = []
    multiline = True
    preferred_parent = ["todo bucket"]

@nodecreator("todo bucket")
class TodoBucket(Node):
    toplevel = True
    allowed_children = ["todo"]

    def load_finished(self):
        self.root.todo = self

    def move_review_task(self):
        todo_review = self.root.todo_review
        if not len(self.children):
            self.root.todo_review = None
            todo_review.detach()
            return

        active = self.root.active_node
        if not active:
            return # not much we can do :(
        newparent = None
        after_node = None
        for node in active.iter_parents():
            after_node = newparent
            newparent = node
            if node is self.root or newparent.node_type == "day":
                break

        if newparent == self or newparent == todo_review:
            raise Exception("about to have a fit")
        if todo_review and after_node is todo_review:
            after_node = after_node.next_neighbor

        if todo_review:
            todo_review.detach()
            todo_review = todo_review.copy(parent=newparent)
            newparent.addchild(todo_review, after=after_node)
        else:
            todo_review = newparent.createchild("todo review", after=after_node)

        self.root.todo_review = todo_review

    def addchild(self, child, *args, **keywords):
        child = super(TodoBucket, self).addchild(child, *args, **keywords)
        self.move_review_task()
        return child

@nodecreator("todo review")
class TodoReview(BaseTask):
    textless = True
    def load_finished(self):
        if self.root.todo_review and self.root.todo_review is not self:
            self.root.todo_review.detach()
        self.root.todo_review = self
        self.root.todo.move_review_task()

    def start(self):
        self.root.tracker.start_editor()

    def finish(self):
        super(TodoReview, self).finish()
        self.root.todo.move_review_task()
