from __future__ import unicode_literals, print_function

import traceback
import json
import os

from twisted.internet.defer import Deferred

from treeoflife.exceptions import LoadError, ErrorContext
from treeoflife.nodes.node import TreeRootNode, nodecreator
from treeoflife import file_storage


class Tracker(object):
    filenames = ["log", "life"]

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

    def deserialize(self, files):
        self.root = root = self.roottype(self, self.nodecreator,
                loading_in_progress=True)
        root.loading_in_progress = True

        #log_data = files.get('log', u'')
        #self.root.log = <load_log>(log_data)

        stack = []
        lastnode = root
        lastindent = -1
        metadata_allowed_here = False

        error_context = ErrorContext()  # mutable thingy

        try:
            life_data = files.get('life', u'')
            parser = file_storage.parse_string(life_data)
            parser.error_context = error_context
            for indent, is_metadata, nodeid, node_type, text in parser:
                if node_type == "":
                    indent = lastindent
                    if lastnode is not None and lastnode.node_type != "":
                        indent += 1
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

                    node = self.nodecreator.create(node_type, text, parent,
                            nodeid=nodeid)
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

    def serialize(self):
        return {
            "life": file_storage.serialize_to_str(self.root),
            #"log": <save_log>(self.root.log)
        }

    def load(self, save_dir):
        config_path = os.path.join(save_dir, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as reader:
                self.config = json.loads(reader.read())

        files = {}
        for filename in self.filenames:
            path = os.path.join(save_dir, filename)
            if os.path.exists(path):
                with open(path, "r") as reader:
                    files[filename] = reader.read().decode("utf-8")

        self.deserialize(files)

    def save(self, save_dir):
        config_path = os.path.join(save_dir, "config.json")
        with open(config_path, "w") as writer:
            json.dump(self.config, writer, sort_keys=True,
                    indent=4)

        files = self.serialize()
        for filename, data in files.items():
            path = os.path.join(save_dir, filename)
            with open(path, "w") as writer:
                writer.write(data.encode("utf-8"))
