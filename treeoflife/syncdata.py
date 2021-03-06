from __future__ import unicode_literals, print_function

import zlib
import shutil
import hashlib
import json
import py
import datetime


def sha256(data):
    assert type(data) == str
    return hashlib.sha256(data).hexdigest()


class SyncData(object):
    def __init__(self, directory, group, name, init_stuff=None,
            replace_data=lambda x: None,
            on_synced=lambda: None,
            population_file=None):
        # doesn't keep any but the latest data
        self.name = name
        self.group = group

        self.connections = {}
        self.last_synced = {}

        self.replace_data_hook = replace_data
        self.on_synced_hook = on_synced

        self.directory = py.path.local(directory)
        self.directory.ensure(dir=True)
        self.datafile = self.directory.join(u"last_data")
        self.hashfile = self.directory.join(u"hash_history")
        self.last_synced_file = self.directory.join(u"last_synced")

        self.population_file = (py.path.local(population_file)
                                if population_file else None)

        try:
            self.last_synced = self.parse_last_synced(
                    self.last_synced_file.read_binary())
        except py.error.ENOENT:
            self.last_synced = {}

        try:
            self.data = self.datafile.read_binary()
            self.hash_history = self.hashfile.read_binary().split()
        except py.error.ENOENT:
            self.data = b""
            self.hash_history = [sha256(self.data)]
            self.last_synced = {}
            if init_stuff is not None:
                self.data = self.dump(init_stuff)
                self.hash_history.append(sha256(self.data))
            self.write()

    def parse_last_synced(self, data):
        pairs = (
            line.partition(b' ')
            for line in data.split(b"\n")
            if line.strip()
        )
        return dict(
            (name.decode("utf-8"), datetime.datetime.strptime(date,
                b'%Y-%m-%d %H:%M:%S'))
            for name, _, date in pairs
            if name and date
        )

    def dump_last_synced(self, last_synced):
        return b"\n".join(
            b"{} {}".format(
                name.encode("utf-8"),
                date.replace(microsecond=0).isoformat(b' '))
            for name, date in last_synced.iteritems()
        )

    def write(self):
        self.datafile.write_binary(self.data)
        self.hashfile.write_binary(b"\n".join(self.hash_history))
        self.last_synced_file.write_binary(
                self.dump_last_synced(self.last_synced))

    def resolve_diverge(self, remote_name):
        parents = [self.hash_history[-1]]

        remote = self.directory.join(u"diverge-" + remote_name)
        remote_history = remote.join(u"hash_history").read_binary().split()
        repaired_data = remote.join(u"merged").read_binary()

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
        self.data = self.dump(newstuff)
        h = sha256(self.data)

        if h == self.hash_history[-1]:
            return

        parents = [self.hash_history[-1]]

        self.hash_history.append(h)
        self.write()
        self.broadcast_changed(parents)

    def updated_by_connection(self):
        self.replace_data_hook(json.loads(self.data))
        self.write()
        self.broadcast_changed([self.hash_history[-1]])

    def broadcast_changed(self, parents):
        for connection in self.connections.values():
            # TODO: this compresses and base64-encodes once per connection.
            # is it better to compress and b64-encode on user change?
            if self.hash_history[-1] == connection.remote_hashes[-1]:
                continue
            connection.data_changed(parents)

    def update_synced_time(self, connection):
        self.last_synced[connection.remote_name] = datetime.datetime.now()
        self.on_synced_hook()

    def dump(self, stuff):
        data = json.dumps(stuff)
        assert type(data) == str
        return data

    @property
    def diverged_remotes(self):
        return [path.basename[len(u"diverge-"):]
            for path in self.directory.listdir()
            if path.basename.startswith(u"diverge-")]

    def record_diverge(self, connection, data):
        diverge_dir = self.directory.join(
                u"diverge-" + connection.remote_name)
        diverge_dir.ensure(dir=True)
        diverge_dir.join(u"data").write_binary(data)
        diverge_dir.join(u"hash_history")\
                .write_binary(b"\n".join(connection.remote_hashes))

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
        shutil.rmtree(str(diverge_dir))

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
