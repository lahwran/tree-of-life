import itertools
from collections import deque
from treeoflife.tracker import Tracker

tracker = Tracker()
tracker.deserialize("file", open("/Users/lahwran/.treeoflife/life"))


def by_iterator(node):
    """
    does not deal with any kind of changes at all.
    - nodes becoming finished
    - nodes being added
    - nodes being removed
    - nodes being moved

    also doesn't deal with being read very well
    """
    generators = [(by_iterator(subnode)
                    if len(subnode.children)
                    else itertools.repeat(subnode))
                    for subnode in node.children]

    while True:
        for g in generators:
            yield g.next()


def pairs(iterable):
    "from liblahwran"
    iter1 = iter(iterable)
    iter2 = iter(iterable)
    try:
        iter2.next()
    except StopIteration:
        return iter(lambda: None, None)
    return itertools.izip(iter1, iter2)


class ByLog(object):
    # this is currently not the same as by_iterator.
    # WHYYYYYYYYYYYYY???? I DONT GET IT PLS
    def __init__(self, rootnode):
        self.log = []
        self._cache = {}
        self.rootnode = rootnode

    def next(self):
        # note: THIS IS AN INFINITE ITERATOR THAT LOGS EACH PASS
        #       DO NOT USE BLINDLY!
        node = self.rootnode
        while True:
            if not len(node.children):
                result = node
                break
            childid = self._lastactive(node.id)
            if childid is None:
                node = node.children.next_neighbor
                continue

            child = self.rootnode.root.ids[childid]
            newnode = child.next_neighbor
            if newnode is None:
                node = node.children.next_neighbor
            else:
                node = newnode
        self._logpath(result)
        return result

    def _ischild(self, parentid, nodeid):
        if nodeid is None:
            parent = self.rootnode.root.ids[parentid]
            return len(parent.children) == 0

        node = self.rootnode.root.ids.get(nodeid, None)
        if node is None:
            return False
        return node.parent.id == parentid

    def _lastactive(self, parentid):
        try:
            nodeid = self._cache.get(parentid, object())
            if self._ischild(parentid, nodeid):
                return nodeid
            self._cache[parentid] = None
        except KeyError:
            pass

        for logitem in reversed(self.log):
            path = logitem[0]
            maxindex = len(path) - 1
            try:
                index = path.index(parentid)
            except ValueError:
                continue
            if index == maxindex:
                # last time the node's path was active, it was the active node;
                # keep looking, maybe there was a time before that where
                # its child was active
                continue
            result = path[index + 1]
            if not self._ischild(parentid, result):
                # found a node that was active, but it's been moved or deleted
                continue
            break
        else:
            result = None
        self._cache[parentid] = result
        return result

    def _logpath(self, deepestnode):
        path = [node.id for node in list(deepestnode.iter_parents())[::-1]]
        # later I'll want more things in the log items, like date scheduled
        # and stuff. log items will be added by node activation.
        logitem = [path]
        self.log.append(logitem)
        for parentid, childid in pairs(path):
            self._cache[parentid] = childid

    def __iter__(self):
        return self


for x in itertools.islice(ByLog(tracker.root), 10000):
    print u" > ".join(
        unicode(z)
        for z
        in list(x.iter_parents())[::-1]
    ).encode("utf-8")
