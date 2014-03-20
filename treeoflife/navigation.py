from __future__ import unicode_literals, print_function

from treeoflife.userinterface import command
from treeoflife import searching


def _create(query, root, auto=False):
    creator = searching.parse_create(query=query, do_auto_add=auto)
    node = creator(root.active_node)
    node.user_creation()

    return node


def _filter_can_activate(nodes):
    # TODO: this is a dumb solution
    for node in nodes:
        good = True
        for parent in node.iter_parents():
            if parent.node_type in ["days", "life"]:
                break
            if not parent.can_activate:
                good = False
                break
        if good:
            yield node


def _activate(nodes, root, force=False):
    if not force:
        # this is a hackfix for the real problem, but will do for a while
        nodes = _filter_can_activate(nodes)
    node = searching.one(nodes)

    active = root.active_node
    root.activate(node, force=force)
    return active


@command()
@command("next")
def done(root):
    query = searching.parse_single("> * :{can_activate}")
    to_activate = query(root.active_node).first()

    if to_activate is not None:
        _activate([to_activate], root)
        return

    query = searching.chain(
        searching.parse_single("-> :{can_activate}"),
        searching.parse_single("< :{can_activate}")
    )
    nodes = query(root.active_node)

    try:
        prev_active = _activate(nodes, root)
    except searching.NoMatchesError:
        return
    else:
        prev_active.finish()


@command()
def createauto(text, root):
    query = searching.parse_single(text)
    try:
        activate(text, root)
        return
    except searching.NoMatchesError:
        message = "no existing node to activate"

    try:
        createactivate(text, root)
        return
    except searching.NodeNotCreated:
        message += ", and parent node to create under not found"
    except searching.CantCreateError as e:
        message += "; " + str(e)
    raise Exception(message)


@command()
@command("c")
def create(text, root):
    query = searching.parse_single(text)
    return _create(query, root)


@command()
@command("a")
def activate(text, root):
    query = searching.parse(text)
    nodes = query(root.active_node)
    return _activate(nodes, root)


@command()
@command("fa")
def forceactivate(text, root):
    query = searching.parse(text)
    nodes = query(root.active_node)
    return _activate(nodes, root, force=True)


@command()
@command("f")
def finish(text, root):
    query = searching.parse(text)
    nodes = query(root.active_node)
    prev_active = _activate(nodes, root)
    prev_active.finish()


@command("ca")
def createactivate(text, root):
    query = searching.parse_single(text)
    node = _create(query, root, auto=True)

    try:
        prev = _activate([node], root)
    except searching.NoMatchesError:
        # couldn't find activate tag on node. create, but do nothing
        return

    return prev


@command("cf")
def createfinish(text, root):
    prev_active = createactivate(text, root)
    if prev_active is not None:
        prev_active.finish()
