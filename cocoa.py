import json
import sys
import os
import subprocess
import tempfile

from twisted.internet.protocol import Factory, ProcessProtocol
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import reactor
from twisted.python import log

from todo_tracker.tracker import Tracker
from todo_tracker.activity import CommandInterface, command, generate_listing
from todo_tracker import autosaving

@command
def error(event):
    raise Exception("test")

@command
def restart(event):
    reactor.stop()

@command
def vimpdb(event):
    import pdb; pdb.set_trace()
    event.ui.vim(event.source, True)

@command
def save(event):
    autosaving.full_save(event.tracker)

class VimRunProtocol(ProcessProtocol):
    def __init__(self, callback, master, originator, extra):
        self.callback = callback
        self.master = master
        self.originator = originator
        self.extra = extra

    def outConnectionLost(self):
        if self.extra:
            import pdb; pdb.set_trace()
        self.master._vim_running = False
        self.callback()
        for listener in self.master.listeners:
            listener.update()
        self.originator.sendmessage({"display": True})

class RemoteInterface(CommandInterface):
    max_format_depth = 3
    def __init__(self, tracker):
        super(RemoteInterface, self).__init__(tracker)
        self.listeners = []
        self._vim_running = False
    
    def command(self, source, line):
        if self._vim_running:
            self._show_iterm()
            return
        super(RemoteInterface, self).command(source, line)

    def _run_vim(self, source, filename, callback, extra):
        if extra:
            import pdb; pdb.set_trace()
        print __file__
        dirname = os.path.dirname(__file__)
        path = os.path.join(dirname, "startvim.sh")
        print dirname, path
        self._vim_running = True
        for listener in self.listeners:
            listener.sendmessage({"display": False})
            self._show_iterm()
        protocol = VimRunProtocol(callback, self, source, extra)
        reactor.spawnProcess(protocol, "/bin/bash", args=["/bin/bash", path, filename], env=os.environ)

    def _show_iterm(self):
        tmpfd0, tmp = tempfile.mkstemp()
        writer = open(tmp, "w")
        writer.write(
            'tell application "iTerm"\n'
            '    activate\n'
            'end tell\n'
        )
        message = subprocess.Popen(["osascript", tmp])
        message.wait()
        os.unlink(tmp)

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
            "suggestions": [self.status, ""],
            "messages": self.commandline.messages()
        })
        autosaving.auto_save(self.commandline.tracker)

    @property
    def status(self):
        if self.error:
            return self.error
        if self.commandline._vim_running:
            return "vim running"
        return ""

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
                log.msg("unrecognized message: %s = %s" % (key, value))
                continue
            handler(value)

    def message_input(self, text_input):
        pass # don't care about input right now

    def message_command(self, command):
        try:
            self.commandline.tracker.editor_callback = lambda: self.commandline.vim(self)
            self.commandline.command(self, command)
        except Exception as e:
            log.err()
            self.error = repr(e)
        else:
            self.update()
        finally:
            self.commandline.tracker.editor_callback = None

    def message_display(self, is_displayed):
        pass

class JSONFactory(Factory):
    def __init__(self, interface):
        self.interface = interface 

    def buildProtocol(self, addr):
        return JSONProtocol(self.interface)

def main():
    log.startLogging(sys.stdout, setStdout=False)
    log.startLogging(open("cocoa.log", "a"))
    tracker = Tracker()
    
    autosaving.load(tracker)
    interface = RemoteInterface(tracker)

    reactor.listenTCP(18081, JSONFactory(interface))
    try:
        reactor.run()
    finally:
        autosaving.full_save(tracker)

if __name__ == "__main__":
    main()
