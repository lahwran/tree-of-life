from __future__ import unicode_literals, print_function

import hashlib
import zlib
import json

import pytest

import treeoflife.protocols
from treeoflife import syncdata

disconnected = object()


@pytest.fixture(autouse=True)
def shortened_sha(monkeypatch):
    oldsha256 = syncdata.sha256
    monkeypatch.setattr(syncdata, "sha256", lambda x: oldsha256(x)[:8])


class SyncProtocol(treeoflife.protocols.SyncProtocol):
    def connectionMade(self):
        treeoflife.protocols.SyncProtocol.connectionMade(self)
        print()

    def send_line(self, line):
        self.mqueue = getattr(self, "mqueue", [])
        assert disconnected not in self.mqueue
        self.mqueue.append(line)

    def disconnect(self, reason):
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


def stabilize(node1, node2, limit=10):
    count = 0
    while node1.mqueue or node2.mqueue:
        transmit(node1, node2)
        transmit(node2, node1)
        count += 1
        assert count < limit


def makesyncdata(tmpdir, name, history):
    directory = tmpdir.join(name)
    directory.ensure(dir=True)
    data = dump(history[-1])
    hashes = [usha256(x) for x in history]
    directory.join("hash_history").write_binary("\n".join(hashes))
    directory.join("last_data").write_binary(data)

    def on_synced():
        print("{} notify upate".format(name))
        sdata.sync_time_notifies += 1

    sdata = syncdata.SyncData(directory, "test_group", name,
        on_synced=on_synced)
    sdata.sync_time_notifies = 0
    return sdata


def usha256(stuff):
    return hashlib.sha256(dump(stuff)).hexdigest()[:8]


def dump(stuff):
    return json.dumps(stuff)


# TODO: later reconvergence can have weird effects, where both sides know each
# other's different hashes but only one is ahead
# this is a required tradeoff of not using a merkle tree (merkle sequence?)

def test_sync_init(tmpdir, setdt):
    # easier to keep track of story characters mentally
    setdt(2014, 12, 6, 0, 0)

    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 fourth data"},
        {"life": "\u2028 fifth data"}]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    assert shaakti.remote_hashes is None
    assert shaakti_data.sync_time_notifies == 0
    assert shaakti_data.last_synced == {}

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()
    assert obiwan_data.sync_time_notifies == 0
    assert obiwan_data.last_synced == {}
    assert obiwan.remote_hashes is None

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256({"life": "\u2028 third data"})
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256({"life": "\u2028 fifth data"})
    ]

    transmit(shaakti, obiwan)
    assert obiwan.remote_name == "shaakti"
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash {0}".format(usha256({"life": "\u2028 third data"})),
        b"please_send {0}".format(usha256({"life": "\u2028 fifth data"}))
    ]
    assert obiwan_data.sync_time_notifies == 1
    assert obiwan_data.last_synced == {}

    transmit(obiwan, shaakti)
    expected_data = zlib.compress(dump({"life": "\u2028 fifth data"}))
    assert shaakti.mqueue == [
        b'history_and_data {0} {1} {2} {data}'.format(
            usha256({"life": "\u2028 third data"}),
            usha256({"life": "\u2028 fourth data"}),
            usha256({"life": "\u2028 fifth data"}),
            data=expected_data.encode("base64").replace(b'\n', b'')
        )
    ]
    assert shaakti_data.sync_time_notifies == 1
    assert shaakti_data.last_synced == {}

    now = setdt(2014, 12, 6, 8, 5).now()
    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b'synced %s' % usha256({"life": "\u2028 fifth data"})
    ]
    assert obiwan_data.sync_time_notifies == 2
    assert obiwan_data.last_synced == {"shaakti": now}

    transmit(obiwan, shaakti)
    assert shaakti.mqueue == []
    assert shaakti_data.last_synced == {"obiwan": now}
    assert shaakti_data.sync_time_notifies == 2

    assert obiwan_data == makesyncdata(tmpdir, "expected",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 fourth data"},
        {"life": "\u2028 fifth data"}]
    )
    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 5
    assert obiwan_data.data == dump({"life": "\u2028 fifth data"})
    assert obiwan.remote_hashes == shaakti.remote_hashes

    assert obiwan.remote_hashes is not obiwan_data.hash_history
    assert shaakti.remote_hashes is not shaakti_data.hash_history


def test_sync_init_uptodate(tmpdir):
    # easier to keep track of story characters mentally

    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    assert shaakti.remote_hashes is None

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()
    assert obiwan.remote_hashes is None

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256({"life": "\u2028 third data"})
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256({"life": "\u2028 third data"})
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash {0}".format(usha256({"life": "\u2028 third data"})),
    ]

    transmit(obiwan, shaakti)
    assert obiwan_data.sync_time_notifies == 1
    assert shaakti_data.sync_time_notifies == 1
    assert obiwan_data.last_synced == {}
    assert shaakti_data.last_synced == {}

    assert obiwan_data == makesyncdata(tmpdir, "expected",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    )
    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 3
    assert obiwan_data.data == dump({"life": "\u2028 third data"})
    assert obiwan.remote_hashes == shaakti.remote_hashes

    assert obiwan.remote_hashes is not obiwan_data.hash_history
    assert shaakti.remote_hashes is not shaakti_data.hash_history


def test_sync_please_send_race(tmpdir):
    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 fourth data"}]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b'please_send {}'.format(usha256({"life": '\u2028 fourth data'}))
    ]

    # this is the opening where something can go wrong, so let's make it!

    shaakti_data.update({"life": "\u2028 fifth data"})

    transmit(obiwan, shaakti)
    assert shaakti.mqueue[-1] is disconnected


def test_init_diverged(tmpdir):
    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"}]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"}]
    )
    obiwan = SyncProtocol(obiwan_data)

    shaakti.connectionMade()
    obiwan.connectionMade()

    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256({"life": "\u2028 other diverged two"})
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256({"life": "\u2028 diverged two"})
    ]

    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 1
    assert shaakti.mqueue[2:] == [
        b"please_send {0}".format(usha256(
            {"life": "\u2028 other diverged two"}
        ))
    ]
    assert shaakti.remote_hashes is None

    transmit(shaakti, obiwan)
    expected_data = zlib.compress(dump({"life": "\u2028 other diverged two"}))
    assert obiwan.mqueue == [
        b"please_send {0}".format(usha256({"life": "\u2028 diverged two"})),
        b'history_and_data {history} {data}'.format(
            history=" ".join(obiwan_data.hash_history),
            data=expected_data.encode("base64").replace(b'\n', b'')
        )
    ]
    assert obiwan.remote_hashes is None
    assert obiwan.diverged

    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 2
    assert shaakti.remote_hashes == obiwan_data.hash_history
    assert shaakti.diverged
    diverge_dir = tmpdir.join("shaakti").join("diverge-obiwan")
    assert diverge_dir.check(dir=True)
    assert diverge_dir.join("data").read_binary() == dump(
        {"life": "\u2028 other diverged two"}
    )
    assert diverge_dir.join("hash_history")\
            .read_binary().split() == obiwan_data.hash_history
    assert shaakti_data.data == dump({"life": "\u2028 diverged two"})

    expected_data = zlib.compress(dump({"life": "\u2028 diverged two"}))
    assert shaakti.mqueue == [
        b'history_and_data {history} {data}'.format(
            history=" ".join(shaakti_data.hash_history),
            data=expected_data.encode("base64").replace(b'\n', b'')
        ),
        b'synced {0}'.format(usha256({"life": "\u2028 other diverged two"})),
    ]

    transmit(shaakti, obiwan)
    assert obiwan_data.sync_time_notifies == 3
    assert obiwan.mqueue == [
        b'synced {0}'.format(usha256({"life": "\u2028 diverged two"})),
    ]

    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 3
    assert shaakti.mqueue == []

    diverge_dir = tmpdir.join("obiwan").join("diverge-shaakti")
    assert diverge_dir.check(dir=True)
    assert diverge_dir.join("data").read_binary() == dump(
        {"life": "\u2028 diverged two"}
    )
    assert diverge_dir.join("hash_history")\
            .read_binary().split() == shaakti_data.hash_history

    assert obiwan.remote_hashes == shaakti_data.hash_history
    assert obiwan_data.data == dump({"life": "\u2028 other diverged two"})


def test_connected_update(tmpdir):
    init_data = [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    shaakti_data = makesyncdata(tmpdir, "shaakti", list(init_data))
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = makesyncdata(tmpdir, "obiwan", list(init_data))
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    stabilize(shaakti, obiwan)

    assert shaakti_data.sync_time_notifies == 1
    assert obiwan_data.sync_time_notifies == 1

    # ... some time later ...

    shaakti_data.update({"life": "\u2028 fourth data"})
    expected_data = zlib\
            .compress(dump({"life": "\u2028 fourth data"}))\
            .encode("base64").replace(b'\n', b'')
    assert shaakti.mqueue == [
        b"new_data {parenthash} {compressed_data}".format(
            parenthash=usha256({"life": "\u2028 third data"}),
            compressed_data=expected_data,
        )
    ]
    transmit(shaakti, obiwan)
    assert obiwan_data.sync_time_notifies == 2
    assert obiwan.mqueue == [
        b"synced {new_hash}".format(
            new_hash=usha256({"life": "\u2028 fourth data"}))
    ]

    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 2

    assert obiwan_data == makesyncdata(tmpdir, "expected",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 fourth data"}]
    )
    assert obiwan_data == shaakti_data


def test_connected_already_diverged_update(tmpdir):
    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"}]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"}]
    )
    obiwan = SyncProtocol(obiwan_data)
    shaakti.connectionMade()
    obiwan.connectionMade()
    stabilize(shaakti, obiwan)
    assert obiwan_data.sync_time_notifies == 3
    assert shaakti_data.sync_time_notifies == 3

    # some time later...

    obiwan_data.update({"life": "\u2028 other diverged three"})

    expected_data = zlib\
            .compress(dump({"life": "\u2028 other diverged three"}))\
            .encode("base64").replace(b'\n', b'')
    assert obiwan.mqueue == [
        b"new_data {parenthash} {compressed_data}".format(
            parenthash=usha256({"life": "\u2028 other diverged two"}),
            compressed_data=expected_data,
        )
    ]

    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 4

    assert shaakti.mqueue == [
        b"synced {}".format(usha256({"life": "\u2028 other diverged three"}))
    ]
    transmit(shaakti, obiwan)
    assert obiwan_data.sync_time_notifies == 4

    diverge_dir = tmpdir.join("shaakti").join("diverge-obiwan")
    assert diverge_dir.check(dir=True)
    assert diverge_dir.join("data").read_binary() == dump(
        {"life": "\u2028 other diverged three"}
    )
    assert diverge_dir.join("hash_history")\
            .read_binary().split() == obiwan_data.hash_history
    assert shaakti.remote_hashes == obiwan_data.hash_history


def test_diverge_since_connect(tmpdir):
    # diverge since connect SHOULD BE IMPOSSIBLE.
    # this test is to make sure we kinda sorta recover anyway.

    init_data = [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"}]
    shaakti_data = makesyncdata(tmpdir, "shaakti", list(init_data))
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = makesyncdata(tmpdir, "obiwan", list(init_data))
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    transmit(shaakti, obiwan)
    transmit(obiwan, shaakti)

    assert shaakti.mqueue == []

    # ...at some point something goes silently wrong...
    obiwan_data.hash_history.append(usha256("uhoh"))
    obiwan_data.data = dump("uhoh")

    # ... some time later ...

    shaakti_data.update({"life": "\u2028 fourth data"})
    transmit(shaakti, obiwan)
    assert obiwan.mqueue[-1] == disconnected


def test_diverge_resolve(tmpdir):
    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"}]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"}]
    )
    obiwan = SyncProtocol(obiwan_data)
    shaakti.connectionMade()
    obiwan.connectionMade()
    stabilize(obiwan, shaakti)

    diverge_dir = shaakti_data.directory.join("diverge-obiwan")
    assert diverge_dir.join("data").read_binary() == obiwan_data.data
    assert diverge_dir.join("hash_history").read_binary().split() == (
            obiwan_data.hash_history)

    # some time later...

    diverge_dir.join("merged").write_binary(
            dump({"life": "\u2028 resolve divergence"}))
    shaakti_data.resolve_diverge("obiwan")
    assert not diverge_dir.check()

    expected_data = zlib\
            .compress(dump({"life": "\u2028 resolve divergence"}))\
            .encode("base64").replace(b'\n', b'')
    assert shaakti.mqueue == [
        b"new_data {parenthash} {remoteparent} {compressed_data}".format(
            parenthash=usha256({"life": "\u2028 diverged two"}),
            remoteparent=usha256({"life": "\u2028 other diverged two"}),
            compressed_data=expected_data,
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"synced {}".format(usha256({"life": "\u2028 resolve divergence"}))
    ]

    assert obiwan_data == makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"},
        {"life": "\u2028 resolve divergence"}]
    )

    assert shaakti_data == makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"},
        {"life": "\u2028 resolve divergence"}]
    )


def test_disconnected_diverge_resolve(tmpdir):
    shaakti_data = makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"}]
    )
    shaakti = SyncProtocol(shaakti_data)

    obiwan_data = makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"}]
    )
    obiwan = SyncProtocol(obiwan_data)
    shaakti.connectionMade()
    obiwan.connectionMade()

    stabilize(shaakti, obiwan)

    shaakti.disconnect("test")
    transmit(obiwan, shaakti)
    assert shaakti.mqueue == [disconnected]
    assert obiwan.mqueue == [disconnected]
    assert not shaakti_data.connections
    assert not obiwan_data.connections
    obiwan_data.sync_time_notifies = 0
    shaakti_data.sync_time_notifies = 0

    # some time later...
    diverge_dir = shaakti_data.directory.join("diverge-obiwan")
    diverge_dir.join("merged").write_binary(
            dump({"life": "\u2028 resolve divergence"}))
    shaakti_data.resolve_diverge("obiwan")
    assert not diverge_dir.check()

    # ... then reestablish the connection ...
    obiwan = SyncProtocol(obiwan_data)
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    obiwan.connectionMade()

    assert obiwan.mqueue == [
        b"connect obiwan 1",
        b"currenthash %s" % usha256({"life": "\u2028 other diverged two"})
    ]
    assert shaakti.mqueue == [
        b"connect shaakti 1",
        b"currenthash %s" % usha256({"life": "\u2028 resolve divergence"})
    ]

    transmit(shaakti, obiwan)
    assert obiwan_data.sync_time_notifies == 1

    assert obiwan.mqueue[-1:] == [
        b"please_send {0}".format(usha256(
            {"life": "\u2028 resolve divergence"}
        ))
    ]
    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 1

    expected_data = zlib\
            .compress(dump({"life": "\u2028 resolve divergence"}))\
            .encode("base64").replace(b'\n', b'')
    assert shaakti.mqueue == [
        b"history_and_data {history} {compressed_data}".format(
            history=b" ".join([
                usha256({"life": "\u2028 other diverged two"}),
                usha256({"life": "\u2028 resolve divergence"}),
            ]),
            compressed_data=expected_data,
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan_data.sync_time_notifies == 2
    assert obiwan.mqueue == [
        b"synced {}".format(usha256({"life": "\u2028 resolve divergence"}))
    ]
    transmit(obiwan, shaakti)
    assert shaakti_data.sync_time_notifies == 2

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

    assert obiwan_data == makesyncdata(tmpdir, "obiwan",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"},
        {"life": "\u2028 resolve divergence"}]
    )

    assert shaakti_data == makesyncdata(tmpdir, "shaakti",
        [{"life": "\u2028 first data"},
        {"life": "\u2028 second data"},
        {"life": "\u2028 third data"},
        {"life": "\u2028 diverged one"},
        {"life": "\u2028 diverged two"},
        {"life": "\u2028 other diverged one"},
        {"life": "\u2028 other diverged two"},
        {"life": "\u2028 resolve divergence"}]
    )


# TODO: test three-node diverge scenario where [ab, c] diverges, c finds out
# that both b and a are diverged from itself, it tracks both their diverges
# (separately? not? whatever), and then c resolves the diverge relative to a
# while also connected to b.
