angular.module("treeoflife")
.directive("tlEditor", function(backend, $rootScope) {
    return {
        restrict: "E",
        templateUrl: "partials/editor.html",
        replace: true,
        link: function($scope, $element, $attrs) {
            $scope.$on("message/embedded_edit", function(event, edit) {
                $scope.editor = edit;
                if ($scope.editor) {
                    $scope.editor.initial = $scope.editor.data;
                }
                $scope.use_embedded = true;
            });

            $scope.cancel = function() {
                $scope.editor.data = null;
                $scope.commit();
            }

            $scope.commit = function() {
                backend.send({
                    embedded_editor_finished: {
                        identifier: $scope.editor.identifier,
                        data: $scope.editor.data
                    }
                });
                $rootScope.$broadcast("editor_done");
            }
        }
    }
})
.directive("codemirror", function() {
    return {
        restrict: "E",
        scope: {
            editor: "=",
            save: "&"
        },
        link: function($scope, $element, $attrs) {
            var cm = CodeMirror($element[0], {
                mode: "yaml",
                theme: "monokai",
                indentUnit: 4,
                smartIndent: false,
                tabSize: 4,
                electricChars: false,
                keyMap: "vim",
                lineNumbers: true,
                undoDepth: 200,
            });
            $scope.$watch("editor", function(editor) {
                if (editor) {
                    cm.setValue(editor.data);
                } else {
                    cm.setValue("");
                }
                cm.markClean();
                cm.focus();
                var s = cm.getSearchCursor(/@active/);
                if (s.find()) {
                    var position = s.start();
                    cm.setCursor(position);
                }
            });

            cm.on("change", function() {
                if ($scope.editor) {
                    $scope.editor.data = cm.getValue();
                }
            });
        }
    };
});
