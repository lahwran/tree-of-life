# FIXME: this file is kinda verbose right now, can be derepeated...

from __future__ import unicode_literals, print_function
import datetime

from treeoflife.userinterface import command, Command
from treeoflife import searching
from treeoflife.util import HandlerDict
from scheduler import ByLog


def _cmd(name, root, text=""):
    """
    convenience func for use in integration tests
    """
    from treeoflife.userinterface import Event, global_commands
    e = Event(source=None,
            root=root,
            command_name=name,
            text=text,
            ui=None)
    c = global_commands.handlers[name]
    ci = e._inject(c)
    return ci.execute()


actions = HandlerDict()


@actions.add()
def finishactivate(node):
    try:
        prev_active = activate(node)
    except searching.NoMatchesError:
        return
    else:
        prev_active.finish()


@actions.add()
def forceactivate(node):
    return activate(node, force=True)


@actions.add()
def activate(node, force=False):
    # TODO: this is a dumb solution for activation checking. should be done
    #       as part of can_activate or such. that doesn't work for creates
    #       yet though, when the hooking up is done to keep track of
    #       where a create will end up, then we can do this.
    exception = []
    for special_node in node.root.active_node.iter_parents():
        if special_node.node_type in ["days", "life"]:
            break
        exception.append(special_node)

    good = True
    for parent in node.iter_parents():
        if parent.node_type in ["days", "life"]:
            break
        if not parent.can_activate:
            good = False
            break

    if node not in exception and not good and not force:
        raise searching.NoMatchesError("tried to activate forbidden node "
                        "(detected by stupid failsafe check)")

    active = node.root.active_node
    node.root.activate(node, force=force)
    return active


@actions.add()
def do_nothing(node):
    pass


class PreviewCommand(Command):
    def preview(self):
        return {"options": [result.preview() for result in self.results[:20]]}

    def execute(self):
        if not self.results:
            # TODO: blow up on nothing to do?
            #       user get no notification right now
            return
        r = self.results[0]
        node = r.produce_node()
        if r.actions:
            action = r.actions[0]
            func = actions.handlers[action]
            func(node)


@command("createauto")
class CreateAutoCommand(PreviewCommand):
    def __init__(self, text, root):
        self.query = searching.parse(text)
        bound = self.query(root.active_node).actions().ignore_overflow()
        results = []
        for result in bound:
            if not result.can_activate and result.exists:
                continue
            if result.can_activate:
                result.actions[:] = ["activate"]
            results.append(result)

        results.sort(key=lambda result: (
            (0,) if result.exists else
            (1, -result.createposition)
        ))
        self.results = results


@command("create")
@command("c")
class CreateCommand(PreviewCommand):
    def __init__(self, text, root):
        self.query = searching.parse(text)
        self.results = self.query(root.active_node)\
                .actions(matches=False).ignore_overflow().list()
        self.results.sort(key=lambda result: -result.createposition)


@command("activate")
@command("a")
class ActivateCommand(PreviewCommand):
    def __init__(self, text, root):
        self.query = searching.parse(text)
        query = self.query(root.active_node)\
                .actions(creates=False).ignore_overflow()
        self.results = []
        for result in query:
            if not result.can_activate:
                continue
            result.actions = ["activate"]
            self.results.append(result)


@command("createactivate")
@command("ca")
class CreateActivateCommand(PreviewCommand):
    def __init__(self, text, root):
        self.query = searching.parse(text)
        results = self.query(root.active_node)\
                .actions(matches=False).ignore_overflow().list()
        results.sort(key=lambda result: -result.createposition)
        self.results = []
        for result in results:
            if not result.can_activate:
                continue
            result.actions = ["activate"]
            self.results.append(result)


@command("finish")
@command("f")
class FinishActivateCommand(ActivateCommand):
    def __init__(self, text, root):
        ActivateCommand.__init__(self, text, root)
        for result in self.results:
            result.actions = ["finishactivate"]


@command("createfinish")
@command("cf")
class CreateFinishActivateCommand(CreateActivateCommand):
    def __init__(self, text, root):
        CreateActivateCommand.__init__(self, text, root)
        for result in self.results:
            result.actions = ["finishactivate"]


@command("forceactivate")
@command("fa")
class ForceActivateCommand(PreviewCommand):
    def __init__(self, text, root):
        self.query = searching.parse(text)
        query = self.query(root.active_node)\
                .actions(creates=False).ignore_overflow()
        self.results = []
        for result in query:
            if result.can_activate:
                continue
            if not type(result.node).can_activate:
                continue
            result.actions = ["forceactivate"]
            self.results.append(result)


class JumpResult(searching._NodeResult):
    def produce_node(self):
        self.node.root.log_event(self.node, "jump")
        return self.node


@command("done")
@command("next")
class DoneCommand(PreviewCommand):
    def __init__(self, root):
        self.bylog = ByLog(root, root.log)
        self.query1 = searching.parse_single("> * :{can_activate}")
        self.query2 = searching.parse_single("-> :{can_activate}")
        self.query3 = searching.parse_single("< :{can_activate}")

        self.results = []
        if (datetime.datetime.now() - self.find_last_jump(root)
                > datetime.timedelta(minutes=30)):
            self.results.append(
                JumpResult(self.bylog.next(),
                    actions=["activate"])
            )

        results = self.query1(root.active_node).actions(creates=False)

        for result in results:
            assert result.exists
            result.actions[:] = ["activate"]
            self.results.append(result)

        if self.results:
            return

        results = self.query2(root.active_node).actions(creates=False)

        for result in results:
            assert result.exists
            result.actions[:] = ["finishactivate"]
            self.results.append(result)

        if self.results:
            return

        results = self.query3(root.active_node).actions(creates=False)

        for result in results:
            assert result.exists
            result.actions[:] = ["finishactivate"]
            self.results.append(result)

    def find_last_jump(self, root):
        for path, event_type, time in reversed(root.log):
            if event_type == "jump":
                return time
        for path, event_type, time in root.log:
            if event_type == "activation":
                return time
        return datetime.datetime.now()
