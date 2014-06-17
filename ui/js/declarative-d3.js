function d4directive(options) {
    "use strict";
    var prefix = function(string) {
        return options.shapeName + string.substr(0, 1).toUpperCase() + string.substr(1);
    }
    return function($parse) {
        return {
            restrict: "A",
            link: function($scope, $element, $attrs) {
                var shape = d3.svg[options.shapeName]();
                var theobj;

                var writeAttrs = [];
                angular.forEach(options.writeAttrs || [], function(name) {
                    var attr = $attrs[prefix(name)];
                    if (angular.isDefined(attr)) {
                        writeAttrs.push({
                            expression: $parse(attr),
                            name: name
                        });
                    }
                });

                function reshow() {
                    if (waitcount > 0) {
                        return;
                    }
                    angular.forEach(writeAttrs, function(writeAttr) {
                        writeAttr.expression.assign($scope, shape[writeAttr.name](theobj));
                    });
                    $element.attr("d", shape(theobj));
                }
                var waitcount = 1;
                var mainwait = true;
                $scope.$watch($attrs[options.directiveName], function(obj) {
                    if (!angular.isDefined(obj)) {
                        return;
                    }
                    if (mainwait) {
                        mainwait = false;
                        waitcount -= 1;
                    }
                    theobj = obj;
                    reshow();
                })
                angular.forEach(options.attrs, function(name) {
                    var attrName = prefix(name);
                    if (!angular.isDefined($attrs[attrName])) {
                        return;
                    }
                    var mywait = true;
                    waitcount += 1;
                    $scope.$watch($attrs[attrName], function(value) {
                        if (!angular.isDefined(value)) {
                            return;
                        }
                        if (mywait) {
                            mywait = false;
                            waitcount -= 1;
                        }
                        shape[name](value);
                        reshow();
                    });
                });
            }
        };
    };
}

// d3: data driven documents
// d4: declarative data driven documents
angular.module("d4", [])
    .factory("d4ParseAccessor", function($parse) {
        return function(string, scope, defaultFunc) {
            if (!angular.isDefined(string)) {
                return defaultFunc;
            } else {
                var expression = $parse(string);
                return function(x, index) {
                    return expression(scope, {x: x});
                }
            }
        }
    })
    .directive("d4ChartPie", function(d4ParseAccessor) {
        return {
            restrict: "E",
            templateUrl: "/partials/d4-piechart.html",
            replace: true,
            scope: {
                radius: "&",
                innerRadius: "&",
                data: "="
            },
            link: function($scope, $element, $attrs) {
                $scope.colorFromIndex = d3.scale.category20c();

                $scope.value = d4ParseAccessor($attrs.valueAccessor,
                        $scope.$parent, function(x) { return x.value; });
                $scope.label = d4ParseAccessor($attrs.labelAccessor,
                        $scope.$parent, function(x) { return x.label; });

                $scope.$watch("data", function(data) {
                    if (!angular.isDefined(data)) {
                        return;
                    }
                    // https://github.com/mbostock/d3/wiki/Pie-Layout
                    // generates array of objects to be fed to d3.arc
                    var arcObjectCreator = d3.layout.pie()
                        .value($scope.value);

                    // takes: [{..., value: }, ...]
                    // returns: [{data: ..., innerRadius, outerRadius, startAngle, endAngle}, ...]
                    $scope.arcs = arcObjectCreator(data);
                }, true);
            }
        };
    })
    .directive("d4ChartRadial", function(d4ParseAccessor) {
        return {
            restrict: "E",
            templateUrl: "/partials/d4-radialchart.html",
            scope: {
                baselineInnerRadius: "&",
                baselineOuterRadius: "&",
                barInnerRadius: "&",
                barOuterRadius: "&",
                domain: "&",
                data: "="
            },
            replace: true,
            link: function($scope, $element, $attrs) {
                $scope.colorFromIndex = d3.scale.category20c();

                var accessor = d4ParseAccessor($attrs.valueAccessor,
                    $scope.$parent, function(x) { return x.value; });

                var recalculate = function() {
                    var data = $scope.data;
                    var outer = $scope.barOuterRadius();
                    var inner = $scope.barInnerRadius();
                    var domain = $scope.domain();
                    if (!angular.isDefined($scope.data)
                            || !angular.isDefined(inner)
                            || !angular.isDefined(outer)) {
                        return;
                    }
                    if (domain === "extent") {
                        domain = d3.extent(data, accessor);
                    }
                    if (domain[0] === "min") {
                        domain[0] = d3.min(data, accessor);
                    }
                    if (domain[1] === "max") {
                        domain[1] = d3.max(data, accessor);
                    }
                    var scale = d3.scale.linear()
                            .domain(domain)
                            .range([inner, outer]);
                    var curvescale = d3.scale.linear()
                            .domain([0, data.length])
                            .range([0, Math.PI * 2]);

                    var innerArcCount = 8;
                    var innerArcScale = curvescale.copy()
                            .domain([0, innerArcCount]);
                    $scope.innerArcs = [];
                    for (var index=0; index<innerArcCount; index++) {
                        $scope.innerArcs.push({
                            innerRadius: $scope.baselineInnerRadius(),
                            outerRadius: $scope.baselineOuterRadius(),
                            startAngle: innerArcScale(index),
                            endAngle: innerArcScale(index+1)
                        });
                    }

                    $scope.arcs = [];
                    angular.forEach(data, function(item, index) {
                        item = accessor(item);
                        $scope.arcs.push({
                            outerRadius: scale(item),
                            innerRadius: inner,
                            startAngle: curvescale(index),
                            endAngle: curvescale(index+1)
                        })
                    });
                }
                $scope.$watch("data", recalculate, true);
                $scope.$watch("barInnerRadius()", recalculate);
                $scope.$watch("barOuterRadius()", recalculate);
                $scope.$watch("baselineInnerRadius()", recalculate);
                $scope.$watch("baselineOuterRadius()", recalculate);
            }
        };
    })
    .directive("d4Transform", function($parse) {
        return {
            restrict: "A",
            link: function($scope, $element, $attrs) {
                var expression = $parse($attrs.d4Transform);
                var functions = {
                    translate: function(x, y) {
                        if (angular.isDefined(y)) {
                            return "translate(" + x + "," + y + ")";
                        } else {
                            return "translate(" + x + ")";
                        }
                    }
                }
                $scope.$watch(function() {
                    return expression($scope, functions);
                }, function(value) {
                    if (!angular.isDefined(value)) {
                        return;
                    }
                    $element.attr("transform", value);
                });
            }
        }
    })
    .directive("d4Arc", d4directive({
        writeAttrs: ["centroid"],
        shapeName: "arc",
        directiveName: "d4Arc",
        attrs: ["innerRadius", "outerRadius", "startAngle", "endAngle"]
    }));
