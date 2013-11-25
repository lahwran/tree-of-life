"""
Nodes for interactive/full integration testing purposes
"""
from __future__ import unicode_literals, print_function

import datetime

from treeoflife.nodes.node import Node, nodecreator, BooleanOption
from treeoflife.nodes.tasks import BaseTask
from treeoflife import alarms


@nodecreator("_test_alarm")
class AlarmTestNode(BaseTask, alarms.NodeMixin):
    def __init__(self, *args, **kwargs):
        self.thealarm = self.alarm(self.derp)
        BaseTask.__init__(self, *args, **kwargs)

    def start(self):
        if newvalue:
            self.thealarm.delta = datetime.timedelta(seconds=10)

    def finish(self):
        pass

    def derp(self):
        listeners = self.root.tracker.listeners
        for listener in listeners:
            listener.sendmessage({
                "prompt": ["test alarm fired", self.text]
            })
