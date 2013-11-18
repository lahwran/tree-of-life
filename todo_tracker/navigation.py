from __future__ import unicode_literals, print_function

from todo_tracker.userinterface import command
from todo_tracker import searching


def _eventquery(eventorquery):
    if getattr(eventorquery, "command_name", None) is not None:
        return searching.Query(eventorquery.text), eventorquery.root
    else:
        query, root = eventorquery
        if isinstance(query, basestring):
            query = searching.Query(query)
        return query, root.root


def eventquery(firstarg, *args):
    args = (firstarg,) + args
    if hasattr(args[0], "command_name"):
        prefix = _eventquery(args[0])
    else:
        prefix = _eventquery(args[:2])
    return prefix


@command()
@command("next")
def done(event):
    root = getattr(event, "root", event)
    if activate(":{can_activate}", root):
        return
    finish(searching.chain(
        searching.Query("-> :{can_activate}"),
        searching.Query("< :{can_activate}")
    ), root)


@command()
def createauto(*args):
    query, root = eventquery(*args)
    if getattr(query.segments[-1].matcher, "is_rigid", False):
        return createactivate(query, root, auto=True)
    else:
        return activate(query, root)


@command()
@command("c")
def create(arg1, arg2=None, auto=False):
    query, root = eventquery(arg1, arg2)
    creator = searching.Creator(joinedsearch=query,
            do_auto_add=auto)
    nodes = creator(root.active_node)
    for node in nodes:
        node.user_creation()
    return nodes


def _activate(nodes, root, force=False):
    if not force:
        nodes = searching.tag_filter(nodes, set(["can_activate"]))
    node = searching.first(nodes)
    if node is None:
        return  # no notification...?

    active = root.active_node
    root.activate(node, force=force)
    return active


@command()
@command("a")
def activate(arg1, arg2=None, force=False):
    query, root = eventquery(arg1, arg2)
    nodes = query(root.active_node)
    return _activate(nodes, root, force=force)


@command()
@command("fa")
def forceactivate(*args):
    query, root = eventquery(*args)
    return activate(query, root, force=True)


@command()
@command("f")
def finish(*args):
    query, root = eventquery(*args)
    prev_active = activate(query, root)
    if prev_active is None:
        return

    prev_active.finish()
    return prev_active


@command("ca")
def createactivate(arg1, arg2=None, auto=False):
    query, root = eventquery(arg1, arg2)
    nodes = create(query, root, auto=auto)
    return _activate(nodes, root)


@command("cf")
def createfinish(*args):
    query, root = eventquery(*args)
    prev_active = createactivate(query, root)
    if prev_active is None:
        return

    prev_active.finish()
