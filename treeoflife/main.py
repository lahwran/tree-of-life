from __future__ import unicode_literals, print_function

import json
import sys
import os
import argparse
import uuid
import shlex
import logging
from datetime import datetime
from collections import defaultdict

from twisted.internet.protocol import Factory, ProcessProtocol
from twisted.protocols.basic import LineOnlyReceiver
import twisted.python.log
import twisted.web.static
import twisted.web.server
from txws import WebSocketFactory

from treeoflife.userinterface import (SavingInterface, command,
    generate_listing)
from treeoflife.util import Profile, setter
import treeoflife.editor_launch

logger = logging.getLogger(__name__)


@command()
def error():
    raise Exception("test")


@command()
def restart(text, ui):
    if text:
        logger.debug("restart request: %r - %s", text, text)
        args = shlex.split(str(text))
        logger.debug("restart request args: %r", args)
    else:
        args = None
    ui.restarter.restart(args)


@command()
def stop(ui):
    ui.restarter.stop()


@command()
def save(ui):
    ui.full_save()


@command()
def quit_popup(source):
    source.sendmessage({"should_quit": True})


@command()
def update(ui):
    ui.update_all()


class RemoteInterface(SavingInterface):
    max_format_depth = 3

    def __init__(self, config, restarter, *args, **keywords):
        super(RemoteInterface, self).__init__(*args, **keywords)
        self.listeners = []
        self.run_config = config
        self.restarter = restarter
        self.edit_session = None

    def deserialize(self, *a, **kw):
        SavingInterface.deserialize(self, *a, **kw)
        for listener in self.listeners:
            listener.update()

    def hide_all_clients(self):
        for listener in self.listeners:
            listener.sendmessage({"display": False})

    def update_all(self):
        for listener in self.listeners:
            listener.update()

    @setter
    def edit_session(self, session):
        self._realedit_session = session
        for listener in self.listeners:
            listener.update_editor_running()

    def show_client(self, client):
        client.sendmessage({"display": True})

    def command(self, source, line):
        if self.edit_session:
            self.edit_session.editor.command_attempted()
            return
        super(RemoteInterface, self).command(source, line)

    def _editor_finished(self, identifier):
        if identifier != self.edit_session.editor.identifier:
            logger.error("editor id mismatches, doing nothing: %r",
                            identifier)
            return
        logger.info("finishing edit instance: %r", identifier)
        with Profile("editor finished"):
            self.edit_session.editor.done()

    def _embedded_editor_finished(self, identifier, contents):
        if identifier != self.edit_session.editor.identifier:
            logger.error("editor id mismatches, doing nothing: %r",
                            identifier)
            return
        logger.info("finishing embedded edit instance: %r", identifier)
        with Profile("embedded edit finished"):
            self.edit_session.editor.done(contents)

    def errormessage(self, source, message):
        source.error(message)
        logger.error("errormessage from %r: %r", source, message)

    def displaychain(self):
        result = super(RemoteInterface, self).displaychain()
        realresult = []
        for x in result:
            realresult.append(x)
            if x.node_type == "days":
                break
        return realresult


class JSONProtocol(LineOnlyReceiver):
    delimiter = b"\n"

    def __init__(self, commandline, reactor):
        self.commandline = commandline
        self._is_transient_connection = False
        self.command_history = [""]
        self.command_index = 0
        self.update_timeout = None
        self.reactor = reactor

    def connectionLost(self, reason):
        if not self._is_transient_connection:
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
        self.update_timeout = self.reactor.callLater(600, self.update)
        self.update_editor_running()

        try:
            reversed_displaychain = self.commandline.displaychain()[::-1]
            root = self.commandline.root
            pool = root.ui_graph()
            active_ref = getattr(root.active_node, "_px_root", None)
            todo = getattr(root, "todo", None)
            if todo is not None:
                todo_id = todo.id
            else:
                todo_id = None
            pool["ids"] = {
                "root": root.id,
                "days": "00001",
                "active": root.active_node.active_id,
                "active_ref": active_ref.id if active_ref else None,
                "todo_bucket": todo_id
            }
            self.sendmessage({
                "promptnodes": [node.id for node in reversed_displaychain],
                "pool": pool,
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
            "editor_running": self.commandline.edit_session is not None
        })

    def error(self, new_error):
        self.sendmessage({"error": new_error})

    def lineReceived(self, line):
        try:
            document = json.loads(line)
        except ValueError:
            logger.exception("Error loading line: %r", line)
            self.error("exception, see console")
            return

        for key, value in document.items():
            try:
                handler = getattr(self, "message_%s" % key)
            except AttributeError:
                logger.info("unrecognized message: %s = %s", key, value)
                self.error("exception, see console")
                continue
            try:
                handler(value)
            except Exception as e:
                logger.exception("error running handler")
                self.capture_error(e, "UNEXPECTED, SEE CONSOLE")

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
            self.capture_error(e)
        else:
            self.commandline.update_all()

    def capture_error(self, e, message=None):
        stred = str(e)
        name = type(e).__name__
        if name != "Exception" and stred:
            formatted = "%s: %s" % (name, stred)
        elif stred:
            formatted = stred
        else:
            formatted = name
        if message is not None:
            formatted = message + " " + formatted
        self.error(formatted)

    def message_display(self, is_displayed):
        pass

    def message_file_editor_finished(self, identifier):
        self._is_transient_connection = True
        self.reactor.callLater(0, self.commandline._editor_finished,
                identifier=identifier)
        self.transport.loseConnection()

    def message_embedded_editor_finished(self, info):
        self.commandline._embedded_editor_finished(
                info["identifier"], info["data"])

    def message_ui_connected(self, ignoreme):
        self._is_transient_connection = False
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
    def __init__(self, interface, reactor):
        self.interface = interface
        self.reactor = reactor

    def buildProtocol(self, addr):
        return JSONProtocol(self.interface, self.reactor)


argparser = argparse.ArgumentParser(description="run server")
argparser.add_argument("--dev", nargs="?", dest="dev", default="false",
        const="true", type=lambda s: s.lower() == "true")
argparser.add_argument("-d", "--dir-path", default="~/.treeoflife",
        dest="path")
argparser.add_argument("-p", "--port", default=18081, dest="port", type=int)
argparser.add_argument("-l", "--log", default="server", dest="logname")
argparser.add_argument("--log-ext", default="log", dest="log_ext")
argparser.add_argument("-m", "--main-file", default="life", dest="mainfile")
argparser.add_argument("--interface", default="127.0.0.1", dest="listen_iface")
argparser.add_argument("--ignore-tests", action="store_true",
        dest="ignore_tests")
argparser.add_argument("-e", "--editor", default="embedded", dest="editor")


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

        request.setHeader(str("Cache-Control"),
                str("no-cache, no-store, must-revalidate"))
        request.setHeader(str("Pragma"), str("no-cache"))
        request.setHeader(str("Expires"), str("0"))

        if not self.exists():
            return self.ensure_no_cache(self.childNotFound.render(request))

        if self.isdir():
            return self.redirect(request)

        request.setHeader(str('accept-ranges'), str('bytes'))

        try:
            fileForReading = self.openForReading()
        except IOError, e:
            import errno
            if e[0] == errno.EACCES:
                return resource.ForbiddenResource().render(request)
            else:
                raise

        producer = self.makeProducer(request, fileForReading)

        if request.method == str('HEAD'):
            return str('')

        producer.start()
        # and make sure the connection doesn't get closed
        return server.NOT_DONE_YET
    render_HEAD = render_GET


def main(restarter, args):
    from twisted.internet import reactor

    projectroot = os.path.os.path.abspath(os.path.join(
        os.path.dirname(__file__), b".."
    ))
    os.chdir(projectroot)
    config = argparser.parse_args(args)

    if not config.ignore_tests:
        import pytest
        if pytest.main([]) != 0:
            return

    if config.dev:
        config.path += str("_dev")
        config.logname += str("_dev")
    config.logfile = str("%s.%s") % (config.logname, config.log_ext)

    logfile = init_log(config)
    restarter.to_flush.append(logfile)

    ui = RemoteInterface(config, restarter, config.path, config.mainfile,
            reactor=reactor)
    ui.load()
    ui.config.setdefault("max_width", 500)
    logger.info("ui config: %r", ui.config)

    factory = JSONFactory(ui, reactor=reactor)
    reactor.listenTCP(config.port, factory, interface=config.listen_iface)
    reactor.listenTCP(config.port + 2,
            WebSocketFactory(factory), interface=config.listen_iface)

    # serve ui directory
    ui_dir = os.path.join(projectroot, b"ui")
    resource = NoCacheFile(ui_dir)
    static = twisted.web.server.Site(resource)
    reactor.listenTCP(config.port + 1, static,
            interface=str(config.listen_iface))
    try:
        reactor.run()
    finally:
        ui.full_save()


def _main():
    print("(pre-logging init note) sys.argv:", sys.argv)
    restarter = Restarter()
    restarter.call(main, sys.argv[1:])

if __name__ == "__main__":
    _main()
