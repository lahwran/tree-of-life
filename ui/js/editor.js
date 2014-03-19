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
            doCancel: "&",
            doCommit: "&"
        },
        link: function($scope, $element, $attrs) {
            var options = {
                mode: "yaml",
                theme: "monokai",
                indentUnit: 4,
                smartIndent: false,
                tabSize: 4,
                electricChars: false,
                keyMap: "vim",
                lineNumbers: true,
                undoDepth: 200,
            };

            CodeMirror.Vim.defineEx("writeandquit", "writeandquit", function() {
                $scope.doCommit();
            });
            CodeMirror.Vim.map(":wqa", ":writeandquit");
            CodeMirror.Vim.map(":wq", ":writeandquit");
            CodeMirror.Vim.map(":w", ":writeandquit");
            CodeMirror.Vim.defineEx("quit", "quit", function() {
                $scope.doCancel();
            });
            CodeMirror.Vim.map(":qa", ":quit");
            CodeMirror.Vim.map(":q", ":quit");

            var cm = CodeMirror($element[0], options);
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
                    var position = s.from();
                    cm.setCursor(position);
                    center();
                }
            });

            function center() {
                // shamelessly stolen from codemirror vim.js
                var lineNum = cm.getCursor().line;
                var charCoords = cm.charCoords({line: lineNum, ch: 0}, 'local');
                var height = cm.getScrollInfo().clientHeight;
                var y = charCoords.top;
                var lineHeight = charCoords.bottom - y;

                y = y - (height / 2) + lineHeight;

                cm.scrollTo(null, y);
            }

            cm.on("change", function() {
                if ($scope.editor) {
                    $scope.editor.data = cm.getValue();
                }
            });
        }
    };
});
