from __future__ import unicode_literals, print_function

import sys
import os
import argparse
import shlex
import logging
import socket

from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
import twisted.python.log
import twisted.web.static
import twisted.web.server
from txws import WebSocketFactory

from treeoflife.userinterface import SavingInterface, command
from treeoflife.util import Profile, setter
from treeoflife.protocols import UIProtocol, SyncProtocol
from treeoflife import syncdata
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
    ui.save()


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

        if self.save_dir is not None:
            name = config.sync_name
            self.syncdata = syncdata.SyncData(
                    os.path.join(self.save_dir, "sync"),
                    name, replace_data=self.sync_replace_data)
        else:
            self.syncdata = None

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

    def parse_command(self, source, line):
        if self.edit_session:
            self.edit_session.editor.command_attempted()
            return
        return super(RemoteInterface, self).parse_command(source, line)

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

    def sync_replace_data(self, files):
        self.deserialize(files)
        self.update_all()

        if self.save_dir is None:
            return
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self._save_files(self.save_dir, files)

    def sync_commit(self):
        if self.syncdata is None:
            return
        dumped = self.serialize()
        self.syncdata.update(dumped)


class Server(Factory):
    def __init__(self, protocolclass, tracker, reactor):
        self.protocolclass = protocolclass
        self.tracker = tracker
        self.reactor = reactor

    def buildProtocol(self, addr):
        return self.protocolclass(self.tracker, self.reactor)


class SyncServer(Factory):
    def __init__(self, syncdata, reactor):
        self.syncdata = syncdata
        self.reactor = reactor

    def buildProtocol(self, addr):
        return SyncProtocol(self.syncdata, reactor=self.reactor)

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
argparser.add_argument("--android", default=None, dest="android_root")
argparser.add_argument("--sync-remote", default=(), action="append",
        dest="sync_remotes")
argparser.add_argument("--sync-name", default=None, dest="sync_name")


class Restarter(object):
    def __init__(self):
        self.should_restart = False
        self.orig_cwd = os.path.realpath(".")
        self.to_flush = [sys.stdout, sys.stderr]
        self.args = sys.argv

    def restart(self, args=None):
        from twisted.internet import reactor
        reactor.stop()
        if args is not None:
            self.args = [self.args[0]] + args
        self.should_restart = True

    def stop(self):
        from twisted.internet import reactor
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
        timeout=1
    )
    handler = SentryHandler(client)
    handler.setLevel(logging.WARNING)

    setup_logging(handler)


def init_log(config):
    directory = os.path.realpath(os.path.expanduser(config.path))
    rootlogger = logging.getLogger()

    formatter = logging.Formatter('[%(asctime)s %(levelname)8s] %(name)s: '
                                            '%(message)s')

    init_sentry()

    rootlogger.setLevel(logging.INFO)
    path = os.path.join(directory, config.logfile)
    logfile = open(path, "a")
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

        # no really that's supposed to be "restat"
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


def connect_sync(syncdata, reactor, remotes):
    for remote in remotes:
        protocol = SyncProtocol(syncdata, reactor=reactor)
        host, port = remote.split(":")
        endpoint = TCP4ClientEndpoint(reactor, host, int(port))
        logger.info("Connecting sync to %s", remote)
        connectProtocol(endpoint, protocol)


def main(restarter, args):
    from twisted.internet import reactor

    projectroot = os.path.os.path.abspath(os.path.join(
        os.path.dirname(__file__), b".."
    ))
    os.chdir(projectroot)
    config = argparser.parse_args(args)
    use_git = True
    if config.android_root:
        config.ignore_tests = True
        config.path = os.path.join(config.android_root, "data")
        use_git = False

    directory = os.path.realpath(os.path.expanduser(config.path))
    if not os.path.exists(directory):
        os.makedirs(directory)

    if not config.ignore_tests:
        import pytest
        if pytest.main(["-qq", "treeoflife"]) != 0:
            return

    if config.dev:
        config.path += str("_dev")
        config.logname += str("_dev")
    config.logfile = str("%s.%s") % (config.logname, config.log_ext)

    logfile = init_log(config)
    restarter.to_flush.append(logfile)

    import treeoflife.nodes.import_all

    ui = RemoteInterface(
            config, restarter,
            config.path, config.mainfile, use_git=use_git,
            reactor=reactor)
    ui.load()
    ui.config.setdefault("max_width", 500)
    logger.info("ui config: %r", ui.config)

    factory = Server(UIProtocol, ui, reactor=reactor)
    reactor.listenTCP(config.port, factory, interface=config.listen_iface)
    reactor.listenTCP(config.port + 2,
            WebSocketFactory(factory), interface=config.listen_iface)

    reactor.listenTCP(config.port + 6,
            SyncServer(ui.syncdata, reactor=reactor),
            interface=config.listen_iface)
    reactor.callLater(3, connect_sync,
            ui.syncdata, reactor, config.sync_remotes)

    # serve ui directory
    ui_dir = os.path.join(projectroot, b"ui")
    resource = NoCacheFile(ui_dir)
    static = twisted.web.server.Site(resource)
    reactor.listenTCP(config.port + 1, static,
            interface=str(config.listen_iface))
    try:
        reactor.run()
    finally:
        ui.save()


def _main():
    print("(pre-logging init note) sys.argv:", sys.argv)
    restarter = Restarter()
    restarter.call(main, sys.argv[1:])

if __name__ == "__main__":
    _main()
