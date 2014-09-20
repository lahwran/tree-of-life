from __future__ import unicode_literals, print_function

import datetime

from treeoflife.nodes.node import Node, nodecreator
from treeoflife.nodes.tasks import BaseTask, ActiveMarker
from treeoflife.ordereddict import OrderedDict
from treeoflife.file_storage import parse_line
from treeoflife import timefmt


#######################
### generic nodes


@nodecreator("_gennode")
class GenericNode(Node):
    multiline = True

    def __init__(self, node_type="_gennode", text=None, parent=None,
            nodeid=None):
        self.metadata = OrderedDict()
        super(GenericNode, self).__init__(node_type, text, parent, nodeid)

    def setoption(self, option, value):
        self.metadata[option] = value

    def option_values(self, adapter=None):
        result = [(x, y, True) for x, y in self.metadata.items()]
        return result


@nodecreator("_genactive")
class GenericActivate(Node):
    options = (
        ActiveMarker(),
    )
    can_activate = True

    def __init__(self, *args, **kwargs):
        Node.__init__(self, *args, **kwargs)

    def start(self):
        pass

    def finish(self):
        pass

    def unfinish(self):
        pass


@nodecreator("archived")
class Archived(GenericNode):
    def __init__(self, node_type, text, *a, **kw):
        if kw.get("nodeid", None) is None and text:
            _, _, nodeid, _, _ = parse_line(text)
            kw["nodeid"] = nodeid
        GenericNode.__init__(self, node_type, text, *a, **kw)

    @classmethod
    def fromnode(cls, node, parent):
        if node.node_type == "archived":
            newnode = node.copy(parent=parent, children=False, nodeid=node.id)
        else:
            text = "%s#%s: %s" % (node.node_type, node.id, node.text)
            newnode = cls("archived", text, parent, nodeid=node.id)
            for option, value, show in node.option_values():
                if show:
                    newnode.setoption(option, value)
        newnode.setoption("_af", None)

        for child in list(node.children):
            child = child.detach()
            newnode.addchild(cls.fromnode(child, parent=newnode))
        return newnode

    def load_finished(self):
        if ("__af" in self.metadata or
                ("__af", None, True) in self.parent.option_values()):
            self.metadata["__af"] = None
            return

        prev_node = self.prev_neighbor
        next_node = self.next_neighbor
        parent = self.parent
        detached = self.detach()
        parent.addchild(self.fromnode(detached, parent=parent),
                before=next_node, after=prev_node)


@nodecreator("unarchive")
@nodecreator("unarchived")
class Unarchiver(GenericNode):
    def __init__(self, node_type, text, *a, **kw):
        if kw.get("nodeid", None) is None and text:
            _, _, nodeid, _, _ = parse_line(text)
            kw["nodeid"] = nodeid
        GenericNode.__init__(self, node_type, text, *a, **kw)

    @classmethod
    def unarchive(cls, node, parent):
        if node.node_type not in ("archived", "unarchive", "unarchived"):
            newnode = node.copy(parent=parent, children=False, nodeid=node.id)
        else:
            indent, ismetadata, nodeid, node_type, text = parse_line(node.text)
            assert not indent
            assert not ismetadata
            if node_type == "archived":
                indent, ismetadata, nodeid, node_type, text = parse_line(text)
                assert not indent
                assert not ismetadata

            newnode = node.root.nodecreator.create(node_type, text, parent,
                    nodeid=nodeid)
            for option, value, show in node.option_values():
                if show and option != "_af":
                    newnode.setoption(option, value)

        for child in list(node.children):
            child = child.detach()
            newnode.addchild(cls.unarchive(child, parent=newnode))

        return newnode

    def load_finished(self):
        prev_node = self.prev_neighbor
        next_node = self.next_neighbor
        parent = self.parent
        detached = self.detach()
        parent.addchild(self.unarchive(detached, parent=parent),
                after=prev_node, before=next_node)


#######################
### comments


@nodecreator("comment")
@nodecreator("answer")
@nodecreator("solution")
@nodecreator("IGNORE")
class Comment(Node):
    multiline = True

    options = (
        timefmt.DatetimeOption("time"),
    )

    def user_creation(self):
        self.time = datetime.datetime.now()


#######################
### todo


@nodecreator("todo")
class TodoItem(Node):
    children_of = ["todo bucket"]
    allowed_children = []
    multiline = True
    preferred_parent = "<< > todo bucket"


@nodecreator("todo bucket")
class TodoBucket(Node):
    toplevel = True
    allowed_children = ["todo"]

    def load_finished(self):
        self.root.todo = self


class NoActiveMarker(ActiveMarker):
    def get(self, node):
        return False, None
