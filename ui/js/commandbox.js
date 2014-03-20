angular.module("treeoflife")
.directive("tlCommandbox", function() {
    return {
        restrict: "E",
        template: '<input type="text" ng-model="command" class="commandbox reset" tl-keypress="keys" autofocus>',
        replace: true,
        scope: {
            sendCommand: "="
        },
        link: function($scope, $element, $attrs) {
            $scope.keys = {
                13: function() {
                    var c = $scope.command;
                    $scope.command = "";
                    $scope.sendCommand(c);
                },
                35: function() {
                    var l = $scope.command.length;
                    $element[0].setSelectionRange(l, l);
                },
                36: function() {
                    $element[0].setSelectionRange(0, 0);
                }
            }
        }
    };
});
