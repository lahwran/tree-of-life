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
    $scope.sidebar = {};
    $scope.sendcommand = function(command) {
        backend.send({command: command});
        $scope._command = "";
    }
    $scope._quit = function() {
        backend.quit = true;
    }
    $scope.$on("message/tree", function(event, tree) {
        $scope.root.children = tree;
        console.log(tree);
        angular.forEach(tree, function(child) {
            if (child.type == "days") {
                $scope.days = child;
            } else if (child.type == "todo bucket") {
                $scope.todo_bucket = child;
            }
        });
    });
    $scope.notifications = backend.notifications;
    $scope.removeNotification = function(index) {
        $scope.notifications.splice(index, 1);
    }

    function whatareyoudoing() {
        $timeout(whatareyoudoing, 30 * 60 * 1000);
        $scope.backend.notifications.push("What are you currently doing?");
    }
    whatareyoudoing();
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

angular.module("todotracker", [], function($rootScopeProvider) {
        $rootScopeProvider.digestTtl(200);
    })
    .run(function(backend, handlers) {
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
                console.log("derp");
                ensure();
            });
        };
    })
    .directive("nodes", function() {
        return {
            restrict: 'E',
            template: '<div class="nodes"><node ng-repeat="subnode in nodes track by $index" node="subnode" option="options">'
                    + '</node></div>',
            scope: {
                nodes: "=",
                options: "="
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
                options: '='
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
                    scope.$watch(attrs.node, function(node) {
                        if (!angular.isDefined(childscope)) return;
                        childscope.node = node;
                    });
                    scope.$watch(function() {
                            if (!angular.isDefined(scope[attrs.node])) return undefined;
                            return scope[attrs.node].type;
                    }, function(type, last) {
                        if (!angular.isDefined(type)) {
                            return;
                        }
                        var chosen_nodetypes;
                        var ntype;
                        if (is_option) {
                            chosen_nodetypes = optiontypes;
                            ntype = "option";
                        } else {
                            chosen_nodetypes = nodetypes;
                            ntype = "node";
                        }

                        // get node type
                        var nodetype = chosen_nodetypes[type];
                        if (typeof nodetype == 'string') {
                            nodetype = chosen_nodetypes[nodetype];
                        }
                        if (!angular.isDefined(nodetype)) {
                            nodetype = chosen_nodetypes._default;
                        }
                        if (nodetype === lastnodetype) return;
                        lastnodetype = nodetype;

                        element.addClass(ntype);

                        // update childscope and css
                        if (angular.isDefined(last)) {
                            element.removeClass(ntype + "-" + last);
                        }
                        if (angular.isDefined(childscope)) {
                            childscope.$destroy();
                        }
                        element.addClass(ntype + "-" + type);
                        childscope = scope.$new();
                        childscope.node = scope[attrs.node];

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
            $timeout(reset_menu_text, 1000);
        }
        reset_menu_text();

        function set_menu_text() {
            var x;
            if (b.notifications.length) {
                var last = b.notifications[b.notifications.length-1];
                var c = $.merge([], b.prompt);
                x = $.merge(c, [notePrefixes[notePrefix] + last]);
                notePrefix += 1;
                if (notePrefix >= notePrefixes.length) {
                    notePrefix = 0;
                }
            } else {
                x = b.prompt;
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

        b.$watch("prompt", function(x) {
            if (!angular.isDefined(x)) return;
            set_menu_text();
        })

        b.$watch("notifications", function(ns) {
            if (!angular.isDefined(ns)) return;
            set_menu_text();
        }, true);

        b.$watch("display", function(x) {
            if (!angular.isDefined(x)) return;
            b.__host__.setPanelShown(x);
        })
    

        return b;
    })
    .factory("handlers", function($rootScope, backend) {
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

        $rootScope.$on("message/prompt", function(event, prompt) {
            backend.prompt = prompt;
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


        return _handlers;
    })
