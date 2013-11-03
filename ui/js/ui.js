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



function ui_controller($scope, connection, handlers) {
    $scope.inbrowser = inbrowser;
    $scope.root = {
        type: "root",
        text: null,
        children: []
    }
    $scope.sendcommand = function(command) {
        connection.send({command: command});
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
}

var nodetypes = {
    days: {templateurl: "partials/node-days.html"},
    day: {
        controller: function($scope) {
            console.log($scope.node);
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

angular.module("todotracker", [], function($rootScopeProvider) {
        $rootScopeProvider.digestTtl(200);
    })
    .run(function(connection, handlers) {
        connection.host.connect();
    })
    .directive("autofocus", function() {
        return function(scope, element, attrs) {
            function ensure(backoff) {
                if (element.is(":focus")) {
                    return;
                }
                if (!angular.isDefined(backoff)) {
                    backoff = 10;
                } else {
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
            template: '<node ng-repeat="subnode in nodes track by $index" node="subnode">'
                    + '</node>',
            scope: {
                nodes: "="
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
                nodes: '='
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
            template: "<div class='node'>loading...</div>",
            compile: function(tElement, tAttrs) {
                return function(scope, element, attrs) {
                    var childscope;
                    var lastnodetype;
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

                        // get node type
                        var nodetype = nodetypes[type];
                        if (typeof nodetype == 'string') {
                            nodetype = nodetypes[nodetype];
                        }
                        if (!angular.isDefined(nodetype)) {
                            nodetype = nodetypes._default;
                        }
                        if (nodetype === lastnodetype) return;
                        lastnodetype = nodetype;

                        // update childscope and css
                        if (angular.isDefined(last)) {
                            element.removeClass("node-"+last);
                        }
                        if (angular.isDefined(childscope)) {
                            childscope.$destroy();
                        }
                        element.addClass("node-"+type);
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
    .factory("connection", function() {
        return {
            host: tracker_api,
            send: function(obj) {
                tracker_api.sendline(JSON.stringify(obj));
            }
        };
    })
    .factory("handlers", function($rootScope, connection) {
        _handlers.panel_shown           = function() { $rootScope.$broadcast("panel_shown"); };
        _handlers.panel_hidden          = function() { $rootScope.$broadcast("panel_hidden"); };
        _handlers.attempting_reconnect  = function() { $rootScope.$broadcast("attempting_reconnect"); };
        _handlers.connected             = function() {
            $rootScope.$broadcast("connected");
            connection.send({ui_connected: true});
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
        _handlers.status_changed        = function(message) { $rootScope.connection_status = message; };
        _handlers.browser_compat_mode   = function() { $rootScope.browser_compat = true; };
        _handlers.calculate_height = function() {
            return 800;
            var value = 0;
            function add(v) { value += v; }
            $rootScope.$broadcast("heightcalc", add);
            return value;
        }
        _handlers.calculate_width = function() {
            return 600;
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
