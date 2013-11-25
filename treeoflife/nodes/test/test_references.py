from __future__ import unicode_literals, print_function

from treeoflife.tracker import Tracker, nodecreator
from treeoflife import navigation
from treeoflife import searching
from treeoflife.nodes import references
from treeoflife.nodes import node

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
    tracker.deserialize("str",
        u"task#11111: \xfctarget\n"
        u"    task#22222: \xfcsomechild\n"
        u"        task#33333: \xfcsomechild\n"
        u"    comment#44444: \xfcderp\n"
        u"%s#aaaaa: <- \xfctarget\n" % reftype
    )

    assert len(tracker.root.find_one(reftype).children) == 2

    assert _dump(tracker.root.find(reftype), ids=True) == [
        u"%s#aaaaa: #11111" % reftype,
        u"    proxy: task#22222: \xfcsomechild",
        u"        proxy: task#33333: \xfcsomechild",
        u"    proxy: comment#44444: \xfcderp"
    ]


def test_nested_reference(tracker, reftype):
    tracker.deserialize("str",
        u"task#trgt1: \xfctarget\n"
        u"    task: \xfcsomechild\n"
        u"        task: \xfcsomechild\n"
        u"    comment: \xfcderp\n"
        u"task#trgt2: \xfcsome other thingy\n"
        u"    task: \xfcdo some work\n"
        u"        reference: << > \xfctarget\n"
        u"    task: \xfcdo some other work\n"
        u"%s: <- task\n" % reftype
    )

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
    tracker.deserialize("str",
        u"task#trgt1: \xfctarget\n"
        u"    task: \xfcsomechild\n"
        u"        task: \xfcsomechild\n"
        u"    comment: \xfcderp\n"
        u"task#trgt2: \xfcsome other thingy\n"
        u"    task: \xfcdo some work\n"
        u"        reference: << > \xfctarget\n"
        u"    task: \xfcdo some other work\n"
        u"%s: <- task\n" % reftype
    )

    somechild = tracker.root.find_one(u"%s > task > "
                u"reference > \xfcsomechild" % reftype)
    node = somechild.createchild(u"task", u"\xfctest")
    node2 = tracker.root.find_one(u"task > task > reference > task > \xfctest")
    assert node._px_target is node2
    assert node2._px_target is tracker.root.find_one(u"task > task > \xfctest")

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
    tracker.deserialize("str",
        u"task#trgt1: \xfctarget\n"
        u"    task: \xfcsomechild\n"
        u"        task: \xfcsomechild\n"
        u"    comment: \xfcderp\n"
        u"%s: <- \xfctarget\n" % reftype
    )

    somechild = tracker.root.find_one(u"%s > \xfcsomechild" % reftype)
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
    tracker.deserialize("str",
        u"task: \xfctarget 1\n"
        u"    task: \xfctarget 2\n"
        u"        task: \xfctarget 3\n"
        u"%s: <-" % reftype
    )

    proxy_3 = tracker.root.find_one(u"%s > * > \xfctarget 3" % reftype)
    proxy_2 = tracker.root.find_one(u"%s > \xfctarget 2" % reftype)
    reference = tracker.root.find_one(reftype)
    assert proxy_3.parent is proxy_2
    assert proxy_2.parent is reference


class TestProxynode(object):
    def test_activate(self, tracker, reftype):
        tracker.deserialize("str",
            u"task: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"%s: <-\n"
            u"days\n"
            u"    day: today\n"
            u"        reference: << > %s\n"
            u"            @active\n" % (reftype, reftype)
        )

        root = tracker.root

        navigation.done(tracker)
        assert root.active_node is root.find_one(
                u"days > day > reference > task")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                u"days > day > reference > task > task")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                u"days > day > reference > task")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                u"days > day > reference")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                u"days > day")

        reference = tracker.root.find_one(u"days > day > reference")
        target_3 = tracker.root.find_one(u"** > \xfctarget 3")
        target_2 = tracker.root.find_one(u"** > \xfctarget 2")
        target_1 = tracker.root.find_one(u"\xfctarget 1")

        assert reference.started
        assert target_1.started
        assert target_2.started > target_1.started
        assert target_3.started > target_2.started
        assert target_3.finished > target_3.started
        assert target_2.finished > target_3.finished
        assert not target_1.finished
        assert reference.finished > target_2.finished

    def test_reposition(self, tracker, reftype):
        tracker.deserialize("str",
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s: <- \xfctarget 1\n" % reftype
        )

        target_3 = tracker.root.find_one(u"task > task > \xfctarget 3")
        target_4 = tracker.root.find_one(u"task > \xfctarget 4")

        proxy_3 = tracker.root.find_one(u"%s > task > \xfctarget 3" % reftype)
        proxy_4 = tracker.root.find_one(u"%s > \xfctarget 4" % reftype)

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
        tracker.deserialize("str",
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s#trgt2: <-\n"
            u"reference: <-\n" % reftype
        )

        target_3 = tracker.root.find_one(u"task > task > \xfctarget 3")
        target_4 = tracker.root.find_one(u"task > \xfctarget 4")

        proxy_3 = tracker.root.find_one(u"%s -> "
                u"reference > task > \xfctarget 3" % reftype)

        detached = proxy_3.detach()
        detached.parent = target_4

        target_4.addchild(detached)
        assert target_4.find_one(u"*") is target_3

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
        tracker.deserialize("str",
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"    task: \xfctarget 3\n"
            u"%s: <- \xfctarget 1\n" % reftype
        )

        target_2 = tracker.root.find_one(u"task > \xfctarget 2")
        target_3 = tracker.root.find_one(u"task > \xfctarget 3")

        proxy_2 = tracker.root.find_one(u"%s > \xfctarget 2" % reftype)

        detached = proxy_2.detach()
        detached.parent = target_3

        target_3.addchild(detached)
        assert target_3.find_one(u"*") is target_2

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctarget 3",
            u"        task: \xfctarget 2",
            u"%s: #trgt1" % reftype,
            u"    proxy: task: \xfctarget 3",
            u"        proxy: task: \xfctarget 2",
        ]

    def test_copy_1(self, tracker, reftype):
        tracker.deserialize("str",
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s: <- \xfctarget 1\n" % reftype
        )

        target_3 = tracker.root.find_one(u"task > task > \xfctarget 3")
        target_4 = tracker.root.find_one(u"task > \xfctarget 4")

        proxy_3 = tracker.root.find_one(reftype + u" > task > \xfctarget 3")
        proxy_4 = tracker.root.find_one(reftype + u" > \xfctarget 4")

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
        tracker.deserialize("str",
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"        task: \xfctarget 3\n"
            u"    task: \xfctarget 4\n"
            u"%s: <- \xfctarget 1\n" % reftype
        )

        target_3 = tracker.root.find_one(u"task > task > \xfctarget 3")
        target_4 = tracker.root.find_one(u"task > \xfctarget 4")

        proxy_3 = tracker.root.find_one(reftype + u"> task > \xfctarget 3")
        proxy_4 = tracker.root.find_one(reftype + u"> \xfctarget 4")

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
        tracker.deserialize("str",
            u"task#trgt1: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"%s: <-" % reftype
        )

        target_2 = tracker.root.find_one(reftype + u" > ")

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
        tracker.deserialize("str",
            u"task#toref: \xfcto reference\n"
            u"    task: \xfcdummy\n"
            u"        task: \xfcmove me\n"
            u"    task: \xfcparent\n"
            u"%s: <- \xfcto reference\n" % reftype
        )

        proxy = tracker.root.find_one(reftype + u" > task > \xfcmove me")
        parent = tracker.root.find_one(reftype + u"> task: \xfcparent")
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
        tracker.deserialize("str",
            u"task#toref: \xfcto reference\n"
            u"    task: \xfcdummy\n"
            u"        task: \xfcmove me\n"
            u"    task: \xfcparent\n"
            u"%s: <- \xfcto reference\n" % reftype
        )

        proxy = tracker.root.find_one(reftype + u"> task > \xfcmove me")
        parent = tracker.root.find_one(reftype + u"> task: \xfcparent")
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
        tracker.deserialize("str",
            u"task#toref: \xfcto reference\n"
            u"    task: \xfcto rename\n"
            u"%s: <-" % reftype
        )

        to_rename = tracker.root.find_one(reftype + u' > \xfcto rename')
        to_rename.text = u"\xfcrenamed"

        assert _dump(tracker.root.children) == [
            u"task: \xfcto reference",
            u"    task: \xfcrenamed",
            reftype + ": #toref",
            u"    proxy: task: \xfcrenamed"
        ]

    def test_export(self, tracker, reftype):
        tracker.deserialize("str",
            u"task: \xfcto reference\n"
            u"    task#aaaaa: \xfcparent\n"
            u"        task: \xfcchild 1\n"
            u"        task: \xfcchild 2\n"
            u"        task: \xfcchild 3\n"
            u"%s: <-" % reftype
        )

        from treeoflife.file_storage import serialize

        result = serialize(tracker.root.find_one(reftype + u" > \xfcparent"))
        assert result == [
            u"task#aaaaa: \xfcparent"
        ]

    def test_no_options(self, tracker, reftype):
        tracker.deserialize("str",
            u"task: \xfcto reference\n"
            u"    task: \xfctarget\n"
            u"%s: <-" % reftype
        )

        target = tracker.root.find_one(reftype + u"> \xfctarget")

        with pytest.raises(AttributeError) as excinfo:
            target.options

        assert "do not have" in excinfo.value.message


class TestRefnode(object):
    def test_creation(self, tracker, reftype):
        tracker.deserialize("str",
            u"task#abcde: \xfctarget 1\n"
            u"{}: <-".format(reftype)
        )

        ref = tracker.root.find_one(reftype)

        ref.createchild(u"task", u"\xfctest")

        assert _dump(tracker.root.find(u"*")) == [
            u"task: \xfctarget 1",
            u"    task: \xfctest",
            reftype + u": #abcde",
            U"    proxy: task: \xfctest"
        ]

    def test_unfinish(self, tracker, reftype):
        tracker.deserialize("str",
            u"task#abcde: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"days\n"
            u"    day: today\n"
            u"        @active\n"
            u"        {}: << >\n".format(reftype)
        )

        navigation.done(tracker.root)
        refnode = tracker.root.find_one(u"** > " + reftype)
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]
        navigation.finish(u"<", tracker.root)
        target = tracker.root.find_one(u"task: \xfctarget 1")
        if reftype == u"depends":
            assert target.finished
        else:
            assert not target.finished
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde"
        ]
        assert tracker.root.active_node.node_type == u"day"

        navigation.forceactivate(u">", tracker.root)
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not target.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]

    def test_unfinish_notinitialized(self, tracker, reftype):
        tracker.deserialize("str",
            u"task#abcde: \xfctarget 1\n"
            u"    task: \xfctarget 2\n"
            u"days\n"
            u"    day: today\n"
            u"        @active\n"
            u"        {}: << >\n"
            u"            @started\n"
            u"            @finished\n".format(reftype)
        )

        refnode = tracker.root.find_one(u"** > " + reftype)
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + u": " + refnode.text
        ]
        assert tracker.root.active_node.node_type == u"day"
        target = tracker.root.find_one(u"task: \xfctarget 1")
        if reftype == u"depends":
            assert target.finished
        else:
            assert not target.finished

        navigation.forceactivate(
            searching.Query(u">"), tracker.root)
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not refnode._px_target.finished
        assert _dump([refnode]) == [
            reftype + u": #abcde",
            u"    proxy: task: \xfctarget 2"
        ]

    def test_unfinish_targetfinished(self, tracker, reftype):
        tracker.deserialize("str",
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
        )

        refnode = tracker.root.find_one(u"** > " + reftype)
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + u": " + refnode.text
        ]
        assert tracker.root.active_node.node_type == u"day"
        target = tracker.root.find_one(u"task: \xfctarget 1")
        assert target.finished

        navigation.forceactivate(
            searching.Query(u">"), tracker.root)
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

        tracker.deserialize("str",
            u"task: \xfctarget\n"
            u"    task: \xfcchild\n"
        )

        tracker.root.addchild(ref)

        assert ref._px_target is tracker.root.find_one(u"task")

    def test_export(self, tracker, reftype):
        tree = (
            u"task#55555: \xfctarget\n"
            u"    task#44444: \xfcsomechild\n"
            u"        task#33333: \xfcsomechild\n"
            u"    comment#22222: \xfcderp\n"
            u"{}#11111: %s\n".format(reftype)
        )
        tracker.deserialize("str", tree % u"<- \xfctarget")

        assert tracker.serialize("str") == tree % u"#55555"

    def test_removechild(self, tracker, reftype):
        tracker.deserialize("str",
            u"task#abcde: \xfcreferenced\n"
            u"    task: \xfctoremove\n"
            u"{}: <-\n".format(reftype)
        )
        reference = tracker.root.find_one(reftype)

        toremove = reference.find_one(u"task")
        reference.removechild(toremove)
        assert _dump(tracker.root.children) == [
            u"task: \xfcreferenced",
            u"{}: #abcde".format(reftype)
        ]


def test_child_loop(tracker, reftype):
    tracker.deserialize("str",
        u"task: a\n"
        u"    task: b\n"
        u"        task: e\n"
        u"        task: f\n"
        u"        task: g\n"
        u"    task: c\n"
        u"    task: d\n"
        u"%s: <-" % reftype
    )

    a = tracker.root.find_one(reftype)
    b = a.find_one(u"b")
    c = a.find_one(u"c")
    d = a.find_one(u"d")
    e = a.find_one(u"b > e")
    f = a.find_one(u"b > f")
    g = a.find_one(u"b > g")

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
        tracker.deserialize("str",
            u"task: target\n"
            u"%s: <-" % reftype
        )
        creator = searching.Creator(reftype + u" > task: test")
        nodes = creator(tracker.root)
        assert len(nodes) == 1
        node = nodes[0]
        proxy = tracker.root.find_one(reftype + u"> test")
        assert node is proxy

    def test_mini_child_loop(self, tracker, reftype):
        tracker.deserialize("str",
            "task: target\n"
            "%s: <-" % reftype
        )
        creator = searching.Creator(reftype + u"> task: test")
        nodes = creator(tracker.root)
        assert len(nodes) == 1

        proxy_task = tracker.root.find_one(reftype + u"> test")
        target_task = tracker.root.find_one(u"target > test")
        reference = tracker.root.find_one(reftype)
        target = tracker.root.find_one(u"target")

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
    tracker.deserialize("str",
        u"task: target\n"
        u"days\n"
        u"    day: today\n"
        u"        @started\n"
        u"        %s: << > target\n"
        u"            @active\n" % reftype
    )

    navigation.createauto(u"task: test", tracker)

    active_node = tracker.root.active_node
    proxy = tracker.root.find_one(u"days > today > " + reftype + u" > test")
    target = tracker.root.find_one(u"target > test")
    assert active_node is proxy
    assert proxy is not target
    assert proxy._px_target is target
    assert proxy._px_root.get_proxy(target) is proxy

    navigation.createfinish(u"-> task: test 2", tracker)

    target = tracker.root.find_one(u"target")
    assert target.started
    first_child = target.children.next_neighbor
    assert first_child.started
    assert first_child.finished
    second_child = first_child.next_neighbor
    assert second_child.started
    assert not second_child.finished

    proxy_active = tracker.root.find_one(u"days > day > "
            + reftype + u"> test 2")
    assert proxy_active is tracker.root.active_node


def test_another_interaction(tracker, reftype):
    tracker.deserialize("str",
        u"task: target\n"
        u"days\n"
        u"    day: today\n"
        u"        @started\n"
        u"        %s: << > target\n"
        u"            @active\n" % reftype
    )

    navigation.createauto(u"task: test 1", tracker)
    navigation.createfinish(u"< > +task: test 2", tracker)

    target = tracker.root.find_one(u"target")

    assert target.started
    first_child = target.children.next_neighbor
    assert first_child.started
    assert first_child.finished
    second_child = first_child.next_neighbor
    assert second_child.started
    assert not second_child.finished

    proxy_active = tracker.root.find_one(u"days > day > "
            + reftype + u" > test 2")
    assert proxy_active is tracker.root.active_node


def test_str(tracker, reftype):
    tracker.deserialize("str",
        u"task#abcde: target\n"
        u"    comment: to test against\n"
        u"%s: <-\n" % reftype
    )

    proxy = tracker.root.find_one(reftype + u" > comment")
    proxy_target = proxy._px_target
    assert str(proxy) == str(proxy_target)

    ref = tracker.root.find_one(reftype)
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
    tracker.deserialize("str",
        u"task#abcde: target\n"
        u"    task: something\n"
        u"        %s: < target\n" % reftype
    )

    assert _dump(tracker.root.children) == [
        u"task: target",
        u"    task: something",
        u"        %s: #abcde" % reftype,
        u"            proxy: task: something",
        u"                proxy: %s: <recursing>" % reftype,
    ]


def test_ui_dictify(tracker, reftype):
    tracker.deserialize("str",
        (u"task#targt: target\n"
        u"    task#abcde: child\n"
        u"%s#rfrnc: <-\n"
        u"%s#rfrn2: <-\n"
        ) % (reftype, reftype)
    )

    child = tracker.root.find_one(reftype + u" > child")
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
    monkeypatch.setattr(references.Reference, "find_one", None)
    tracker.deserialize("str",
        u"reference: <-\n"
        u"    @started\n"
        u"    @finished"
    )


def test_reference_finished(tracker, reftype):
    tracker.deserialize("str",
        u"task: finished node\n"
        u"    @started: June 1, 2013 1:00 am\n"
        u"    @finished: June 1, 2013 2:00 am\n"
        u"%s: <-" % reftype
    )

    reference = tracker.root.find_one(reftype)
    assert not reference.started
    assert reference.finished


def test_depends_finished_node(tracker, reftype):
    tracker.deserialize("str",
        u"task: finished node\n"
        u"    @started: June 1, 2013 1:00 am\n"
        u"    @finished: June 1, 2013 2:00 am\n"
        u"%s: <-\n"
        u"    @finished: June 2, 2013 2:00 am" % reftype
    )

    reference = tracker.root.find_one(reftype)
    target = tracker.root.find_one(u"task")
    assert not reference.started
    assert reference.finished
    assert reference.finished > target.finished


def test_reference_started(tracker, reftype):
    tracker.deserialize("str",
        u"task: finished node\n"
        u"%s: <-\n"
        u"    @started: June 1, 2013 1:00 am\n" % reftype
    )

    reference = tracker.root.find_one(reftype)
    target = reference._px_target
    assert reference.started == target.started
    assert not reference._px_didstart


def test_depends_propogate_finished(tracker):
    tracker.deserialize("str",
        u"task: finished node\n"
        u"depends: <-\n"
        u"    @started: June 1, 2013 1:00 am\n"
        u"    @finished: June 2, 2013 1:00 am\n"
    )

    dep = tracker.root.find_one(u"depends")
    target = tracker.root.find_one(u"task")
    assert dep._px_target is None
    assert dep.finished == target.finished
    assert not dep._px_didfinish


def test_reference_category(tracker, reftype):
    tracker.deserialize("str",
        u"category: stuff\n"
        u"    task: stuff\n"
        u"days\n"
        u"    day: today\n"
        u"        %s: << > category" % reftype
    )

    ref = tracker.root.find_one(u'** > ' + reftype)
    tracker.root.activate(ref)

    assert ref.started


def test_reference_category_existingtime(tracker, reftype):
    tracker.deserialize("str",
        u"category: stuff\n"
        u"    task: stuff\n"
        u"days\n"
        u"    day: today\n"
        u"        %s: << > category\n"
        u"            @started: December 19, 1994 11:55 PM" % reftype
    )

    ref = tracker.root.find_one(u'** > ' + reftype)

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

    tracker.deserialize("str",
        u"nontask: something\n"
        u"    task: something else\n"
        u"        task: something else 3\n"
        u"    task: something else 2\n"
        u"days\n"
        u"    day: today\n"
        u"        %s: << >\n"
        u"            @started\n" % reftype
    )

    ref = tracker.root.find_one(u"days > day > " + reftype)

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

    tracker.deserialize("str",
        u"nontask: something\n"
        u"    task: something else\n"
        u"        task: something else 3\n"
        u"    task: something else 2\n"
        u"days\n"
        u"    day: today\n"
        u"        depends: << >\n"
        u"            @started\n"
        u"            @finished\n"
    )

    ref = tracker.root.find_one(u"days > day > depends")

    assert called[0]
    assert ref.finished
    assert not hasattr(ref._px_target, "finished")


# search contexts or search quoting are required to make references useful
# test finish with behavior being called
# test target nodes with no finished or started slots
