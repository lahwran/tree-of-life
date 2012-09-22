import json
import sys
import os
import subprocess
import tempfile
import argparse

from twisted.internet.protocol import Factory, ProcessProtocol
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import reactor
from twisted.python import log

from todo_tracker.tracker import Tracker
from todo_tracker.activity import SavingInterface, command

@command
def error(event):
    raise Exception("test")

@command
def restart(event):
    reactor.stop()

@command
def vimpdb(event):
    import pdb; pdb.set_trace()
    event.ui.vim(event.source, debug=True)

@command
def save(event):
    event.ui.full_save()

class VimRunProtocol(ProcessProtocol):
    def __init__(self, callback, master, originator, debug):
        self.callback = callback
        self.master = master
        self.originator = originator
        self.debug = debug

    def outReceived(self, data):
        sys.stdout.write(data)
        sys.stdout.flush()

    def errReceived(self, data):
        sys.stderr.write(data)
        sys.stderr.flush()

    def outConnectionLost(self):
        if self.debug:
            import pdb; pdb.set_trace()
        self.master._vim_running = False
        if self.callback():
            for listener in self.master.listeners:
                listener.update()
            self.originator.sendmessage({"display": True})

class RemoteInterface(SavingInterface):
    max_format_depth = 3
    def __init__(self, *args, **keywords):
        super(RemoteInterface, self).__init__(*args, **keywords)
        self.listeners = []
        self._vim_running = False
    
    def command(self, source, line):
        if self._vim_running:
            self._show_iterm()
            return
        super(RemoteInterface, self).command(source, line)

    def _run_vim(self, source, callback, *filenames, **kw):
        debug = kw.get("debug", False)
        if debug:
            import pdb; pdb.set_trace()
        print __file__
        dirname = os.path.dirname(__file__)
        path = os.path.join(dirname, "startvim.py")
        print dirname, path
        self._vim_running = True
        for listener in self.listeners:
            listener.sendmessage({"display": False})
            self._show_iterm()
        protocol = VimRunProtocol(callback, self, source, debug)
        reactor.spawnProcess(protocol, sys.executable, args=[sys.executable, path, "-o", "--"] + list(filenames), env=os.environ)

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
        if self.tracker.todo:
            return [str(child) for child in self.tracker.todo.children]
        else:
            return []

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
        self.commandline.auto_save()

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

argparser = argparse.ArgumentParser(description="run server")
argparser.add_argument("--dev", action="store_true", dest="dev")
argparser.add_argument("-d", "--dir-path", default="~/.todo_tracker", dest="path")
argparser.add_argument("-p", "--port", default=18081, dest="port")
argparser.add_argument("-l", "--log", default="cocoa.log", dest="logfile")
argparser.add_argument("-m", "--main-file", default="life", dest="mainfile")

def main(args):
    config = argparser.parse_args(args)
    if config.dev:
        config.path += "_dev"

    log.startLogging(sys.stdout, setStdout=False)
    log.startLogging(open(config.logfile, "a"), setStdout=False)
    tracker = Tracker()
    
    interface = RemoteInterface(tracker, config.path, config.mainfile)
    interface.load()

    reactor.listenTCP(config.port, JSONFactory(interface))
    try:
        reactor.run()
    finally:
        interface.full_save()

if __name__ == "__main__":
    main(sys.argv[1:])
