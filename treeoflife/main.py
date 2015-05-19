from __future__ import unicode_literals, print_function

import sys
import os
import argparse
import shlex
import logging
import socket
import json

from twisted.internet.protocol import Factory
from twisted.internet.endpoints import (connectProtocol, SSL4ClientEndpoint,
        SSL4ServerEndpoint)
from twisted.internet import ssl
from twisted.internet.task import LoopingCall
from twisted.internet.error import CannotListenError
from twisted.internet.utils import getProcessValue
import twisted.python.log
import twisted.web.static
import twisted.web.server
from txws import WebSocketFactory
import py

from treeoflife.userinterface import SavingInterface, command
from treeoflife.util import Profile, setter
from treeoflife.protocols import UIProtocol, SyncProtocol, DiscoveryProtocol
from treeoflife import syncdata
from treeoflife import searching
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

        self.best_genome = None
        self.best_fitness = None

        if self.save_dir is not None:
            self.population_file = os.path.join(self.save_dir, "population")

            name = config.sync_name
            self.syncdata = syncdata.SyncData(
                    os.path.join(self.save_dir, "sync"),
                    "default_group",  # TODO: actual groups
                    name,
                    population_file=self.population_file,
                    replace_data=self.sync_replace_data,
                    on_synced=self.sync_notify)
        else:
            self.syncdata = None

    def load(self):
        SavingInterface.load(self)
        if self.save_dir is not None:
            self.load_genome()

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

    def optimize_and_commit(self):
        dumped = self.serialize()
        # TODO: detect changes to tree internally, skip this if not dirty
        # TODO: skip optimize if hash is equal

        self._save_and_optimize(dumped)

        # these force a sync commit any time the genome changes
        dumped["best_genome"] = json.dumps(self.best_genome)
        dumped["best_fitness"] = json.dumps(self.best_fitness)
        self.sync_commit(dumped)

    def _save_and_optimize(self, dumped):
        if self.save_dir is None:
            return

        optimize_dir = "/tmp/optimize_dir/"  # FIXME
        try:
            # TODO: makedirs()?
            os.mkdir(optimize_dir)
        except OSError as e:
            # TODO: only respond to some errors?
            pass
        self._save_files(optimize_dir, dumped)
        self._optimize(optimize_dir)

    def _optimize(self, optimize_dir):
        # TODO: actually call the optimizer via twisted
        #       (reactor.callProcess or something, google knows)
        optimizer_binary = self.run_config.optimizer_binary

        deferred = getProcessValue(str(optimizer_binary),
                [os.path.join(optimize_dir, "life"),
                self.population_file])

        deferred.addCallback(lambda x: self.load_genome)

    def load_genome(self, run_optimizer_if_missing=False):
        if self.save_dir is None:
            return

        try:
            reader = open(self.population_file, "r")
        except IOError as e:
            if e.errno == 2:
                if run_optimizer_if_missing:
                    self._optimize(self.save_dir)
                return False
            else:
                raise

        with reader:
            genome_separator = "genome_separator"
            genome = []
            best_fitness = None
            for line in reader:
                line = line.strip()
                if line.startswith("fitness"):
                    # parses "fitness 100.0"
                    _, _, f = line.partition(" ")
                    best_fitness = float(f)
                elif line == genome_separator:
                    # parses "genome_separator"
                    # only want the first genome
                    break
                else:
                    time, _, activity = line.partition(' ')
                    nodeid = None  # parses "2010-10-10T11:11:11 nothing"
                    if activity != "nothing":
                        # parses "2010-10-10T11:11:11 workon ab13d"
                        # parses "2010-10-10T11:11:11 finish ab13d"
                        activity, _, nodeid = activity.partition(' ')
                    timeformat = "%Y-%m-%dT%H:%M:%S"
                    time = datetime.datetime.strptime(time, timeformat)
                    genome.append((time, activity, nodeid))
            self.best_genome = genome
            self.best_fitness = best_fitness

    def sync_replace_data(self, files):
        files.pop("best_genome")
        files.pop("best_fitness")

        self.deserialize(files)
        self.update_all()

        if self.save_dir is None:
            return
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        self._save_files(self.save_dir, files)

    def sync_commit(self, dumped):
        if self.syncdata is None:
            return
        self.syncdata.update(dumped)

    def sync_notify(self):
        for listener in self.listeners:
            listener.update_last_synced()


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


class TLSKeys(object):
    def __init__(self, reactor, basedir):
        self.reactor = reactor
        clientdata = (
            basedir.join("client.crt.pem").read_binary()
            + basedir.join("client.key.pem").read_binary()
        )
        serverdata = (
            basedir.join("server.crt.pem").read_binary()
            + basedir.join("server.key.pem").read_binary()
        )
        cadata = basedir.join("ca.crt.pem").read()
        self.server_cert = ssl.PrivateCertificate.loadPEM(serverdata)
        self.client_cert = ssl.PrivateCertificate.loadPEM(clientdata)
        self.ca_cert = ssl.Certificate.loadPEM(cadata)
        self.client_options = self.client_cert.options(self.ca_cert)
        self.server_options = self.server_cert.options(self.ca_cert)

    def server(self, port):
        return SSL4ServerEndpoint(self.reactor, port,
                self.server_options)

    def client(self, host, port):
        return SSL4ClientEndpoint(self.reactor, host, port,
                self.client_options)


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
argparser.add_argument("--android", default=None, type=py.path.local,
        dest="android_root")
argparser.add_argument("--sync-name", default=None, dest="sync_name")
argparser.add_argument("--sync-announce-interval", default=2, type=float,
        dest="sync_interval")
argparser.add_argument("--sync-tls-dir", type=py.path.local,
        default=None, dest="tls_directory")
argparser.add_argument("optimizer_binary", type=py.path.local)


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
    return
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


def main(restarter, args):
    from twisted.internet import reactor

    projectroot = os.path.os.path.abspath(os.path.join(
        os.path.dirname(__file__), b".."
    ))
    os.chdir(projectroot)
    config = argparser.parse_args(args)
    use_git = True
    if config.android_root:
        # pretend we're on pypy - this will make things slow
        # TODO: this is an awful hack, and will slow things down
        # a ton. need to migrate slow stuff into ceylon-controlled
        # stuff (the GA thing).
        searching.MAX_TICKS = 100000
        config.tls_directory = config.android_root.join("app/tls")
        config.sync_name = config.android_root.join("app/name")\
                            .read_binary().decode("utf-8")
        config.ignore_tests = True
        config.path = str(config.android_root.join("data"))
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

    tls = TLSKeys(reactor, config.tls_directory)

    sync_port = config.port + 6
    tls.server(sync_port).listen(SyncServer(ui.syncdata, reactor=reactor))

    def connect_sync(host):
        protocol = SyncProtocol(ui.syncdata, reactor=reactor)
        endpoint = tls.client(host, sync_port)
        logger.info("Connecting sync to %s", host)
        connectProtocol(endpoint, protocol)

    def connect_discovery():
        logger.info("Starting udp broadcast announce")
        discovery_port = config.port + 7
        discovery = DiscoveryProtocol(ui.syncdata, discovery_port,
                connect_sync, connect_discovery, reactor,
                interval=config.sync_interval)
        try:
            reactor.listenUDP(discovery_port, discovery)
        except CannotListenError:
            logger.exception("Error connecting udp, retrying...")
            reactor.callLater(config.sync_interval, connect_discovery)
    connect_discovery()

    # serve ui directory
    ui_dir = os.path.join(projectroot, b"ui")
    resource = NoCacheFile(ui_dir)
    static = twisted.web.server.Site(resource)
    reactor.listenTCP(config.port + 1, static,
            interface=str(config.listen_iface))

    pinger = LoopingCall(ui.sync_notify)
    pinger.start(90)

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
