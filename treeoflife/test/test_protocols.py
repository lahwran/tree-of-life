from __future__ import unicode_literals, print_function

import hashlib
import zlib
import treeoflife.protocols

class SyncProtocol(treeoflife.protocols.SyncProtocol):
    def send_line(self, line):
        self.mqueue = getattr(self, "mqueue", [])
        self.mqueue.append(line)


def transmit(source, dest):
    for message in source.mqueue:
        assert type(message) == str
        dest.line_received(message)
    source.mqueue = []


def usha256(data):
    assert type(data) == unicode
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class DataSource(object):
    def __init__(self, name, data_history):
        # doesn't keep any but the latest data

        self.hash_history = [usha256(x) for x in data_history]
        self.data = data_history[-1]

    def __eq__(self, other):
        return (other.hash_history == self.hash_history
                and self.data == other.data)


# TODO: later reconvergence can have weird effects, where both sides know each
# other's different hashes but only one is ahead
# this is a required tradeoff of not using a merkle tree (merkle sequence?)

def test_sync_init():
    # easier to keep track of story characters mentally

    shaakti_data = DataSource("shaakti",
        ["\u2028first data",
        "\u2028second data",
        "\u2028third data",
        "\u2028fourth data",
        "\u2028fifth data",]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = DataSource("obiwan",
        ["\u2028first data",
        "\u2028second data",
        "\u2028third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [b"currenthash %s" % usha256("\u2028third data")]
    assert shaakti.mqueue == [b"currenthash %s" % usha256("\u2028fifth data")]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"currenthash {0}".format(usha256("\u2028third data")),
        b"please_send {0}".format(usha256("\u2028fifth data"))
    ]

    transmit(obiwan, shaakti)
    expected_data = zlib.compress("\u2028fifth data".encode("utf-8"))
    assert shaakti.mqueue == [
        b'history_and_data {0} {1} {2} {data}'.format(
            usha256("\u2028third data"), usha256("\u2028fourth data"), usha256("\u2028fifth data"),
            data=expected_data.encode("base64")
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == []

    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 5
    assert obiwan_data.data == "\u2028fifth data"


def test_sync_init_uptodate():
    # easier to keep track of story characters mentally

    shaakti_data = DataSource("shaakti",
        ["\u2028first data",
        "\u2028second data",
        "\u2028third data",]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = DataSource("obiwan",
        ["\u2028first data",
        "\u2028second data",
        "\u2028third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [b"currenthash %s" % usha256("\u2028third data")]
    assert shaakti.mqueue == [b"currenthash %s" % usha256("\u2028third data")]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"currenthash {0}".format(usha256("\u2028third data")),
    ]

    transmit(obiwan, shaakti)
    assert shaakti.mqueue == []

    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 3
    assert obiwan_data.data == "\u2028third data"
