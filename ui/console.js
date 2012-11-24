
//////////////////////////
// ui_console.log hack

jQuery.fn.getPath = function () {
    if (this.length != 1) throw 'Requires one element.';

    var path, node = this;
    while (node.length) {
        var realNode = node[0], name = realNode.localName;
        if (!name) break;
        name = name.toLowerCase();

        var parent = node.parent();

        var siblings = parent.children(name);
        if (siblings.length > 1) { 
            name += ':eq(' + siblings.index(realNode) + ')';
        }

        path = name + (path ? '>' + path : '');
        node = parent;
    }

    return path;
};

function typeOf(value) {
    var s = typeof value;
    if (s === 'object') {
        if (value) {
            if (Object.prototype.toString.call(value) == '[object Array]') {
                s = 'array';
            }
        } else {
            s = 'null';
        }
    }
    return s;
}


function isEmpty(o) {
    var i, v;
    if (typeOf(o) === 'object') {
        for (i in o) {
            v = o[i];
            if (v !== undefined && typeOf(v) !== 'function') {
                return false;
            }
        }
    }
    return true;
}

if (!String.prototype.entityify) {
    String.prototype.entityify = function () {
        return this.replace(/&/g, "&amp;").replace(/</g,
            "&lt;").replace(/>/g, "&gt;");
    };
}

if (!String.prototype.quote) {
    String.prototype.quote = function () {
        var c, i, l = this.length, o = '"';
        for (i = 0; i < l; i += 1) {
            c = this.charAt(i);
            if (c >= ' ') {
                if (c === '\\' || c === '"') {
                    o += '\\';
                }
                o += c;
            } else {
                switch (c) {
                case '\b':
                    o += '\\b';
                    break;
                case '\f':
                    o += '\\f';
                    break;
                case '\n':
                    o += '\\n';
                    break;
                case '\r':
                    o += '\\r';
                    break;
                case '\t':
                    o += '\\t';
                    break;
                default:
                    c = c.charCodeAt();
                    o += '\\u00' + Math.floor(c / 16).toString(16) +
                        (c % 16).toString(16);
                }
            }
        }
        return o + '"';
    };
}

if (!String.prototype.supplant) {
    String.prototype.supplant = function (o) {
        return this.replace(
            /\{([^{}]*)\}/g,
            function (a, b) {
                var r = o[b];
                return typeof r === 'string' || typeof r === 'number' ? r : a;
            }
        );
    };
}

if (!String.prototype.trim) {
    String.prototype.trim = function () {
        return this.replace(/^\s*(\S*(?:\s+\S+)*)\s*$/, "$1");
    };
}


function repr(o, depth, max) {
      var e, k;
      if (depth == null) {
        depth = 0;
      }
      if (max == null) {
        max = 2;
      }
      if (depth > max) {
        return '<..>';
      } else {
        if (o == null) {
          return 'null';
        }
        switch (typeOf(o)) {
          case 'string':
            return "\"" + (o.replace(/"/g, '\\"')) + "\"";
          case 'function':
            return "" + o;
          case 'object':
              return '{' + [
                (function() {
                  _results = [];
                  $.each(o, function(index, item) {
                    _results.push('' + index + ':' + repr(item, depth + 1, max));
                  });
                  return _results;
                })()
              ] + '}';
          case 'array':
              return '[' + [
                (function() {
                  var _i, _len, _results;
                  _results = [];
                  for (_i = 0, _len = o.length; _i < _len; _i++) {
                    e = o[_i];
                    _results.push('' + repr(e, depth + 1, max));
                  }
                  return _results;
                })()
              ] + ']';
          case 'undefined':
            return 'undefined';
          default:
            return o;
        }
      }
};

ui_console = {
    _count: 0,
    _highlit: false,
    log: function() {
        try {
            ui_console._log_unsafe.apply(null, arguments);
        } catch (e) {
            var args = [];
            for (index=0; index< arguments.length; index++) {
                args.push("" + arguments[index]);
            }
            ui_console._log_unsafe("error logging: " + args + " error was " + e);
        }
    },
    _log_unsafe: function() {
        var args = [];
        for (index=0; index< arguments.length; index++) {
            if (typeof arguments[index] == "string") {
                args.push(arguments[index]);
            } else {
                args.push("" + repr(arguments[index]));
            }
        }
        var element = $handlebars("._js_messages .template", {
            args: args,
            highlit: ui_console._highlit,
            count: ui_console._count
        });
        ui_console._count += 1;
        ui_console._highlit = !ui_console._highlit;
        $("._js_messages").append(element);
        $("._js_messages_scroller").scrollTop($("._js_messages").height());
    }
};

function min(x, y) {
    if (x < y) {return x;}
    else return y;
}

function assert(x, message) {
    if (!x) {
        ui_console.log("houston, we've had a problem", message);
    }
}

