
//////////////////////////
// console.log hack

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
        switch (typeOf(o)) {
          case 'string':
            return "\"" + (o.replace(/"/g, '\\"')) + "\"";
          case 'function':
            return "" + o;
          case 'null':
            if (o === null) {
              'null';

            }
          case 'object':
              return '{' + [
                (function() {
                  var _i, _len, _ref, _results;
                  _ref = _.keys(o);
                  _results = [];
                  for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                    k = _ref[_i];
                    _results.push('' + k + ':' + repr(o[k], depth + 1, max));
                  }
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

_old_console = console;
var _old_log = Function.prototype.bind.call(console.log, console);
console = {
    _count: 0,
    _highlit: false,
    log: function() {
        var newargs = Array.prototype.slice.call(arguments);
        _old_log.apply(null, newargs);
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
            highlit: console._highlit,
            count: console._count
        });
        console._count += 1;
        console._highlit = !console._highlit;
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
        console.log("houston, we've had a problem", message);
    }
}

