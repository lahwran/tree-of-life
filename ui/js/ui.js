var pevents = [];
function profile(message) {
    pevents.push({time: new Date().getTime(), label: message});
}
profile("init");
function pprofile() {
    var lasttime= 0;
    angular.forEach(pevents, function(pevent) {
        console.log("Delta:", pevent.time - lasttime, 
                    "Total:", pevent.time - pevents[0].time,
                    "Time:", pevent.time,
                    "Label:", pevent.label);
        lasttime = pevent.time;
    });
    pevents = [];
}
var _handlers = {};

function on_panel_shown()               {return (_handlers.panel_shown           || angular.noop)();}
function on_panel_hidden()              {return (_handlers.panel_hidden          || angular.noop)();}
function on_attempting_reconnect()      {return (_handlers.attempting_reconnect  || angular.noop)();}
function on_connected()                 {return (_handlers.connected             || angular.noop)();}
function on_disconnected()              {return (_handlers.disconnected          || angular.noop)();}
function on_message_received(message)   {return (_handlers.message_received      || angular.noop)(message);}
function on_status_changed(message)     {return (_handlers.status_changed        || angular.noop)(message);}
function on_calculate_width()           {return (_handlers.calculate_width       || angular.noop)();}
function on_calculate_height()          {return (_handlers.calculate_height      || angular.noop)();}


function ui_controller($scope, backend, handlers, $timeout) {
    $scope.root = {
        type: "root",
        text: null,
        children: []
    }
    $scope.show_editor = function() {
        backend.send({command: "vim"});
    }
    $scope.sidebar = {};
    $scope.sendcommand = function(command) {
        $scope._command = "";
        if (command === "reload") {
            location.reload(true);
            return;
        }
        backend.send({command: command});
    }
    $scope._quit = function() {
        backend.quit = true;
    }
    $scope.notifications = backend.notifications;
    $scope.removeNotification = function(index) {
        $scope.notifications.splice(index, 1);
    }
    $scope.test = "abcde";

    function whatareyoudoing() {
        $timeout(whatareyoudoing, 30 * 60 * 1000);
        $scope.backend.notifications.push("What are you currently doing?");
    }
    //whatareyoudoing();
}

var nodetypes = {
    days: {templateurl: "partials/node-days.html"},
    day: {
        controller: function($scope) {
            $scope.$watch("node.text", function(text) {
                var matches = text.match(/([^ ]{3})[^ ]* ([0-9]+), ([0-9]+) ?(.*)/);
                $scope.m = matches[1];
                $scope.d = matches[2];
                $scope.y = matches[3];
                $scope.info = matches[4];
            });
        },
        templateurl: "partials/node-date.html"
    },
    root: {template: '<nodes nodes="node.children"></node>'},
    _default: {templateurl: "partials/node-default.html"},
};
nodetypes.sleep = nodetypes.day;

var optiontypes = {
    _default: {templateurl: "partials/option-default.html"}
}

function activeclass($scope) {
    $scope.activeclass = function() {
        var ids = $scope.pool.ids;
        var ref = ids.active_ref != null;
        var node = $scope.node;
        return {
            started: node.started,
            finished: node.finished,
            active: !ref && node.active_id === ids.active,
            activeref: ref && node.id === ids.active_ref,
            activewithref: ref && node.active_id === ids.active,
            imactive: node.id == ids.active
        };
    }
}

angular.module("todotracker", [], function($rootScopeProvider) {
        profile("angular init");
        $rootScopeProvider.digestTtl(200);
    })
    .run(function(backend, handlers) {
        profile("angular ready, connecting");
        backend.__host__.connect();
    })
    .directive("autofocus", function() {
        return function(scope, element, attrs) {
            function ensure(backoff) {
                if (backoff > 2000) {
                    return;
                }
                if (!angular.isDefined(backoff)) {
                    backoff = 10;
                }
                element.focus();
                setTimeout(function() { ensure(backoff * 5); }, backoff);
            }
            scope.$on("panel_shown", function() {
                ensure();
            });
        };
    })
    .directive("nodes", function() {
        return {
            restrict: 'E',
            template: '<div class="nodes">'
                    + '<node ng-repeat="subnode in nodes" node="subnode" option="options" pool="pool">'
                    + '</node></div>',
            scope: {
                nodes: "=",
                options: "=",
                pool: "="
            },
            replace: true
        };
    })
    .directive("collapseable", function() {
        return {
            restrict: "E",
            transclude: true,
            replace: true,
            scope: {
                nodes: '=',
                options: '=',
                pool: '='
            },
            templateUrl: "partials/collapseable.html",
            link: function(scope, element, attrs) {
                scope.addnodes = angular.isDefined(attrs.nodes);
                scope.collapsed = angular.isDefined(attrs.collapsed);
                attrs.$observe("text", function(text) {
                    if (text) {
                        scope.collapsedtext = text;
                    } else {
                        scope.collapsedtext = "...";
                    }
                });
                scope.$watch("collapsed", function(collapsed) {
                    scope.evershown = scope.evershown || !collapsed;
                    scope.$parent[attrs.shown] = !collapsed;
                });
            }
        };
    })
    .directive("externEnter", function() {
        return {
            link: function(scope, element, attrs) {
                element.bind("keydown keypress", function(event) {
                    if(event.which === 13) {
                        scope.$apply(function(){
                            scope.$eval(attrs.externEnter);
                        });

                        event.preventDefault();
                    }
                });
            }
        };
    })
    .directive("node", function($compile, $templateCache, $http, $injector) {
        return {
            restrict: "E",
            replace: true,
            template: "<div>loading...</div>",
            compile: function(tElement, tAttrs) {
                return function(scope, element, attrs) {
                    var childscope;
                    var lastnodetype;
                    var is_option = scope.$eval(attrs.option);
                    var _things;
                    if (is_option) {
                        _things = {
                            nodeobj: function() {
                                return scope[attrs.node];
                            },
                            nodetype: function() {
                                var n = _things.nodeobj();
                                if (n === undefined) return undefined;
                                return n.type;
                            },
                            nodeid: function() {
                                return undefined;
                            },
                            nodetypes: optiontypes,
                            ntype: "option"
                        };
                    } else {
                        _things = {
                            nodeobj: function() {
                                var pool = scope[attrs.pool];
                                if (pool === undefined) return undefined;
                                var nodeid = scope.$eval(attrs.node);
                                if (nodeid === undefined) return undefined;
                                return pool[nodeid];
                            },
                            nodetype: function() {
                                var n = _things.nodeobj();
                                if (n === undefined) return undefined;
                                return n.type;
                            },
                            nodeid: function() {
                                return scope.$eval(attrs.node);
                            },
                            nodetypes: nodetypes,
                            ntype: "node"
                        };
                    }

                    scope.$watch(_things.nodeobj, function(node) {
                        if (!angular.isDefined(childscope)) return;
                        if (!angular.isDefined(node)) return;
                        childscope.node = node;
                    });
                    scope.$watch(_things.nodeid, function(nodeid) {
                        if (nodeid === undefined) return;
                        element.attr("nodeid", nodeid);
                    });
                    scope.$watch(_things.nodetype, function(type, last) {
                        if (!angular.isDefined(type)) {
                            return;
                        }
                        // get node type
                        var nodetype = _things.nodetypes[type];
                        if (typeof nodetype == 'string') {
                            nodetype = _things.nodetypes[nodetype];
                        }
                        if (!angular.isDefined(nodetype)) {
                            nodetype = _things.nodetypes._default;
                        }
                        if (nodetype === lastnodetype) return;
                        lastnodetype = nodetype;

                        element.addClass(_things.ntype);

                        // update childscope and css
                        if (angular.isDefined(last)) {
                            element.removeClass(_things.ntype + "-" + last);
                        }
                        if (angular.isDefined(childscope)) {
                            childscope.$destroy();
                        }
                        element.addClass(_things.ntype + "-" + type);
                        childscope = scope.$new();
                        childscope.node = _things.nodeobj();
                        activeclass(childscope);

                        // render new html
                        if (angular.isDefined(nodetype.templateurl)) {
                            $http.get(nodetype.templateurl, {cache: $templateCache})
                                .success(function(template) {
                                    finishlink(template, nodetype, element);
                                });
                        } else {
                            finishlink(nodetype.template, nodetype, element);
                        }
                    });

                    function finishlink(template, nodetype, tElement) {
                        if (angular.isDefined(nodetype.controller)) {
                            $injector.invoke(nodetype.controller, null, {
                                $scope: childscope,
                            });
                        }
                        childscope.is_toplevel = angular.isDefined(attrs.toplevel);

                        element.html(template);
                        var link = $compile(element.contents());
                        link(childscope);
                    }
                };
            }
        }
    })
    .factory("backend", function($rootScope, $timeout) {
        profile("backend");
        browser_compat($rootScope);
        var b = $rootScope.$new();
        $rootScope.backend = b;

        b.prompt = [];
        b.notifications = [];
        b.__host__ = tracker_api;

        b.send = function(obj) {
            b.__host__.sendline(JSON.stringify(obj));
        }

        var notePrefixes = [".......... - ", "!!!!!!!!!! - "];
        var notePrefix = 0;

        function reset_menu_text() {
            if (b.notifications.length) {
                set_menu_text();
            }
            // FIXME: this causes a scope update every second :(
            //$timeout(reset_menu_text, 1000);
        }
        reset_menu_text();

        function set_menu_text() {
            var x = $.merge([], promptfunc());
            if (b.notifications.length) {
                var last = b.notifications[b.notifications.length-1];
                $.merge(x, [notePrefixes[notePrefix] + last]);
                notePrefix += 1;
                if (notePrefix >= notePrefixes.length) {
                    notePrefix = 0;
                }
            }
            if (b.editor_running) {
                $.merge(x, ["editor running"]);
            }
            b.__host__.setMenuText(JSON.stringify(x));
        }

        b.$watch("quit", function(x) {
            if (x) {
                b.__host__.quit();
            }
        });

        b.$watch("max_width", function(x) {
            if (!angular.isDefined(x)) return;
            b.__host__.setMaxWidth(x);
        });

        var promptfunc = function() {
            var result = [];
            if (b.promptnodes === undefined) return [];
            if (b.pool === undefined) return [];
            angular.forEach(b.promptnodes, function(nodeid) {
                var node = b.pool[nodeid];
                var realnode = node;
                if (node === undefined) {
                    result.push("node not found: " + nodeid);
                    return;
                }
                if (node.active_id !== undefined && node.id !== node.active_id) {
                    node = b.pool[node.active_id];
                }
                var text = "" + realnode.type;
                if (node.text !== null && node.text !== undefined) {
                    text += ": " + node.text;
                }
                result.push(text);
            });
            return result;
        }
        b.$watch(promptfunc, function(x) {
            if (!angular.isDefined(x)) return;
            set_menu_text();
        }, true)

        b.$watch("notifications", function(ns) {
            if (!angular.isDefined(ns)) return;
            set_menu_text();
        }, true);
        b.$watch("editor_running", function(ns) {
            if (!angular.isDefined(ns)) return;
            set_menu_text();
        });

        b.$watch("display", function(x) {
            if (!angular.isDefined(x)) return;
            b.__host__.setPanelShown(x);
        })
    

        return b;
    })
    .factory("handlers", function($rootScope, backend) {
        profile("handlers");
        _handlers.panel_shown = function() {
            $rootScope.$broadcast("panel_shown"); $rootScope.$digest();
        };

        _handlers.panel_hidden = function() {
            $rootScope.$broadcast("panel_hidden"); $rootScope.$digest();
        };

        _handlers.attempting_reconnect = function() {
            $rootScope.$broadcast("attempting_reconnect"); $rootScope.$digest();
        };

        _handlers.connected = function() {
            profile("connected");
            $rootScope.$broadcast("connected");
            backend.send({ui_connected: true});
            $rootScope.$digest();
        };

        _handlers.disconnected = function() {
            $rootScope.$broadcast("disconnected"); $rootScope.$digest();
        };

        _handlers.message_received = function(message) {
            var loaded = JSON.parse(message);
            angular.forEach(loaded, function(value, key) {
                $rootScope.$broadcast("message/" + key, value);
            })
            $rootScope.$digest();
        };

        _handlers.status_changed = function(message) {
            $rootScope.backend.connection_status = message;
            $rootScope.$digest();
        };

        _handlers.browser_compat_mode = function() {
            $rootScope.browser_compat = true; $rootScope.$digest();
        };

        _handlers.calculate_height = function() {
            return 750;
        }

        _handlers.calculate_width = function() {
            return 1200;
        }

        $rootScope.$on("message/promptnodes", function(event, promptnodes) {
            backend.promptnodes = promptnodes;
        });
        $rootScope.$on("message/notification", function(event, info) {
            backend.notifications.push(info);
        });
        $rootScope.$on("message/max_width", function(event, maxwidth) {
            backend.max_width = maxwidth;
        });
        $rootScope.$on("message/display", function(event, display) {
            backend.display = display;
        });
        $rootScope.$on("message/editor_running", function(event, editor_running) {
            backend.editor_running = editor_running;
        });
        $rootScope.$on("message/should_quit", function(event, should_quit) {
            backend.quit = should_quit;
        });
        $rootScope.$on("message/pool", function(event, pool) {
            backend.pool = pool;
            $rootScope.pool = pool;
        });
        $rootScope.$watch(function() {
            profile("rootscope");
        });


        return _handlers;
    })
