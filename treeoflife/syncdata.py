import zlib
import hashlib


def sha256(data):
    assert type(data) == str
    return hashlib.sha256(data).hexdigest()


class SyncData(object):
    def __init__(self, name, hash_history, data):
        # doesn't keep any but the latest data

        self.diverges = {}
        self.name = name
        assert type(data) == unicode
        self.data = data.encode('utf-8')
        self.hash_history = hash_history
        self.connections = {}

    def update(self, newdata, resolve_diverge=None):
        # TODO: call this from user updates
        assert type(newdata) == unicode
        self.data = newdata.encode("utf-8")

        parents = [self.hash_history[-1]]

        if resolve_diverge:
            remote = self.diverges[resolve_diverge]
            hashes = slice_common_parent(
                    self.hash_history,
                    remote["history"])
            if hashes:
                parents.append(hashes[-1])
                self.hash_history.extend(hashes)

        self.hash_history.append(
            sha256(self.data)
        )
        for connection in self.connections.values():
            # TODO: this compresses and base64-encodes once per connection.
            # is it better to compress and b64-encode on user change?
            # TODO: don't send if we think it's up to date
            connection.data_changed(parents)

    def record_diverge(self, connection, data):
        self.diverges[connection.remote_name] = {
            "data": data,
            "history": connection.remote_hashes
        }

    def not_diverged(self, connection):
        connection.diverged = False

        stuff = self.diverges.get(connection.remote_name)
        if not stuff:
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
