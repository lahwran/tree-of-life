from __future__ import unicode_literals, print_function

from treeoflife.tracker import Tracker, nodecreator
from treeoflife import navigation
from treeoflife import searching
from treeoflife.nodes import references
from treeoflife.nodes import node
from treeoflife.file_storage import serialize_to_str

import pytest


@pytest.fixture
def tracker():
    tracker = Tracker(skeleton=False)
    return tracker


@pytest.fixture(params=[u"depends", u"reference"])
def reftype(request):
    return request.param


def _dump(nodes, getiterator=lambda x: x.children, depth=0, proxyinfo=True,
        ids=False):
    result = []
    for node in nodes:
        if ids:
            strnode = u"%s#%s: %s" % (node.node_type, node.id, node.text)
        else:
            strnode = u"%s: %s" % (node.node_type, node.text)
        if proxyinfo and isinstance(node, references.ProxyNode):
            strnode = u"proxy: " + strnode
        result.append(u" " * depth * 4 + strnode)
        result.extend(_dump(getiterator(node), getiterator, depth + 1,
            proxyinfo=proxyinfo, ids=ids))
    return result


def test_reference(tracker, reftype):
    tracker.deserialize({"life":
        u"task#11111: \xfctarget\n"
        u"    task#22222: \xfcsomechild\n"
        u"        task#33333: \xfcsomechild\n"
        u"    comment#44444: \xfcderp\n"
        u"%s#aaaaa: <- \xfctarget\n" % reftype
    })

    assert len(tracker.root.find(reftype).one().children) == 2

    assert _dump(tracker.root.find(reftype), ids=True) == [
        u"%s#aaaaa: #11111" % reftype,
        u"    proxy: task#22222: \xfcsomechild",
        u"        proxy: task#33333: \xfcsomechild",
        u"    proxy: comment#44444: \xfcderp"
    ]


def test_nested_reference(tracker, reftype):
    tracker.deserialize({"life":
        u"task#trgt1: \xfctarget\n"
        u"    task: \xfcsomechild\n"
        u"        task: \xfcsomechild\n"
        u"    comment: \xfcderp\n"
        u"task#trgt2: \xfcsome other thingy\n"
        u"    task: \xfcdo some work\n"
        u"        reference: << > \xfctarget\n"
        u"    task: \xfcdo some other work\n"
        u"%s: <- task\n" % reftype
    })

    x = _dump(tracker.root.find(reftype))
    y = [
        u"%s: #trgt2" % reftype,
        u"    proxy: task: \xfcdo some work",
        u"        proxy: reference: #trgt1",
        u"            proxy: task: \xfcsomechild",
        u"                proxy: task: \xfcsomechild",
        u"            proxy: comment: \xfcderp",
        u"    proxy: task: \xfcdo some other work"
    ]
    assert x == y


def test_nested_createchild(tracker, reftype):
    tracker.deserialize({"life":
        u"task#trgt1: \xfctarget\n"
        u"    task: \xfcsomechild\n"
        u"        task: \xfcsomechild\n"
        u"    comment: \xfcderp\n"
        u"task#trgt2: \xfcsome other thingy\n"
        u"    task: \xfcdo some work\n"
        u"        reference: << > \xfctarget\n"
        u"    task: \xfcdo some other work\n"
        u"%s: <- task\n" % reftype
    })

    somechild = tracker.root.find(u"%s > task > "
                u"reference > \xfcsomechild" % reftype).one()
    node = somechild.createchild(u"task", u"\xfctest")
    node2 = tracker.root.find(u"task > task > reference > "
                u"task > \xfctest").one()
    assert node._px_target is node2
    assert node2._px_target is tracker.root.find(
                u"task > task > \xfctest").one()

    assert _dump(tracker.root.find("*")) == [
        u"task: \xfctarget",
        u"    task: \xfcsomechild",
        u"        task: \xfcsomechild",
        u"        task: \xfctest",
        u"    comment: \xfcderp",
        u"task: \xfcsome other thingy",
        u"    task: \xfcdo some work",
        u"        reference: #trgt1",
        u"            proxy: task: \xfcsomechild",
        u"                proxy: task: \xfcsomechild",
        u"                proxy: task: \xfctest",
        u"            proxy: comment: \xfcderp",
        u"    task: \xfcdo some other work",
        u"%s: #trgt2" % reftype,
        u"    proxy: task: \xfcdo some work",
        u"        proxy: reference: #trgt1",
        u"            proxy: task: \xfcsomechild",
        u"                proxy: task: \xfcsomechild",
        u"                proxy: task: \xfctest",
        u"            proxy: comment: \xfcderp",
        u"    proxy: task: \xfcdo some other work"
    ]


def test_createchild(tracker, reftype):
    tracker.deserialize({"life":
        u"task#trgt1: \xfctarget\n"
        u"    task: \xfcsomechild\n"
        u"        task: \xfcsomechild\n"
        u"    comment: \xfcderp\n"
        u"%s: <- \xfctarget\n" % reftype
    })

    somechild = tracker.root.find(u"%s > \xfcsomechild" % reftype).one()
    somechild.createchild(u"task", u"\xfctest")

    assert _dump(tracker.root.find("*")) == [
        u"task: \xfctarget",
        u"    task: \xfcsomechild",
        u"        task: \xfcsomechild",
        u"        task: \xfctest",
        u"    comment: \xfcderp",
        u"%s: #trgt1" % reftype,
        u"    proxy: task: \xfcsomechild",
        u"        proxy: task: \xfcsomechild",
        u"        proxy: task: \xfctest",
        u"    proxy: comment: \xfcderp",
    ]


def test_parent(tracker, reftype):
    tracker.deserialize({"life":
        u"task: \xfctarget 1\n"
        u"    task: \xfctarget 2\n"
        u"        task: \xfctarget 3\n"
        u"%s: <-" % reftype
    })

    proxy_3 = tracker.root.find(u"%s > * > \xfctarget 3" % reftype).one()
    proxy_2 = tracker.root.find(u"%s > \xfctarget 2" % reftype).one()
    reference = tracker.root.find(reftype).one()
    assert proxy_3.parent is proxy_2
    assert proxy_2.parent is reference


class TestProxynode(object):
    def test_activate(self, tracker, reftype, setdt):
        setdt(2014, 1, 1, 1, 1)
        tracker.deserialize({"life":
            u"task: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"%s: <-\n"
            u"days\n"
            u"    day: today\n"
            u"        reference: << > %s\n"
            u"            @active\n" % (reftype, reftype)
        })

        root = tracker.root

        # manual search just in case
        days = tracker.root.children.prev_neighbor
        day = days.children.next_neighbor
        ref = day.children.prev_neighbor

        assert root.active_node is ref

        setdt.increment(seconds=1)
        navigation._cmd("done", tracker.root)
        assert root.active_node is root.find(
                u"days > day > reference > task").one()
        setdt.increment(seconds=1)
        navigation._cmd("done", tracker.root)
        assert root.active_node is root.find(
                u"days > day > reference > task > task").one()
        setdt.increment(seconds=1)
        navigation._cmd("done", tracker.root)
        assert root.active_node is root.find(
                u"days > day > reference > task").one()
        setdt.increment(seconds=1)
        navigation._cmd("done", tracker.root)
        assert root.active_node is root.find(
                u"days > day > reference").one()
        setdt.increment(seconds=1)
        navigation._cmd("done", tracker.root)
        assert root.active_node is root.find(
                u"days > day").one()

        reference = tracker.root.find(u"days > day > reference").one()
        target_3 = tracker.root.find(u"** > \xfctarget 3").one()
        target_2 = tracker.root.find(u"** > \xfctarget 2").one()
        target_1 = tracker.root.find(u"\xfctarget 1").one()

        assert reference.started
        assert target_1.started
        assert target_2.started > target_1.started
        assert target_3.started > target_2.started
        assert target_3.finished > target_3.started
        assert target_2.finished > target_3.finished
        assert not target_1.finished
        assert reference.finished > target_2.finished

    def test_reposition(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s: <- \xfctarget 1\n" % reftype
        })

        target_3 = tracker.root.find(u"task > task > \xfctarget 3").one()
        target_4 = tracker.root.find(u"task > \xfctarget 4").one()

        proxy_3 = tracker.root.find(u"%s > task > \xfctarget 3"
                                    % reftype).one()
        proxy_4 = tracker.root.find(u"%s > \xfctarget 4" % reftype).one()

        proxy_3 = proxy_3.detach()
        proxy_3.parent = proxy_4

        proxy_4.addchild(proxy_3)

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 2",
            u"    task: \xfctarget 4",
            u"        task: \xfctarget 3",
            u"%s: #trgt1" % reftype,
            u"    proxy: task: \xfctarget 2",
            u"    proxy: task: \xfctarget 4",
            u"        proxy: task: \xfctarget 3",
        ]

    def test_reposition_2(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s#trgt2: <-\n"
            u"reference: <-\n" % reftype
        })

        target_3 = tracker.root.find(u"task > task > \xfctarget 3").one()
        target_4 = tracker.root.find(u"task > \xfctarget 4").one()

        proxy_3 = tracker.root.find(u"%s -> "
                u"reference > task > \xfctarget 3" % reftype).one()

        detached = proxy_3.detach()
        detached.parent = target_4

        target_4.addchild(detached)
        assert target_4.find(u"*").one() is target_3

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 2",
            u"    task: \xfctarget 4",
            u"        task: \xfctarget 3",
            u"%s: #trgt1" % reftype,
            u"    proxy: task: \xfctarget 2",
            u"    proxy: task: \xfctarget 4",
            u"        proxy: task: \xfctarget 3",
            u"reference: #trgt2",
            u"    proxy: task: \xfctarget 2",
            u"    proxy: task: \xfctarget 4",
            u"        proxy: task: \xfctarget 3",
        ]

    def test_reposition_3(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"    task: \xfctarget 3\n"
            u"%s: <- \xfctarget 1\n" % reftype
        })

        target_2 = tracker.root.find(u"task > \xfctarget 2").one()
        target_3 = tracker.root.find(u"task > \xfctarget 3").one()

        proxy_2 = tracker.root.find(u"%s > \xfctarget 2" % reftype).one()

        detached = proxy_2.detach()
        detached.parent = target_3

        target_3.addchild(detached)
        assert target_3.find(u"*").one() is target_2

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 3",
            u"        task: \xfctarget 2",
            u"%s: #trgt1" % reftype,
            u"    proxy: task: \xfctarget 3",
            u"        proxy: task: \xfctarget 2",
        ]

    def test_copy_1(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s: <- \xfctarget 1\n" % reftype
        })

        target_3 = tracker.root.find(u"task > task > \xfctarget 3").one()
        target_4 = tracker.root.find(u"task > \xfctarget 4").one()

        proxy_3 = tracker.root.find(reftype + u" > task > \xfctarget 3").one()
        proxy_4 = tracker.root.find(reftype + u" > \xfctarget 4").one()

        target_3_new = proxy_3.copy()
        target_3_new.parent = proxy_4

        proxy_4.addchild(target_3_new)

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 2",
            u"        task: \xfctarget 3",
            u"    task: \xfctarget 4",
            u"        task: \xfctarget 3",
            u"%s: #trgt1" % reftype,
            u"    proxy: task: \xfctarget 2",
            u"        proxy: task: \xfctarget 3",
            u"    proxy: task: \xfctarget 4",
            u"        proxy: task: \xfctarget 3",
        ]

    def test_copy_2(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s: <- \xfctarget 1\n" % reftype
        })

        target_3 = tracker.root.find(u"task > task > \xfctarget 3").one()
        target_4 = tracker.root.find(u"task > \xfctarget 4").one()

        proxy_3 = tracker.root.find(reftype + u"> task > \xfctarget 3").one()
        proxy_4 = tracker.root.find(reftype + u"> \xfctarget 4").one()

        target_3_new = proxy_3.copy(parent=proxy_4)

        target_4.addchild(target_3_new)

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 2",
            u"        task: \xfctarget 3",
            u"    task: \xfctarget 4",
            u"        task: \xfctarget 3",
            reftype + u": #trgt1",
            u"    proxy: task: \xfctarget 2",
            u"        proxy: task: \xfctarget 3",
            u"    proxy: task: \xfctarget 4",
            u"        proxy: task: \xfctarget 3",
        ]

    def test_creation(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"%s: <-" % reftype
        })

        target_2 = tracker.root.find(reftype + u" > ").one()

        target_2.createchild(u"task", u"\xfctest")

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 2",
            u"        task: \xfctest",
            reftype + u": #trgt1",
            u"    proxy: task: \xfctarget 2",
            u"        proxy: task: \xfctest"
        ]

    def test_whacky_reposition_setparent(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#toref: \xfcto reference\n"
            u"    task: \xfcdummy\n"
            u"        task: \xfcmove me\n"
            u"    task: \xfcparent\n"
            u"%s: <- \xfcto reference\n" % reftype
        })

        proxy = tracker.root.find(reftype + u" > task > \xfcmove me").one()
        parent = tracker.root.find(reftype + u"> task: \xfcparent").one()
        move_me = proxy._px_target

        move_me.detach()

        # this is to make sure assigning to parent doesn't blow things up
        proxy.parent = parent
        assert proxy.parent is parent

        parent.addchild(proxy)

        assert _dump(tracker.root.children) == [
            u"task: \xfcto reference",
            u"    task: \xfcdummy",
            u"    task: \xfcparent",
            u"        task: \xfcmove me",
            reftype + u": #toref",
            u"    proxy: task: \xfcdummy",
            u"    proxy: task: \xfcparent",
            u"        proxy: task: \xfcmove me",
        ]

    def test_whacky_reposition_noneparent(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#toref: \xfcto reference\n"
            u"    task: \xfcdummy\n"
            u"        task: \xfcmove me\n"
            u"    task: \xfcparent\n"
            u"%s: <- \xfcto reference\n" % reftype
        })

        proxy = tracker.root.find(reftype + u"> task > \xfcmove me").one()
        parent = tracker.root.find(reftype + u"> task: \xfcparent").one()
        move_me = proxy._px_target

        move_me.detach()

        # this is to make sure assigning to parent doesn't blow things up
        proxy.parent = None
        assert proxy.parent is None

        parent.addchild(proxy)

        assert _dump(tracker.root.children) == [
            u"task: \xfcto reference",
            u"    task: \xfcdummy",
            u"    task: \xfcparent",
            u"        task: \xfcmove me",
            reftype + u": #toref",
            u"    proxy: task: \xfcdummy",
            u"    proxy: task: \xfcparent",
            u"        proxy: task: \xfcmove me",
        ]

    def test_set_text(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#toref: \xfcto reference\n"
            u"    task: \xfcto rename\n"
            u"%s: <-" % reftype
        })

        to_rename = tracker.root.find(reftype + u' > \xfcto rename').one()
        to_rename.text = u"\xfcrenamed"

        assert _dump(tracker.root.children) == [
            u"task: \xfcto reference",
            u"    task: \xfcrenamed",
            reftype + ": #toref",
            u"    proxy: task: \xfcrenamed"
        ]

    def test_export(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task: \xfcto reference\n"
            u"    task#aaaaa: \xfcparent\n"
            u"        task: \xfcchild 1\n"
            u"        task: \xfcchild 2\n"
            u"        task: \xfcchild 3\n"
            u"%s: <-" % reftype
        })

        from treeoflife.file_storage import serialize

        result = serialize(tracker.root.find(reftype + u" > \xfcparent").one())
        assert result == [
            u"task#aaaaa: \xfcparent"
        ]

    def test_no_options(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task: \xfcto reference\n"
            u"    task: \xfctarget\n"
            u"%s: <-" % reftype
        })

        target = tracker.root.find(reftype + u"> \xfctarget").one()

        with pytest.raises(AttributeError) as excinfo:
            target.options

        assert "do not have" in excinfo.value.message


class TestRefnode(object):
    def test_creation(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#abcde: \xfctarget 1\n"
            u"{}: <-".format(reftype)
        })

        ref = tracker.root.find(reftype).one()

        ref.createchild(u"task", u"\xfctest")

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctest",
            reftype + u": #abcde",
            U"    proxy: task: \xfctest"
        ]

    def test_unfinish(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#abcde: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"days\n"
            u"    day: today\n"
            u"        @active\n"
            u"        {}: << >\n".format(reftype)
        })

        navigation._cmd("done", tracker.root)
        refnode = tracker.root.find(u"** > " + reftype).one()
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]
        navigation._cmd("finish", tracker.root, u"<")
        target = tracker.root.find(u"task: \xfctarget 1").one()
        if reftype == u"depends":
            assert target.finished
        else:
            assert not target.finished
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde"
        ]
        assert tracker.root.active_node.node_type == u"day"

        navigation._cmd("forceactivate", tracker.root, u">")
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not target.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]

    def test_unfinish_notinitialized(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#abcde: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"days\n"
            u"    day: today\n"
            u"        @active\n"
            u"        {}: << >\n"
            u"            @started\n"
            u"            @finished\n".format(reftype)
        })

        refnode = tracker.root.find(u"** > " + reftype).one()
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + u": " + refnode.text
        ]
        assert tracker.root.active_node.node_type == u"day"
        target = tracker.root.find(u"task: \xfctarget 1").one()
        if reftype == u"depends":
            assert target.finished
        else:
            assert not target.finished

        navigation._cmd("forceactivate", tracker.root, u">")
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not refnode._px_target.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]

    def test_unfinish_targetfinished(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#abcde: \xfctarget 1\n"
            u"    @started\n"
            u"    @finished\n"
            u"    task: \xfctarget 2\n"
            u"days\n"
            u"    day: today\n"
            u"        @active\n"
            u"        {}: << >\n"
            u"            @started\n"
            u"            @finished\n".format(reftype)
        })

        refnode = tracker.root.find(u"** > " + reftype).one()
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + u": " + refnode.text
        ]
        assert tracker.root.active_node.node_type == u"day"
        target = tracker.root.find(u"task: \xfctarget 1").one()
        assert target.finished

        navigation._cmd("forceactivate", tracker.root, u">")
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not refnode._px_target.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]

    def test_initial_state(self, tracker, reftype):
        creator = tracker.nodecreator.creators[reftype]
        ref = creator(reftype, u"<-")

        assert ref._px_target is None
        assert ref.children.length == 0

        tracker.deserialize({"life":
            u"task: \xfctarget\n"
            u"    task: \xfcchild\n"
        })

        tracker.root.addchild(ref)

        assert ref._px_target is tracker.root.find(u"task").one()

    def test_export(self, tracker, reftype):
        tree = (
            u"task#55555: \xfctarget\n"
            u"    task#44444: \xfcsomechild\n"
            u"        task#33333: \xfcsomechild\n"
            u"    comment#22222: \xfcderp\n"
            u"{}#11111: %s\n".format(reftype)
        )
        tracker.deserialize({"life": tree % u"<- \xfctarget"})

        assert tracker.serialize()["life"] == tree % u"#55555"

    def test_removechild(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task#abcde: \xfcreferenced\n"
            u"    task: \xfctoremove\n"
            u"{}: <-\n".format(reftype)
        })
        reference = tracker.root.find(reftype).one()

        toremove = reference.find(u"task").one()
        reference.removechild(toremove)
        assert _dump(tracker.root.children) == [
            u"task: \xfcreferenced",
            u"{}: #abcde".format(reftype)
        ]


def test_child_loop(tracker, reftype):
    tracker.deserialize({"life":
        u"task: a\n"
        u"    task: b\n"
        u"        task: e\n"
        u"        task: f\n"
        u"        task: g\n"
        u"    task: c\n"
        u"    task: d\n"
        u"%s: <-" % reftype
    })

    a = tracker.root.find(reftype).one()
    b = a.find(u"b").one()
    c = a.find(u"c").one()
    d = a.find(u"d").one()
    e = a.find(u"b > e").one()
    f = a.find(u"b > f").one()
    g = a.find(u"b > g").one()

    assert a.children._next_node is b
    assert a.children is b._prev_node
    assert c is b._next_node
    assert c._prev_node is b
    assert c._next_node is d
    assert c is d._prev_node
    assert a.children is d._next_node
    assert a.children._prev_node is d

    assert b.children._next_node is e
    assert b.children is e._prev_node
    assert f is e._next_node
    assert f._prev_node is e
    assert f._next_node is g
    assert f is g._prev_node
    assert b.children is g._next_node
    assert b.children._prev_node is g


class TestSearchCreateIntegration(object):
    def test_proxied_create(self, tracker, reftype):
        tracker.deserialize({"life":
            u"task: target\n"
            u"%s: <-" % reftype
        })
        creator = searching.parse_create(reftype + u" > task: test")
        node = creator(tracker.root)
        proxy = tracker.root.find(reftype + u"> test").one()
        assert node is proxy

    def test_mini_child_loop(self, tracker, reftype):
        tracker.deserialize({"life":
            "task: target\n"
            "%s: <-" % reftype
        })
        creator = searching.parse_create(reftype + u"> task: test")
        node = creator(tracker.root)
        assert node

        proxy_task = tracker.root.find(reftype + u"> test").one()
        target_task = tracker.root.find(u"target > test").one()
        reference = tracker.root.find(reftype).one()
        target = tracker.root.find(u"target").one()

        unwrap = reference.unwrap
        wrap = reference.get_proxy

        assert unwrap(reference) is target
        assert wrap(target) is reference
        assert unwrap(proxy_task) is target_task
        assert wrap(target_task) is proxy_task

        assert target_task._next_node is target.children
        assert target_task._prev_node is target.children
        assert proxy_task._next_node is reference.children
        assert proxy_task._prev_node is reference.children

        assert target_task.parent is target
        assert proxy_task.parent is reference


def test_simple_interaction(tracker, reftype):
    tracker.deserialize({"life":
        u"task: target\n"
        u"days\n"
        u"    day: today\n"
        u"        @started\n"
        u"        %s: << > target\n"
        u"            @active\n" % reftype
    })

    navigation._cmd("createauto", tracker.root, u"task: test")

    active_node = tracker.root.active_node
    proxy = tracker.root.find(u"days > today > " + reftype + u" > test").one()
    target = tracker.root.find(u"target > test").one()
    assert active_node is proxy
    assert proxy is not target
    assert proxy._px_target is target
    assert proxy._px_root.get_proxy(target) is proxy

    navigation._cmd("createfinish", tracker.root, u"-> task: test 2")

    target = tracker.root.find(u"target").one()
    assert target.started
    first_child = target.children.next_neighbor
    assert first_child.started
    assert first_child.finished
    second_child = first_child.next_neighbor
    assert second_child.started
    assert not second_child.finished

    proxy_active = tracker.root.find(u"days > day > "
            + reftype + u"> test 2").one()
    assert proxy_active is tracker.root.active_node


def test_another_interaction(tracker, reftype):
    tracker.deserialize({"life":
        u"task: target\n"
        u"days\n"
        u"    day: today\n"
        u"        @started\n"
        u"        %s: << > target\n"
        u"            @active\n" % reftype
    })

    navigation._cmd("createauto", tracker.root, u"task: test 1")
    navigation._cmd("createfinish", tracker.root, u"< > +task: test 2")

    target = tracker.root.find(u"target").one()

    assert target.started
    first_child = target.children.next_neighbor
    assert first_child.started
    assert first_child.finished
    second_child = first_child.next_neighbor
    assert second_child.started
    assert not second_child.finished

    proxy_active = tracker.root.find(u"days > day > "
            + reftype + u" > test 2").one()
    assert proxy_active is tracker.root.active_node


def test_str(tracker, reftype):
    tracker.deserialize({"life":
        u"task#abcde: target\n"
        u"    comment: to test against\n"
        u"%s: <-\n" % reftype
    })

    proxy = tracker.root.find(reftype + u" > comment").one()
    proxy_target = proxy._px_target
    assert str(proxy) == str(proxy_target)

    ref = tracker.root.find(reftype).one()
    assert str(ref) == reftype + u": target"

    if reftype == u"reference":
        ref2 = references.Reference(u"reference", u"<- task: target")
        assert str(ref2) == u"reference: <- task: target"
        assert ref2.text == u"<- task: target"

        tracker.root.addchild(ref2)
        assert str(ref2) == reftype + u": target"
        assert ref2.text == u"#abcde"
    elif reftype == u"depends":
        for x in [u"depends", u"dep", u"depend"]:
            ref2 = references.Depends(x, u"<- task: target")
            assert str(ref2) == u"depends: <- task: target"

            tracker.root.addchild(ref2)
            assert str(ref2) == reftype + u": target"
    else:  # pragma: no cover
        assert False


def test_recursion(tracker, reftype):
    tracker.deserialize({"life":
        u"task#abcde: target\n"
        u"    task: something\n"
        u"        %s: < target\n" % reftype
    })

    assert _dump(tracker.root.children) == [
        u"task: target",
        u"    task: something",
        u"        %s: #abcde" % reftype,
        u"            proxy: task: something",
        u"                proxy: %s: <recursing>" % reftype,
    ]


def test_ui_dictify(tracker, reftype):
    tracker.deserialize({"life":
        (u"task#targt: target\n"
        u"    task#abcde: child\n"
        u"%s#rfrnc: <-\n"
        u"%s#rfrn2: <-\n"
        ) % (reftype, reftype)
    })

    child = tracker.root.find(reftype + u" > child").one()
    assert child.ui_dictify() is None
    assert tracker.root.ui_graph() == {
        "rfrn2": {
            "type": reftype,
            "text": "#rfrnc",
            "children": ["abcde"],
            "id": "rfrn2",
            "active_id": "targt",
            "finished": False,
            "started": False,
            "target": "rfrnc"
        },
        "rfrnc": {
            "type": reftype,
            "text": "#targt",
            "children": ["abcde"],
            "id": "rfrnc",
            "active_id": "targt",
            "finished": False,
            "started": False,
            "target": "targt"
        },
        "abcde": {
            "type": "task",
            "text": "child",
            "id": "abcde",
            "active_id": "abcde",
            "finished": False,
            "started": False,
        },
        "targt": {
            "type": "task",
            "text": "target",
            "id": "targt",
            "active_id": "targt",
            "finished": False,
            "started": False,
            "children": ["abcde"]
        },
        "00000": {
            "type": "life",
            "text": None,
            "id": "00000",
            "children": ["targt", "rfrnc", "rfrn2"]
        }
    }


def test_no_query_finished(tracker, monkeypatch):
    # this one does _not_ apply to depends, hence no reftype
    # depends has to do a query to make sure the target is marked
    monkeypatch.setattr(references.Reference, "find", None)
    tracker.deserialize({"life":
        u"reference: <-\n"
        u"    @started\n"
        u"    @finished"
    })


def test_reference_finished(tracker, reftype):
    tracker.deserialize({"life":
        u"task: finished node\n"
        u"    @started: June 1, 2013 1:00 am\n"
        u"    @finished: June 1, 2013 2:00 am\n"
        u"%s: <-" % reftype
    })

    reference = tracker.root.find(reftype).one()
    assert not reference.started
    assert reference.finished


def test_depends_finished_node(tracker, reftype):
    tracker.deserialize({"life":
        u"task: finished node\n"
        u"    @started: June 1, 2013 1:00 am\n"
        u"    @finished: June 1, 2013 2:00 am\n"
        u"%s: <-\n"
        u"    @finished: June 2, 2013 2:00 am" % reftype
    })

    reference = tracker.root.find(reftype).one()
    target = tracker.root.find(u"task").one()
    assert not reference.started
    assert reference.finished
    assert reference.finished > target.finished


def test_reference_started(tracker, reftype):
    tracker.deserialize({"life":
        u"task: finished node\n"
        u"%s: <-\n"
        u"    @started: June 1, 2013 1:00 am\n" % reftype
    })

    reference = tracker.root.find(reftype).one()
    target = reference._px_target
    assert reference.started == target.started
    assert not reference._px_didstart


def test_depends_propogate_finished(tracker):
    tracker.deserialize({"life":
        u"task: finished node\n"
        u"depends: <-\n"
        u"    @started: June 1, 2013 1:00 am\n"
        u"    @finished: June 2, 2013 1:00 am\n"
    })

    dep = tracker.root.find(u"depends").one()
    target = tracker.root.find(u"task").one()
    assert dep._px_target is None
    assert dep.finished == target.finished
    assert not dep._px_didfinish


def test_reference_category(tracker, reftype):
    tracker.deserialize({"life":
        u"category: stuff\n"
        u"    task: stuff\n"
        u"days\n"
        u"    day: today\n"
        u"        %s: << > category" % reftype
    })

    ref = tracker.root.find(u'** > ' + reftype).one()
    tracker.root.activate(ref)

    assert ref.started


def test_reference_category_existingtime(tracker, reftype):
    tracker.deserialize({"life":
        u"category: stuff\n"
        u"    task: stuff\n"
        u"days\n"
        u"    day: today\n"
        u"        %s: << > category\n"
        u"            @started: December 19, 1994 11:55 PM" % reftype
    })

    ref = tracker.root.find(u'** > ' + reftype).one()

    assert ref.started


def test_unwriteable_started(tracker, monkeypatch, reftype):
    called = []

    class NonTaskNode(node.Node):
        def __setattr__(self, name, value):
            if name == "started":
                called.append(True)
                raise AttributeError
            node.Node.__setattr__(self, name, value)

    monkeypatch.setitem(tracker.nodecreator.creators,
            "nontask", NonTaskNode)

    tracker.deserialize({"life":
        u"nontask: something\n"
        u"    task: something else\n"
        u"        task: something else 3\n"
        u"    task: something else 2\n"
        u"days\n"
        u"    day: today\n"
        u"        %s: << >\n"
        u"            @started\n" % reftype
    })

    ref = tracker.root.find(u"days > day > " + reftype).one()

    assert called[0]
    assert ref.started
    assert not hasattr(ref._px_target, "started")


def test_unwriteable_finished(tracker, monkeypatch):
    called = []

    class NonTaskNode(node.Node):
        def __setattr__(self, name, value):
            if name == "finished":
                called.append(True)
                raise AttributeError
            node.Node.__setattr__(self, name, value)

    monkeypatch.setitem(tracker.nodecreator.creators,
            "nontask", NonTaskNode)

    tracker.deserialize({"life":
        u"nontask: something\n"
        u"    task: something else\n"
        u"        task: something else 3\n"
        u"    task: something else 2\n"
        u"days\n"
        u"    day: today\n"
        u"        depends: << >\n"
        u"            @started\n"
        u"            @finished\n"
    })

    ref = tracker.root.find(u"days > day > depends").one()

    assert called[0]
    assert ref.finished
    assert not hasattr(ref._px_target, "finished")


# search contexts or search quoting are required to make references useful
# test finish with behavior being called
# test target nodes with no finished or started slots
