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
        tracker_api.quit();
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
    $scope.$on("message/prompt", function(event, prompt) {
        $scope.backend.prompt = prompt;
    });
    $scope.$on("message/notification", function(event, info) {
        $scope.backend.notifications.push(info);
    });
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
        backend.host.connect();
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

        $rootScope.backend = {prompt: [], notifications: []};
        var b = $rootScope.backend;
        var notePrefixes = [".......... - ", "!!!!!!!!!! - "];
        var notePrefix = 0;
        function resetMenuText() {
            if (b.notifications.length) {
                setMenuText();
            }
            $timeout(resetMenuText, 1000);
        }
        resetMenuText();
        function setMenuText() {
            var x;
            if (b.notifications.length) {
                var last = b.notifications[b.notifications.length-1];
                var c = $.merge([], $rootScope.backend.prompt);
                x = $.merge(c, [notePrefixes[notePrefix] + last]);
                notePrefix += 1;
                if (notePrefix >= notePrefixes.length) {
                    notePrefix = 0;
                }
            } else {
                x = b.prompt;
            }
            tracker_api.setMenuText(JSON.stringify(x));
        }

        $rootScope.$watch("backend.prompt", function(x) {
            if (!angular.isDefined(x)) return;
            setMenuText();
        })
        $rootScope.$watch("backend.notifications", function(ns) {
            if (!angular.isDefined(ns)) return;
            setMenuText();
        }, true);
        b.removeNotification = function(index) {
            b.notifications.splice(index, 1);
        }
        return {
            host: tracker_api,
            send: function(obj) {
                tracker_api.sendline(JSON.stringify(obj));
            }
        };
    })
    .factory("handlers", function($rootScope, backend) {
        _handlers.panel_shown           = function() { $rootScope.$broadcast("panel_shown"); };
        _handlers.panel_hidden          = function() { $rootScope.$broadcast("panel_hidden"); };
        _handlers.attempting_reconnect  = function() { $rootScope.$broadcast("attempting_reconnect"); };
        _handlers.connected             = function() {
            $rootScope.$broadcast("connected");
            backend.send({ui_connected: true});
            $rootScope.$digest();
        };
        _handlers.disconnected          = function() { $rootScope.$broadcast("disconnected"); };
        _handlers.message_received      = function(message) {
            var loaded = JSON.parse(message);
            angular.forEach(loaded, function(value, key) {
                $rootScope.$broadcast("message/" + key, value);
            })
            $rootScope.$digest();
        };
        _handlers.status_changed        = function(message) { $rootScope.backend.connection_status = message; };
        _handlers.browser_compat_mode   = function() { $rootScope.browser_compat = true; };
        _handlers.calculate_height = function() {
            return 800;
            var value = 0;
            function add(v) { value += v; }
            $rootScope.$broadcast("heightcalc", add);
            return value;
        }
        _handlers.calculate_width = function() {
            return 1200;
            var value = 0;
            function add(v) { value += v; }
            $rootScope.$broadcast("widthcalc", add);
            return value;
        }
        return _handlers;
    })
    /*.directive("heightbox", function() {
        return function(scope, element, attrs) {
            scope.$on("heightcalc", function(addheight) {
                if (attrs.heightElement == "element") {
                    addheight(element.height());
                } else if (attrs.heightElement == "border") {
                    addheight(element.outerHeight(false));
                } else {
                    addheight(element.outerHeight(true));
                }
            });
        }
    })
    .directive("widthbox", function() {
        return function(scope, element, attrs) {
            scope.$on("widthcalc", function(addheight) {
                if (attrs.heightElement == "element") {
                    addheight(element.height());
                } else if (attrs.heightElement == "border") {
                    addheight(element.outerHeight(false));
                } else {
                    addheight(element.outerHeight(true));
                }
            });
        }
    })*/
