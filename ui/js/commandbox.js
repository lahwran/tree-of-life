angular.module("treeoflife")
.directive("tlCommandbox", function($rootScope, backend) {
    return {
        restrict: "E",
        template: '<input type="text" ng-model="command" ng-change="changed()" class="commandbox reset" tl-keys="keys" autofocus placeholder="{{syncStatus}}">',
        replace: true,
        scope: {
            sendCommand: "=",
            syncStatus: "="
        },
        link: function($scope, $element, $attrs) {
            $scope.command = "";
            $scope.keys = {
                // enter
                13: function() {
                    var c = $scope.command;
                    $scope.command = "";
                    $scope.sendCommand(c);
                },
                // home
                35: function() {
                    var l = $scope.command.length;
                    $element[0].setSelectionRange(l, l);
                },
                // end
                36: function() {
                    $element[0].setSelectionRange(0, 0);
                },
                // up
                38: function() {
                    backend.send({navigate: "up"});
                },
                // down
                40: function() {
                    backend.send({navigate: "down"});
                }
            }
            $scope.changed = function() {
                if (angular.isDefined($scope.command)) {
                    backend.send({input: $scope.command});
                }
            }
            $rootScope.$on("message/input", function(event, value) {
                $scope.command = value;
            });
        }
    };
});
