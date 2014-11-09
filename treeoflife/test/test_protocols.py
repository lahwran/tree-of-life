from __future__ import unicode_literals, print_function

import hashlib
import zlib
import treeoflife.protocols

disconnected = object()


class SyncProtocol(treeoflife.protocols.SyncProtocol):
    def connectionMade(self):
        treeoflife.protocols.SyncProtocol.connectionMade(self)
        print()

    def send_line(self, line):
        self.mqueue = getattr(self, "mqueue", [])
        assert disconnected not in self.mqueue
        self.mqueue.append(line)

    def disconnect(self):
        self.mqueue = getattr(self, "mqueue", [])
        self.mqueue.append(disconnected)
        self.connectionLost(None)


def check_disconnect(source, dest):
    if disconnected in dest.mqueue and disconnected not in source.mqueue:
        print(dest.datasource.name.upper(), "DISCONNECTED")
        print()

        source.mqueue = [disconnected]
        source.connectionLost(None)
        return True
    return False


def transmit(source, dest):
    for message in source.mqueue:
        if check_disconnect(source, dest):
            break
        assert type(message) == str
        assert '\n' not in message
        print("%s: %s" % (source.datasource.name, message))
        dest.line_received(message)
    else:
        source.mqueue = []
        check_disconnect(source, dest)


def makesyncdata(name, history):
    return treeoflife.protocols.SyncData(name,
            [usha256(x) for x in history], history[-1])


def usha256(data):
    assert type(data) == unicode
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:8]


# TODO: later reconvergence can have weird effects, where both sides know each
# other's different hashes but only one is ahead
# this is a required tradeoff of not using a merkle tree (merkle sequence?)

def test_sync_init():
    # easier to keep track of story characters mentally

    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 fourth data",
        "\u2028 fifth data"]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    assert shaakti.remote_hashes is None

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()
    assert obiwan.remote_hashes is None

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256("\u2028 third data")
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256("\u2028 fifth data")
    ]

    transmit(shaakti, obiwan)
    assert obiwan.remote_name == "shaakti"
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash {0}".format(usha256("\u2028 third data")),
        b"please_send {0}".format(usha256("\u2028 fifth data"))
    ]

    transmit(obiwan, shaakti)
    expected_data = zlib.compress("\u2028 fifth data".encode("utf-8"))
    assert shaakti.mqueue == [
        b'history_and_data {0} {1} {2} {data}'.format(
            usha256("\u2028 third data"),
            usha256("\u2028 fourth data"),
            usha256("\u2028 fifth data"),
            data=expected_data.encode("base64").replace(b'\n', b'')
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == []

    assert obiwan_data == makesyncdata("expected",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 fourth data",
        "\u2028 fifth data"]
    )
    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 5
    assert obiwan_data.data == "\u2028 fifth data".encode("utf-8")
    assert obiwan.remote_hashes == shaakti.remote_hashes

    assert obiwan.remote_hashes is not obiwan_data.hash_history
    assert shaakti.remote_hashes is not shaakti_data.hash_history


def test_sync_init_uptodate():
    # easier to keep track of story characters mentally

    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    assert shaakti.remote_hashes is None

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()
    assert obiwan.remote_hashes is None

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256("\u2028 third data")
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256("\u2028 third data")
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash {0}".format(usha256("\u2028 third data")),
    ]

    transmit(obiwan, shaakti)
    assert shaakti.mqueue == []

    assert obiwan_data == makesyncdata("expected",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 3
    assert obiwan_data.data == "\u2028 third data".encode("utf-8")
    assert obiwan.remote_hashes == shaakti.remote_hashes

    assert obiwan.remote_hashes is not obiwan_data.hash_history
    assert shaakti.remote_hashes is not shaakti_data.hash_history


def test_sync_please_send_race():
    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 fourth data"]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b'please_send {}'.format(usha256('\u2028 fourth data'))
    ]

    # this is the opening where something can go wrong, so let's make it!

    shaakti_data.update("\u2028 fifth data")

    transmit(obiwan, shaakti)
    assert shaakti.mqueue[-1] is disconnected


def test_init_diverged():
    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two"]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two"]
    )
    obiwan = SyncProtocol(obiwan_data)

    shaakti.connectionMade()
    obiwan.connectionMade()

    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256("\u2028 other diverged two")
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256("\u2028 diverged two")
    ]

    transmit(obiwan, shaakti)
    assert shaakti.mqueue[2:] == [
        b"please_send {0}".format(usha256("\u2028 other diverged two"))
    ]
    assert shaakti.remote_hashes is None

    transmit(shaakti, obiwan)
    expected_data = zlib.compress("\u2028 other diverged two".encode("utf-8"))
    assert obiwan.mqueue == [
        b"please_send {0}".format(usha256("\u2028 diverged two")),
        b'history_and_data {history} {data}'.format(
            history=" ".join(obiwan_data.hash_history),
            data=expected_data.encode("base64").replace(b'\n', b'')
        )
    ]
    assert obiwan.remote_hashes is None
    assert obiwan.diverged

    transmit(obiwan, shaakti)
    assert shaakti.remote_hashes == obiwan_data.hash_history
    assert shaakti.diverged
    assert shaakti_data.diverges["obiwan"] == {
        "data": "\u2028 other diverged two".encode("utf-8"),
        "history": obiwan_data.hash_history
    }
    assert shaakti_data.data == "\u2028 diverged two".encode("utf-8")

    expected_data = zlib.compress("\u2028 diverged two".encode("utf-8"))
    assert shaakti.mqueue == [
        b'history_and_data {history} {data}'.format(
            history=" ".join(shaakti_data.hash_history),
            data=expected_data.encode("base64").replace(b'\n', b'')
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan_data.diverges["shaakti"] == {
        "data": "\u2028 diverged two".encode("utf-8"),
        "history": shaakti_data.hash_history,
    }

    assert obiwan.remote_hashes == shaakti_data.hash_history
    assert obiwan_data.data == "\u2028 other diverged two".encode("utf-8")


def test_connected_update():
    init_data = ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    shaakti_data = makesyncdata("shaakti", list(init_data))
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = makesyncdata("obiwan", list(init_data))
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    transmit(shaakti, obiwan)
    transmit(obiwan, shaakti)

    assert shaakti.mqueue == []

    # ... some time later ...

    shaakti_data.update("\u2028 fourth data")
    expected_data = zlib\
            .compress("\u2028 fourth data".encode("utf-8"))\
            .encode("base64").replace(b'\n', b'')
    assert shaakti.mqueue == [
        b"new_data {parenthash} {compressed_data}".format(
            parenthash=usha256("\u2028 third data"),
            compressed_data=expected_data,
        )
    ]
    transmit(shaakti, obiwan)
    assert obiwan.mqueue == []

    assert obiwan_data == makesyncdata("expected",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 fourth data"]
    )
    assert obiwan_data == shaakti_data


def test_connected_already_diverged_update():
    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two"]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two"]
    )
    obiwan = SyncProtocol(obiwan_data)
    shaakti.connectionMade()
    obiwan.connectionMade()
    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)

    assert obiwan.mqueue == []

    # some time later...

    obiwan_data.update("\u2028 other diverged three")

    expected_data = zlib\
            .compress("\u2028 other diverged three".encode("utf-8"))\
            .encode("base64").replace(b'\n', b'')
    assert obiwan.mqueue == [
        b"new_data {parenthash} {compressed_data}".format(
            parenthash=usha256("\u2028 other diverged two"),
            compressed_data=expected_data,
        )
    ]

    transmit(obiwan, shaakti)

    assert shaakti.mqueue == []
    assert shaakti_data.diverges["obiwan"] == {
        "data": "\u2028 other diverged three".encode("utf-8"),
        "history": obiwan_data.hash_history
    }
    assert shaakti.remote_hashes == obiwan_data.hash_history


def test_diverge_since_connect():
    # diverge since connect SHOULD BE IMPOSSIBLE.
    # this test is to make sure we kinda sorta recover anyway.

    init_data = ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    shaakti_data = makesyncdata("shaakti", list(init_data))
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = makesyncdata("obiwan", list(init_data))
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    transmit(shaakti, obiwan)
    transmit(obiwan, shaakti)

    assert shaakti.mqueue == []

    # ...at some point something goes silently wrong...
    obiwan_data.hash_history.append(usha256("uhoh"))
    obiwan_data.data = b"uhoh"

    # ... some time later ...

    shaakti_data.update("\u2028 fourth data")
    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [disconnected]


def test_diverge_resolve():
    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two"]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two"]
    )
    obiwan = SyncProtocol(obiwan_data)
    shaakti.connectionMade()
    obiwan.connectionMade()
    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)

    assert obiwan.mqueue == []

    # some time later...

    shaakti_data.update("\u2028 resolve divergence",
            resolve_diverge="obiwan")

    expected_data = zlib\
            .compress("\u2028 resolve divergence".encode("utf-8"))\
            .encode("base64").replace(b'\n', b'')
    assert shaakti.mqueue == [
        b"new_data {parenthash} {remoteparent} {compressed_data}".format(
            parenthash=usha256("\u2028 diverged two"),
            remoteparent=usha256("\u2028 other diverged two"),
            compressed_data=expected_data,
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == []

    assert obiwan_data == makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two",
        "\u2028 diverged one",
        "\u2028 diverged two",
        "\u2028 resolve divergence"]
    )

    assert shaakti_data == makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two",
        "\u2028 other diverged one",
        "\u2028 other diverged two",
        "\u2028 resolve divergence"]
    )


def test_disconnected_diverge_resolve():
    shaakti_data = makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two"]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two"]
    )
    obiwan = SyncProtocol(obiwan_data)
    shaakti.connectionMade()
    obiwan.connectionMade()
    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    shaakti.disconnect()
    transmit(obiwan, shaakti)
    assert shaakti.mqueue == [disconnected]
    assert obiwan.mqueue == [disconnected]
    assert not shaakti_data.connections
    assert not obiwan_data.connections

    # some time later...
    shaakti_data.update("\u2028 resolve divergence",
            resolve_diverge="obiwan")

    # ... then reestablish the connection ...
    obiwan = SyncProtocol(obiwan_data)
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    obiwan.connectionMade()

    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256("\u2028 other diverged two")
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256("\u2028 resolve divergence")
    ]

    transmit(shaakti, obiwan)

    assert obiwan.mqueue[-1:] == [
        b"please_send {0}".format(usha256("\u2028 resolve divergence"))
    ]
    transmit(obiwan, shaakti)

    expected_data = zlib\
            .compress("\u2028 resolve divergence".encode("utf-8"))\
            .encode("base64").replace(b'\n', b'')
    assert shaakti.mqueue == [
        b"history_and_data {history} {compressed_data}".format(
            history=b" ".join([
                usha256("\u2028 other diverged two"),
                usha256("\u2028 resolve divergence"),
            ]),
            compressed_data=expected_data,
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == []

    # NOTE HOW DIVERGED ONE AND DIVERGED TWO ARE MISSING! this is a compromise
    # by design, not a mistake. Feel free to extend the protocol to fix this,
    # but we're already into such a rare case that not being able to propogate
    # [the fast forward resolution to a diverge] seems like a pretty low
    # priority. it should be resolved fine by a fully connected network graph.

    # There may be some issues with offline fastforward of merges creating an
    # apparent secondary diverge between non-authoritative nodes:
    # 1. shaakti resolves a diverge
    # 2. obiwan finds out, attempts to pass along to yoda
    # 3. but ahsoka and obiwan think they've diverged
    # 4. shaakti updates ahsoka
    # 5. ahsoka and obiwan have diverged data stored for each other despite now
    #     being up to date.
    # but that seems like a pretty minor issue.

    # TODO: shouldn't be too horribly hard to fix, but blaaaaahhh. possible
    # fixes: order history when resolving diverge differently (invert common
    # parent slicing? add local to remote, instead of remote to local?), or
    # remember that we were diverged with a remote and do the diverge resolve
    # on-receipt append operation.

    assert obiwan_data == makesyncdata("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two",
        "\u2028 resolve divergence"]
    )

    assert shaakti_data == makesyncdata("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two",
        "\u2028 other diverged one",
        "\u2028 other diverged two",
        "\u2028 resolve divergence"]
    )


# TODO: test three-node diverge scenario where [ab, c] diverges, c finds out
# that both b and a are diverged from itself, it tracks both their diverges
# (separately? not? whatever), and then c resolves the diverge relative to a
# while also connected to b.
