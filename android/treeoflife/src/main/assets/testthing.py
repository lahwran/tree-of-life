
import datetime
import time
import sys
import os
import signal
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class _Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream
        self._unbuffered = True

    def write(self, data):
        self.stream.write(data)
        if self._unbuffered:
            self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

sys.stdout = _Unbuffered(open("testlog.0", "a"))
sys.stderr = sys.stdout

default_int = signal.getsignal(signal.SIGINT)

def sighandler(name):
    def handle(signum, frame):
        print "got signal", signum, name, "at", datetime.datetime.now()
        return default_int()
    return handle

for sig in ["INT", "QUIT", "TERM", "HUP"]:
    val = getattr(signal, "SIG"+sig)
    signal.signal(val, sighandler(sig))

print "starting at", datetime.datetime.now()
try:
    while True:
        time.sleep(0.1)
        print "still alive at", datetime.datetime.now()
except:
    import traceback
    print "err at", datetime.datetime.now()
    traceback.print_exc()
print "exiting cleanly at", datetime.datetime.now()
