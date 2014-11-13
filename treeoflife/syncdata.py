import zlib
import shutil
import hashlib
import json
import py


def sha256(data):
    assert type(data) == str
    return hashlib.sha256(data).hexdigest()


class SyncData(object):
    def __init__(self, directory, name, init_stuff=None):
        # doesn't keep any but the latest data
        self.name = name

        self.connections = {}

        self.directory = py.path.local(directory)
        self.directory.ensure(dir=True)
        self.datafile = self.directory.join("last_data")
        self.hashfile = self.directory.join("hash_history")

        try:
            self.data = self.datafile.read_binary()
            self.hash_history = self.hashfile.read_binary().split()
        except py.error.ENOENT:
            self.data = ""
            self.hash_history = [sha256(self.data)]
            if init_stuff is not None:
                self.data = self.dump(init_stuff)
                self.hash_history.append(sha256(self.data))
            self.write()

    def write(self):
        self.datafile.write_binary(self.data)
        self.hashfile.write_binary("\n".join(self.hash_history))

    def resolve_diverge(self, remote_name):
        parents = [self.hash_history[-1]]

        remote = self.directory.join("diverge-" + remote_name)
        remote_history = remote.join("hash_history").read_binary().split()
        repaired_data = remote.join("merged").read_binary()

        hashes = slice_common_parent(
                self.hash_history,
                remote_history)
        if hashes:
            parents.append(hashes[-1])
            self.hash_history.extend(hashes)

        self.data = repaired_data

        self.hash_history.append(
            sha256(self.data)
        )
        self.write()
        self.broadcast_changed(parents)
        shutil.rmtree(str(remote))

    def update(self, newstuff):
        # TODO: call this from user updates
        self.data = self.dump(newstuff)

        parents = [self.hash_history[-1]]

        self.hash_history.append(
            sha256(self.data)
        )
        self.write()
        self.broadcast_changed(parents)

    def updated_by_connection(self):
        self.write()
        self.broadcast_changed([self.hash_history[-1]])

    def broadcast_changed(self, parents):
        for connection in self.connections.values():
            # TODO: this compresses and base64-encodes once per connection.
            # is it better to compress and b64-encode on user change?
            if self.hash_history[-1] == connection.remote_hashes[-1]:
                continue
            connection.data_changed(parents)

    def dump(self, stuff):
        data = json.dumps(stuff)
        assert type(data) == str
        return data

    def record_diverge(self, connection, data):
        diverge_dir = self.directory.join(
                "diverge-" + connection.remote_name)
        diverge_dir.ensure(dir=True)
        diverge_dir.join("data").write_binary(data)
        diverge_dir.join("hash_history")\
                .write_binary("\n".join(connection.remote_hashes))

    def not_diverged(self, connection):
        connection.diverged = False

        diverge_dir = self.directory.join(
                "diverge-" + connection.remote_name)
        if not diverge_dir.check(dir=True):
            return

        sliced = slice_common_parent(
                self.hash_history,
                connection.remote_hashes)
        self.hash_history.extend(sliced)

    # TODO: rebroadcast to other nodes

    def __eq__(self, other):
        return (other.hash_history == self.hash_history
                and self.data == other.data)


def _encode_data(utf8_bytes):
    assert type(utf8_bytes) == str
    return zlib.compress(utf8_bytes)\
            .encode("base64")\
            .replace(b'\n', b'')


def _decode_data(base64_bytes):
    b64 = base64_bytes.decode("base64")
    del base64_bytes

    uncompressed = zlib.decompress(b64)
    del b64
    return uncompressed


def _hash_age_dictionary(hash_history):
    return dict((value, index)
            for (index, value)
            in enumerate(hash_history))


def slice_common_parent(local_history, remote_history):
    # have to be able to deal with unaligned ordering
    # dict() will use the last value if there are multiple,
    # thereby giving us maximum index, which is exactly what we want
    theirs = _hash_age_dictionary(remote_history)
    ours = _hash_age_dictionary(local_history)
    overlap = theirs.viewkeys() & ours.viewkeys()
    maxval = max(theirs[key] for key in overlap)
    return remote_history[maxval + 1:]
