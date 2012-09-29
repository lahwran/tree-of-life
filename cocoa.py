import json
import sys
import os
import subprocess
import argparse
import uuid

from twisted.internet.protocol import Factory, ProcessProtocol
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import reactor
from twisted.python import log

from todo_tracker.tracker import Tracker
from todo_tracker.activity import SavingInterface, command
from todo_tracker.util import tempfile

@command
def error(event):
    raise Exception("test")

@command
def restart(event):
    event.ui.restarter.restart()

@command
def vimpdb(event):
    import pdb; pdb.set_trace()
    event.ui.vim(event.source, debug=True)

@command
def save(event):
    event.ui.full_save()

def osascript(code):
    temp_code = tempfile()
    code_writer = open(temp_code, "w")
    code_writer.write(code)
    code_writer.close()
    subprocess.call(["osascript", temp_code])
    os.unlink(temp_code)

class VimRunner(object):
    """
    Tell iterm2 to open a new window, then run a command that runs vim
    after vim finishes, the command will send a json message to the main port
    """

    outer_command = "exec bash -c '%s'\n"
    base_inner_command = "vim %s; echo '%s' | base64 -d | nc 127.0.0.1 %d" # > /dev/null because the initialization message is uninteresting
    applescript = """
        tell application "iTerm"
            activate
            set myterm to (make new terminal)
            tell myterm
                set number of columns to 140
                set number of rows to 150

                launch session "Default Session"

                tell the last session
                    write contents of file "{tempfile}"
                end tell
            end tell
        end tell
    """

    def __init__(self, originator, master, port, callback, filenames):
        self.master = master 
        self.callback = callback
        self.originator = originator

        self.id = str(uuid.uuid4())
        json_data = json.dumps({"vim_finished": self.id}) + "\n"

        args = self.wrap_args(["-o", "--"] + list(filenames))
        inner_command = self.base_inner_command % (" ".join(args), json_data.encode("base64").replace(" ","").replace("\n",""), port)
        inner_command = inner_command.replace("\\'", "'\"'\"'")
        self.command = self.outer_command % inner_command
        log.msg("Starting vim with id %r: %s" % (self.id, self.command))

        self.tempfile = tempfile()
        temp_writer = open(self.tempfile, "w")
        temp_writer.write(self.command)

    def run(self):
        osascript(self.applescript.format(tempfile=self.tempfile))

    def done(self):
        if self.callback():
            for listener in self.master.listeners:
                listener.update()
            self.originator.sendmessage({"display": True})

    def wrap_args(self, args):
        wrapped_args = []
        for arg in args:
            if "'" in arg:
                raise Exception("Can't put quotes in args! sorry")
            wrapped_args.append("'%s'" % arg)
        return wrapped_args

class RemoteInterface(SavingInterface):
    max_format_depth = 3
    def __init__(self, config, restarter, *args, **keywords):
        super(RemoteInterface, self).__init__(*args, **keywords)
        self.listeners = []
        self.config = config
        self.restarter = restarter
        self._vim_instances = {}
    
    def command(self, source, line):
        if self._vim_instances:
            self._show_iterm()
            return
        super(RemoteInterface, self).command(source, line)

    def _run_vim(self, originator, callback, *filenames):
        for listener in self.listeners:
            listener.sendmessage({"display": False})

        runner = VimRunner(originator, self, self.config.port, callback, filenames)
        runner.run()
        
        self._vim_instances[runner.id] = runner

    def _vim_finished(self, identifier):
        if identifier not in self._vim_instances:
            log.msg("can't finish nonexistant vim invocation: %r" % identifier)
            return
        log.msg("finishing vim invocation: %r" % identifier)
        self._vim_instances[identifier].done()
        del self._vim_instances[identifier]

    def _show_iterm(self):
        osascript(
            'tell application "iTerm"\n'
            '    activate\n'
            'end tell\n'
        )

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
        if self.commandline._vim_instances:
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

    def message_vim_finished(self, identifier):
        self.commandline._vim_finished(identifier)

class JSONFactory(Factory):
    def __init__(self, interface):
        self.interface = interface 

    def buildProtocol(self, addr):
        return JSONProtocol(self.interface)

argparser = argparse.ArgumentParser(description="run server")
argparser.add_argument("--dev", action="store_true", dest="dev")
argparser.add_argument("-d", "--dir-path", default="~/.todo_tracker", dest="path")
argparser.add_argument("-p", "--port", default=18081, dest="port")
argparser.add_argument("-l", "--log", default="cocoa", dest="logname")
argparser.add_argument("--log-ext", default="log", dest="log_ext")
argparser.add_argument("-m", "--main-file", default="life", dest="mainfile")
argparser.add_argument("--interface", default="127.0.0.1", dest="listen_iface")

class Restarter(object):
    def __init__(self):
        self.should_restart = False
        self.orig_cwd = os.path.realpath(".")
        self.to_flush = [sys.stdout, sys.stderr]

    def restart(self):
        reactor.stop()
        self.should_restart = True

    def stop(self):
        reactor.stop()
        self.should_restart = False

    def call(self, target, *args):
        target(self, *args)

        if self.should_restart:
            os.chdir(self.orig_cwd)
            sys.__stdout__.write("** restarting **\n")
            for f in self.to_flush:
                f.flush()
            for f in self.to_flush:
                os.fsync(f.fileno())
            os.execv(sys.executable, [sys.executable] + sys.argv)

def main(restarter, args):
    config = argparser.parse_args(args)
    if config.dev:
        config.path += "_dev"
        config.logname += "_dev"
    config.logfile = "%s.%s" % (config.logname, config.log_ext)

    log.startLogging(sys.stdout, setStdout=False)
    logfile = open(config.logfile, "a")
    restarter.to_flush.append(logfile)
    log.startLogging(logfile, setStdout=False)
    log.msg("logfile: %r" % config.logfile)
    tracker = Tracker()
    
    ui = RemoteInterface(config, restarter, tracker, config.path, config.mainfile)
    ui.load()

    reactor.listenTCP(config.port, JSONFactory(ui), interface=config.listen_iface)
    try:
        reactor.run()
    finally:
        ui.full_save()

if __name__ == "__main__":
    restarter = Restarter()
    restarter.call(main, sys.argv[1:])
