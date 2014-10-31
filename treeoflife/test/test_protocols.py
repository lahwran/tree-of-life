from __future__ import unicode_literals, print_function

import hashlib
import zlib
import treeoflife.protocols

disconnected = object()

class SyncProtocol(treeoflife.protocols.SyncProtocol):
    def send_line(self, line):
        self.mqueue = getattr(self, "mqueue", [])
        assert disconnected not in self.mqueue
        self.mqueue.append(line)

    def disconnect(self):
        self.mqueue = getattr(self, "mqueue", [])
        self.mqueue.append(disconnected)


def check_disconnect(source, dest):
    if disconnected in dest.mqueue:
        source.mqueue = [disconnected]
        return True
    return False

def transmit(source, dest):
    print()
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
    print()


def usha256(data):
    assert type(data) == unicode
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class DataSource(object):
    def __init__(self, name, data_history):
        # doesn't keep any but the latest data

        self.name = name
        self.hash_history = [usha256(x) for x in data_history]
        self.data = data_history[-1]

    def update(self, newdata):
        self.data = newdata
        self.hash_history.append(usha256(newdata))

    def __eq__(self, other):
        return (other.hash_history == self.hash_history
                and self.data == other.data)


# TODO: later reconvergence can have weird effects, where both sides know each
# other's different hashes but only one is ahead
# this is a required tradeoff of not using a merkle tree (merkle sequence?)

def test_sync_init():
    # easier to keep track of story characters mentally

    shaakti_data = DataSource("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 fourth data",
        "\u2028 fifth data",]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    assert shaakti.remote_hashes is None

    obiwan_data = DataSource("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()
    assert obiwan.remote_hashes is None

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [b"currenthash %s" % usha256("\u2028 third data")]
    assert shaakti.mqueue == [b"currenthash %s" % usha256("\u2028 fifth data")]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"currenthash {0}".format(usha256("\u2028 third data")),
        b"please_send {0}".format(usha256("\u2028 fifth data"))
    ]

    transmit(obiwan, shaakti)
    expected_data = zlib.compress("\u2028 fifth data".encode("utf-8"))
    assert shaakti.mqueue == [
        b'history_and_data {0} {1} {2} {data}'.format(
            usha256("\u2028 third data"), usha256("\u2028 fourth data"), usha256("\u2028 fifth data"),
            data=expected_data.encode("base64").replace(b'\n', b'')
        )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == []

    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 5
    assert obiwan_data.data == "\u2028 fifth data"
    assert obiwan.remote_hashes == shaakti.remote_hashes

    assert obiwan.remote_hashes is not obiwan_data.hash_history
    assert shaakti.remote_hashes is not shaakti_data.hash_history


def test_sync_init_uptodate():
    # easier to keep track of story characters mentally

    shaakti_data = DataSource("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()
    assert shaakti.remote_hashes is None

    obiwan_data = DataSource("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()
    assert obiwan.remote_hashes is None

    # TODO: this leaves possibility of ordering bugs
    assert obiwan.mqueue == [b"currenthash %s" % usha256("\u2028 third data")]
    assert shaakti.mqueue == [b"currenthash %s" % usha256("\u2028 third data")]

    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [
        b"currenthash {0}".format(usha256("\u2028 third data")),
    ]

    transmit(obiwan, shaakti)
    assert shaakti.mqueue == []

    assert obiwan_data == shaakti_data
    assert len(obiwan_data.hash_history) == 3
    assert obiwan_data.data == "\u2028 third data"
    assert obiwan.remote_hashes == shaakti.remote_hashes

    assert obiwan.remote_hashes is not obiwan_data.hash_history
    assert shaakti.remote_hashes is not shaakti_data.hash_history


def test_sync_please_send_race():
    shaakti_data = DataSource("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 fourth data"]
    )
    shaakti = SyncProtocol(shaakti_data)
    shaakti.connectionMade()

    obiwan_data = DataSource("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data"]
    )
    obiwan = SyncProtocol(obiwan_data)
    obiwan.connectionMade()

    transmit(obiwan, shaakti)
    transmit(shaakti, obiwan)
    assert obiwan.mqueue == [b'please_send {}'.format(usha256('\u2028 fourth data'))]

    # this is the opening where something can go wrong, so let's make it!

    shaakti_data.update("\u2028 fifth data")

    transmit(obiwan, shaakti)
    assert shaakti.mqueue[-1] is disconnected


def test_init_diverged():
    shaakti_data = DataSource("shaakti",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 diverged one",
        "\u2028 diverged two"]
    )
    shaakti = SyncProtocol(shaakti_data)

    
    obiwan_data = DataSource("obiwan",
        ["\u2028 first data",
        "\u2028 second data",
        "\u2028 third data",
        "\u2028 other diverged one",
        "\u2028 other diverged two"]
    )
    obiwan = SyncProtocol(obiwan_data)
    

    shaakti.connectionMade()
    obiwan.connectionMade()

    assert obiwan.mqueue == [b"currenthash %s" % usha256("\u2028 other diverged two")]
    assert shaakti.mqueue == [b"currenthash %s" % usha256("\u2028 diverged two")]

    transmit(obiwan, shaakti)
    assert shaakti.mqueue[1:] == [
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
    assert obiwan.init_diverged

    transmit(obiwan, shaakti)
    assert shaakti.remote_hashes == obiwan_data.hash_history
    assert shaakti.init_diverged
    assert shaakti.diverged_data == "\u2028 other diverged two"
    assert shaakti_data.data == "\u2028 diverged two"

    expected_data = zlib.compress("\u2028 diverged two".encode("utf-8"))
    assert shaakti.mqueue == [
        b'history_and_data {history} {data}'.format(
            history=" ".join(shaakti_data.hash_history),
            data=expected_data.encode("base64").replace(b'\n', b'')
       )
    ]

    transmit(shaakti, obiwan)
    assert obiwan.diverged_data == "\u2028 diverged two"
    assert obiwan.remote_hashes == shaakti_data.hash_history
    assert obiwan_data.data == "\u2028 other diverged two"
