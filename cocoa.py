import json
import sys

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import reactor
from twisted.python import log

from todo_tracker.tracker import Tracker
from todo_tracker.activity import CommandInterface, command, generate_listing

@command
def error(event):
    raise Exception("test")

@command
def restart(event):
    reactor.stop()

class RemoteInterface(CommandInterface):
    max_format_depth = 3
    def __init__(self, tracker):
        super(RemoteInterface, self).__init__(tracker)
        self.listeners = []

    def term_subprocess(self, args, callback):
        # open new iterm
        pass

    def errormessage(self, source, message):
        source.error = message
        log.msg("errormessage from %r: %r" % (source, message))

    def messages(self):
        return [str(child) for child in self.tracker.todo.children]

    def displaychain(self):
        result = super(RemoteInterface, self).displaychain()
        realresult = []
        for x in result:
            realresult.append(x)
            if x.node_type == "days":
                break
        return realresult
    
class JSONProtocol(LineOnlyReceiver):
    delimiter = "\n"

    def __init__(self, commandline):
        self.commandline = commandline
        self._error = ""
        self._errorclear = None

    def connectionMade(self):
        self.update()
        self.commandline.listeners.append(self)

    def connectionLost(self, reason):
        self.commandline.listeners.remove(self)

    def sendmessage(self, message):
        self.sendLine(json.dumps(message))

    def update(self):
        self.sendmessage({
            "prompt": [str(node) for node in self.commandline.displaychain()[::-1]],
            "context": self.commandline.tree_context(),
            "suggestions": [self.error, ""],
            "messages": self.commandline.messages()
        })

    @property
    def error(self):
        return self._error

    @error.setter
    def error(self, new_error):
        self._error = new_error
        if self._errorclear is not None and self._errorclear.active():
            self._errorclear.cancel()
        self._errorclear = reactor.callLater(5.0, self._deerror)
        self.update()

    def _deerror(self):
        self._error = ""
        self.update()
        if self._errorclear is not None:
            if self._errorclear.active():
                self._errorclear.cancel()
            self._errorclear = None

    def lineReceived(self, line):
        try:
            document = json.loads(line)
        except ValueError:
            log.err()
            return

        for key, value in document.items():
            try:
                handler = getattr(self, "message_%s" % key)
            except AttributeError:
                log.msg("unrecognized message: %s")
                continue
            handler(value)

    def message_input(self, text_input):
        pass # don't care about input right now

    def message_command(self, command):
        try:
            self.commandline.command(self, command)
        except Exception as e:
            log.err()
            self.error = repr(e)
        else:
            self.update()

class JSONFactory(Factory):
    def __init__(self, interface):
        self.interface = interface 

    def buildProtocol(self, addr):
        return JSONProtocol(self.interface)

def main(filename):
    log.startLogging(sys.stdout)
    tracker = Tracker()
    try:
        reader = open(filename, "r")
    except IOError:
        pass
    else:
        tracker.load(reader)
    interface = RemoteInterface(tracker)

    reactor.listenTCP(18081, JSONFactory(interface))
    reactor.run()

if __name__ == "__main__":
    name = "activities"
    if len(sys.argv) > 1:
        name = sys.argv[1]
    main(name)
