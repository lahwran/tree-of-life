import json
import sys
import os
import subprocess
import argparse
import uuid
import shlex
import logging
from datetime import datetime
from collections import defaultdict

from twisted.internet.protocol import Factory, ProcessProtocol
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import reactor
import twisted.python.log
import twisted.web.static
import twisted.web.server
from txws import WebSocketFactory

from todo_tracker.userinterface import (SavingInterface, command,
    generate_listing)
from todo_tracker.util import tempfile, Profile

logger = logging.getLogger(__name__)


@command()
def error(event):
    raise Exception("test")


@command()
def restart(event):
    if event.text:
        logger.debug("restart request: %r - %s", event.text, event.text)
        args = shlex.split(str(event.text))
        logger.debug("restart request args: %r", args)
    else:
        args = None
    event.ui.restarter.restart(args)


@command()
def stop(event):
    event.ui.restarter.stop()


@command()
def vimpdb(event):
    import pdb
    pdb.set_trace()
    event.ui.vim(event.source, debug=True)


@command()
def save(event):
    event.ui.full_save()


@command()
def quit_popup(event):
    event.source.sendmessage({"should_quit": True})


@command()
def update(event):
    event.source.update()


def osascript(code):
    temp_code = tempfile()
    with open(temp_code, "w") as code_writer:
        code_writer.write(code)
    subprocess.call(["osascript", temp_code])
    os.unlink(temp_code)


class VimRunner(object):
    """
    Tell iterm2 to open a new window, then run a command that runs vim
    after vim finishes, the command will send a json message to the main port
    """

    outer_command = 'exec bash -c "%s"\n'

    # > /dev/null because the initialization message is uninteresting
    base_inner_command = "vim %s;echo '%s' | base64 --decode | nc 127.0.0.1 %d"

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
        b64_data = json_data.encode("base64")
        b64_data = b64_data.replace(" ", "").replace("\n", "")
        inner_command = self.base_inner_command % (
                " ".join(args), b64_data, port)
        inner_command = inner_command.replace("\\'", "'\"'\"'")
        self.command = self.outer_command % inner_command
        logger.info("Starting vim with id %r: %s", self.id, self.command)

        self.tempfile = tempfile()
        with open(self.tempfile, "w") as temp_writer:
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
        self.run_config = config
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

        runner = VimRunner(originator, self, self.run_config.port, callback,
                filenames)
        runner.run()

        self._vim_instances[runner.id] = runner
        for listener in self.listeners:
            listener.update_editor_running()

    def _vim_finished(self, identifier):
        if identifier not in self._vim_instances:
            logger.error("can't finish nonexistant vim invocation: %r",
                            identifier)
            return
        logger.info("finishing vim invocation: %r", identifier)
        instance = self._vim_instances[identifier]
        del self._vim_instances[identifier]
        instance.done()

    def _show_iterm(self):
        osascript(
            'tell application "iTerm"\n'
            '    activate\n'
            'end tell\n'
        )

    def errormessage(self, source, message):
        source.error(message)
        logger.error("errormessage from %r: %r", source, message)

    def messages(self):
        if self.root.todo:
            messages = [str(child) for child in self.root.todo.children]
        else:
            messages = []

        if self.root.fitness_log:
            today = datetime.now().date()
            things = defaultdict(int)
            format_strings = {}
            for node in reversed(self.root.fitness_log.children):
                if node.time.date() != today:
                    break
                if getattr(node, "value_name", False):
                    things[node.node_type] += getattr(node, node.value_name)
                    format_strings[node.node_type] = node.value_format
            if messages:
                messages.append("")
            for thing, value in sorted(things.items()):
                message = "%s today: " + format_strings[thing]
                messages.append(message % (thing, value))

        return messages

    def top_messages(self):
        result = []
        queue = self.root.find_one("category: queue")
        if queue is not None:
            generate_listing(None, queue, result)
        return result[:30]

    def tree_context(self):
        result = []
        result.extend(self.top_messages())
        if result:
            result.append("")
        result.extend(super(RemoteInterface, self).tree_context())
        return result

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
        self._is_vim_connection = False
        self.command_history = [""]
        self.command_index = 0
        self.update_timeout = None

    def connectionLost(self, reason):
        if not self._is_vim_connection:
            try:
                self.commandline.listeners.remove(self)
            except ValueError:
                logger.exception("Error removing listener from listeners")
            logger.info("connection lost: %r", reason)

    def sendmessage(self, message):
        self.sendLine(json.dumps(message))

    def update(self):
        if self.update_timeout is not None and self.update_timeout.active():
            self.update_timeout.cancel()
        self.update_timeout = reactor.callLater(60, self.update)
        self.update_editor_running()

        try:
            reversed_displaychain = self.commandline.displaychain()[::-1]
            self.sendmessage({
                "prompt": [str(node) for node in reversed_displaychain],
                "graph": {
                    "pool": self.commandline.root.ui_graph(),
                    "ids": {
                        "root": self.commandline.root.id,
                        "days": "00001",
                        "todo_bucket": self.commandline.root.todo.id
                    },
                }
            })
            self.commandline.auto_save()
        except Exception:
            logger.exception("Error updating")
            try:
                self.sendmessage({
                    "prompt": ["** see console **", " ** update error **"],
                })
            except Exception:
                logger.exception("Error sending update notification")
                self.error("exception")

    def update_editor_running(self):
        self.sendmessage({
            "editor_running": len(self.commandline._vim_instances)
        })

    def error(self, new_error):
        self.sendmessage({"error": new_error})

    def lineReceived(self, line):
        try:
            document = json.loads(line)
        except ValueError:
            logger.exception("Error loading line")
            self.error("exception")
            return

        for key, value in document.items():
            try:
                handler = getattr(self, "message_%s" % key)
            except AttributeError:
                logger.info("unrecognized message: %s = %s", key, value)
                self.error("exception")
                continue
            try:
                handler(value)
            except Exception:
                logger.exception("error running handler")
                self.error("exception")

    def message_input(self, text_input):
        self.command_history[self.command_index] = text_input

    def message_navigate(self, direction):
        shift = -1 if direction == "up" else 1

        prev = self.command_index
        self.command_index += shift

        if self.command_index < 0:
            self.command_index = 0
        elif self.command_index >= len(self.command_history):
            self.command_index = len(self.command_history) - 1

        logger.info("navigate history: %s - %s", self.command_index,
                self.command_history[self.command_index])
        if prev == self.command_index:
            return

        self.sendmessage({"input": self.command_history[self.command_index]})

    def message_command(self, command):
        self.command_history[self.command_index] = command
        self.command_index = len(self.command_history)
        self.command_history.append("")
        try:
            self.commandline.command(self, command)
        except Exception as e:
            logger.exception("Error running command")
            stred = str(e)
            name = type(e).__name__
            if stred:
                formatted = "%s: %s" % (name, stred)
            else:
                formatted = name
            self.error(formatted)
        else:
            self.update()

    def message_display(self, is_displayed):
        pass

    def message_vim_finished(self, identifier):
        self._is_vim_connection = True
        with Profile("vim finished"):
            self.commandline._vim_finished(identifier)

    def message_ui_connected(self, ignoreme):
        self._is_vim_connection = False
        try:
            self.sendmessage({
                "max_width": self.commandline.config["max_width"]
            })
            self.sendmessage({
                "display": True
            })
            self.update()
            self.commandline.listeners.append(self)
        except Exception:
            logger.exception("Error sending info on connection")


class JSONFactory(Factory):
    def __init__(self, interface):
        self.interface = interface

    def buildProtocol(self, addr):
        return JSONProtocol(self.interface)


argparser = argparse.ArgumentParser(description="run server")
argparser.add_argument("--dev", nargs="?", dest="dev", default="false",
        const="true", type=lambda s: s.lower() == "true")
argparser.add_argument("-d", "--dir-path", default="~/.todo_tracker",
        dest="path")
argparser.add_argument("-p", "--port", default=18081, dest="port")
argparser.add_argument("-l", "--log", default="cocoa", dest="logname")
argparser.add_argument("--log-ext", default="log", dest="log_ext")
argparser.add_argument("-m", "--main-file", default="life", dest="mainfile")
argparser.add_argument("--interface", default="127.0.0.1", dest="listen_iface")
argparser.add_argument("--ignore-tests", action="store_true",
        dest="ignore_tests")


class Restarter(object):
    def __init__(self):
        self.should_restart = False
        self.orig_cwd = os.path.realpath(".")
        self.to_flush = [sys.stdout, sys.stderr]
        self.args = sys.argv

    def restart(self, args=None):
        reactor.stop()
        if args is not None:
            self.args = [self.args[0]] + args
        self.should_restart = True

    def stop(self):
        reactor.stop()
        self.should_restart = False

    def call(self, target, *args):
        target(self, *args)

        if self.should_restart:
            os.chdir(self.orig_cwd)
            logger.debug("restarting - args: %r", self.args)
            sys.__stdout__.write("** restarting **\n")
            for f in self.to_flush:
                f.flush()
            for f in self.to_flush:
                os.fsync(f.fileno())
            os.execv(sys.executable, [sys.executable] + self.args)


def init_sentry():
    try:
        sentryurl = open("sentryurl", "r").read().strip()
    except IOError:
        return

    from raven import Client
    from raven.handlers.logging import SentryHandler
    from raven.conf import setup_logging

    # Manually specify a client
    client = Client(
        dsn=sentryurl,
        list_max_length=256,
        string_max_length=2 ** 16,
        auto_log_stacks=True,
    )
    handler = SentryHandler(client)
    handler.setLevel(logging.WARNING)

    setup_logging(handler)


def init_log(config):
    rootlogger = logging.getLogger()

    formatter = logging.Formatter('[%(asctime)s %(levelname)8s] %(name)s: '
                                            '%(message)s')

    init_sentry()

    rootlogger.setLevel(logging.DEBUG)
    logfile = open(config.logfile, "a")
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(logfile)
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
        rootlogger.addHandler(handler)

    twisted_observer = twisted.python.log.PythonLoggingObserver()
    twisted_observer.start()

    logger.info("logfile: %r" % config.logfile)

    return logfile


class NoCacheFile(twisted.web.static.File):
    def render_GET(self, request):
        """
        Begin sending the contents of this L{File} (or a subset of the
        contents, based on the 'range' header) to the given request.
        """

        from twisted.web.static import getTypeAndEncoding, resource, server

        self.restat(False)

        if self.type is None:
            self.type, self.encoding = getTypeAndEncoding(self.basename(),
                                              self.contentTypes,
                                              self.contentEncodings,
                                              self.defaultType)

        request.setHeader("Cache-Control",
                "no-cache, no-store, must-revalidate")
        request.setHeader("Pragma", "no-cache")
        request.setHeader("Expires", "0")

        if not self.exists():
            return self.ensure_no_cache(self.childNotFound.render(request))

        if self.isdir():
            return self.redirect(request)

        request.setHeader('accept-ranges', 'bytes')

        try:
            fileForReading = self.openForReading()
        except IOError, e:
            import errno
            if e[0] == errno.EACCES:
                return resource.ForbiddenResource().render(request)
            else:
                raise

        producer = self.makeProducer(request, fileForReading)

        if request.method == 'HEAD':
            return ''

        producer.start()
        # and make sure the connection doesn't get closed
        return server.NOT_DONE_YET
    render_HEAD = render_GET


def main(restarter, args):
    os.chdir(os.path.abspath(os.path.dirname(__file__)))
    config = argparser.parse_args(args)

    if not config.ignore_tests:
        import pytest
        if pytest.main([]) != 0:
            return

    if config.dev:
        config.path += "_dev"
        config.logname += "_dev"
    config.logfile = "%s.%s" % (config.logname, config.log_ext)

    logfile = init_log(config)
    restarter.to_flush.append(logfile)

    ui = RemoteInterface(config, restarter, config.path, config.mainfile)
    ui.load()
    ui.config.setdefault("max_width", 500)
    logger.info("ui config: %r", ui.config)

    factory = JSONFactory(ui)
    reactor.listenTCP(config.port, factory, interface=config.listen_iface)
    reactor.listenTCP(config.port + 2,
            WebSocketFactory(factory), interface=config.listen_iface)

    # serve ui directory
    ui_dir = os.path.join(os.path.dirname(__file__), "ui")
    resource = NoCacheFile(ui_dir)
    static = twisted.web.server.Site(resource)
    reactor.listenTCP(config.port + 1, static, interface=config.listen_iface)
    try:
        reactor.run()
    finally:
        ui.full_save()


def _main():
    print "(pre-logging init note) sys.argv:", sys.argv
    restarter = Restarter()
    restarter.call(main, sys.argv[1:])

if __name__ == "__main__":
    _main()
