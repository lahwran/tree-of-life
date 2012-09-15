import os
import tempfile as _tempfile

def tempfile():
    fd, tmp = _tempfile.mkstemp()
    os.close(fd)
    return tmp
