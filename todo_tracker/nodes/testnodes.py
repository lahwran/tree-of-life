"""
Nodes for interactive/full integration testing purposes
"""
from __future__ import unicode_literals, print_function

import datetime

from todo_tracker.nodes.node import Node, nodecreator, BooleanOption
from todo_tracker.nodes.tasks import BaseTask
from todo_tracker import alarms


@nodecreator("_test_alarm")
class AlarmTestNode(BaseTask, alarms.NodeMixin):
    def __init__(self, *args, **kwargs):
        self.thealarm = self.alarm(self.derp)
        BaseTask.__init__(self, *args, **kwargs)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, newvalue):
        self._active = newvalue
        if newvalue:
            self.thealarm.delta = datetime.timedelta(seconds=10)

    def derp(self):
        listeners = self.root.tracker.listeners
        for listener in listeners:
            listener.sendmessage({
                "prompt": ["test alarm fired", self.text]
            })
