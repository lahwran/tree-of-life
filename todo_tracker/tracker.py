import traceback

from twisted.internet.defer import Deferred

from todo_tracker.exceptions import LoadError
from todo_tracker.nodes.node import TreeRootNode, nodecreator
from todo_tracker.file_storage import loaders, serializers


class ErrorContext(object):
    def __init__(self):
        self.line = None


class Tracker(object):
    def __init__(self, skeleton=True, nodecreator=nodecreator,
            roottype=TreeRootNode):
        self.make_skeleton = skeleton
        self.nodecreator = nodecreator
        self.config = {}

        self.roottype = roottype

        self.root = self.roottype(self, self.nodecreator,
                loading_in_progress=False)
        if self.make_skeleton:
            self.root.make_skeleton()

    def deserialize(self, format, reader):
        self.root = root = self.roottype(self, self.nodecreator,
                loading_in_progress=True)
        root.loading_in_progress = True
        stack = []
        lastnode = root
        lastindent = -1
        metadata_allowed_here = False

        error_context = ErrorContext()  # mutable thingy

        try:
            parser = loaders.handlers[format](reader)
            parser.error_context = error_context
            for indent, is_metadata, node_type, text in parser:
                if indent > lastindent:
                    if indent > lastindent + 1:
                        raise LoadError("indented too far")
                    stack.append(lastnode)
                    metadata_allowed_here = True
                elif indent < lastindent:
                    stack = stack[:int(indent) + 1]
                lastindent = indent

                parent = stack[-1]

                if is_metadata:
                    if not metadata_allowed_here:
                        raise LoadError('metadata in the wrong place')
                    parent.setoption(node_type, text)
                    lastnode = None
                else:
                    if node_type != "-":
                        metadata_allowed_here = False

                    node = self.nodecreator.create(node_type, text, parent)
                    if node is not None:
                        parent.addchild(node)
                    lastnode = node
        except LoadError as e:
            e.error_context = error_context
            raise
        except Exception as e:
            new_e = LoadError("UNHANDLED ERROR:\n %s" % traceback.format_exc())
            new_e.error_context = error_context
            raise new_e

        if self.make_skeleton:
            root.make_skeleton()

        root.load_finished()
        for depth, node in root.iter_flat_children():
            node.load_finished()

        # enable instant load_finished() on node creation
        root.loading_in_progress = False

    def serialize(self, format, *args, **keywords):
        serializer = serializers.handlers[format]
        return serializer(self.root, *args, **keywords)

    def start_editor(self):
        raise NotImplementedError
