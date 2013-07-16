from todo_tracker.userinterface import command
from todo_tracker import searching


def eventquery(eventorquery):
    if getattr(eventorquery, "command_name", None) is not None:
        return searching.Query(eventorquery.text), eventorquery.root
    else:
        query, root = eventorquery
        if isinstance(query, basestring):
            query = searching.Query(query)
        return query, root


def queryevent(func):
    import functools

    @functools.wraps(func)
    def wrapper(firstarg, *args, **kwargs):
        args = (firstarg,) + args
        if hasattr(args[0], "command_name"):
            prefix = eventquery(args[0])
            args = args[1:]
        else:
            prefix = eventquery(args[:2])
            args = args[2:]

        return func(*(prefix + args), **kwargs)
    return wrapper


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
@queryevent
def createauto(query, root):
    if getattr(query.segments[-1].matcher, "is_rigid", False):
        return createactivate(query, root, auto=True)
    else:
        return activate(query, root)


@command()
@command("c")
@queryevent
def create(query, root, auto=False):
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
@queryevent
def activate(query, root, force=False):
    nodes = query(root.active_node)
    return _activate(nodes, root, force=force)


@command()
@command("fa")
@queryevent
def forceactivate(query, root):
    return activate(query, root, force=True)


@command()
@command("f")
@queryevent
def finish(query, root):
    prev_active = activate(query, root)
    if prev_active is None:
        return

    prev_active.finish()
    return prev_active


@command("ca")
@queryevent
def createactivate(query, root, auto=False):
    nodes = create(query, root, auto=auto)
    return _activate(nodes, root)


@command("cf")
@queryevent
def createfinish(query, root):
    prev_active = createactivate(query, root)
    if prev_active is None:
        return

    prev_active.finish()
