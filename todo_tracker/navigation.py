from todo_tracker.userinterface import command
from todo_tracker import searching


def eventquery(eventorquery):
    if getattr(eventorquery, "command_name", None) is not None:
        return searching.Query(eventorquery.text), eventorquery.root
    else:
        query, root = eventorquery
        return query, root


@command()
@command("next")
def done(event):
    root = getattr(event, "root", event)
    finish((searching.chain(
        searching.Query(":{can_activate}"),
        searching.Query("-> :{can_activate}"),
        searching.Query("< :{can_activate}")
    ), root))


@command()
def createauto(event):
    query, root = eventquery(event)
    if getattr(query.segments[-1].matcher, "is_rigid", False):
        return createactivate((query, root), auto=True)
    else:
        return activate((query, root))


@command()
@command("c")
def create(event, auto=False):
    query, root = eventquery(event)
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
        return  # ...?

    active = root.active_node
    root.activate(node, force=force)
    return active


@command()
@command("a")
def activate(event, force=False):
    query, root = eventquery(event)

    nodes = query(root.active_node)
    return _activate(nodes, root, force=force)


@command()
@command("fa")
def forceactivate(event):
    return activate(event, force=True)


@command()
@command("f")
def finish(event):
    query, root = eventquery(event)
    prev_active = activate((query, root))
    if prev_active is None:
        return

    prev_active.finish()


@command("ca")
def createactivate(event, auto=False):
    query, root = eventquery(event)
    nodes = create(event, auto=auto)
    return _activate(nodes, root)


@command("cf")
def createfinish(event):
    prev_active = createactivate(event)
    if prev_active is None:
        return

    prev_active.finish()
