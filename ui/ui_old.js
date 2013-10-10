/////////////////////////
// chrome compat




//////////////////////////
// call-in handlers
function on_panel_shown() {
    setTimeout(function(){
      $(".command-box input").focus();
    }, 10);
}
function on_panel_hidden () {
    // nothing to do here for now
}
function on_attempting_reconnect () {
}
function on_message_received(message) {
    var loaded = $.parseJSON(message);
    $.each(loaded, function(key, value) {
        var func = message_handlers[key];
        if (func) {
            func(value);
        }
    });
}
function on_status_changed(message) {
}
function on_calculate_width() {
    var width = min($(".size-container").width(), tracker_api.getScreenWidth()/2);
    return width;
}
function on_calculate_height() {
    var max_height = tracker_api.getScreenHeight() - 50;

    set_heights(max_height);

    var tree_height = $(".content .tree-outer").height();
    var tree_real_height = $(".content .tree").height();
    if (tree_real_height > tree_height) {
        $(".tree-outer").parents(".shadow-container").addClass("well");
    } else {
        $(".tree-outer").parents(".shadow-container").removeClass("well");
    }

    var height = min($(".size-container").outerHeight(true), max_height);
    return height;
}

function on_disconnected() {
    // derp...
}

function on_connected() {
    $("._js_messages").empty();
    $(".content .status").empty();
    $(".content .todo").empty();
    $(".content .tree").empty();
    message({ui_connected: true});
}

/////////////////////////
// height calc

function get_height_adds() {
    var total_height = {value: 0};
    $(".height-add").each(function(item) {
        var height = $(this).outerHeight(true);
        total_height.value += height;
    });
    return total_height.value;
}

function set_heights(max_height) {
    var used = get_height_adds();
    assert(used <= max_height, "height-add elements taller than max height");

    var height_remaining = $(".height-remaining");
    assert(height_remaining.length == 1, "wrong number of height-remaining elements");
    var height_vestigial = height_remaining.outerHeight(true);

    if (height_remaining.parents(".height-add").length) {
        used -= height_vestigial;
    }

    var fat = height_vestigial - height_remaining.height();
    var target_max = max_height - (used + fat);
    assert(target_max > 0, "too much fat on height-remaining element");
    assert(target_max + used + fat == max_height, "calculation error");
    height_remaining.css("max-height", "" + target_max + "px");
}

handlers = {
    on_panel_hidden: function() {
    }
}

/////////////////////////
// handlebars util
_handlebars_cache = {};
function $handlebars(query, input) {
    var template = _handlebars_cache[query];
    if (template == undefined) {
        template = Handlebars.compile($(query).html());
        _handlebars_cache[query] = template;
    }
    return $(template(input));
}

function render_tree(tree) {
    if (tree.is_toplevel === true && tree.type != "days") {
        return "";
    }

    var rendered = $handlebars(".node-template", tree);
    if (tree.type === "day") {
        rendered.css("margin-top",
                "" + tree.prefix_delta + "px !important");
    }
    var children_bucket = rendered.find(".children");
    if (tree.children) {
        $.each(tree.children, function(index, item) {
            children_bucket.append(render_tree(item));
        });
    }
    return rendered;
}

/////////////////////////
// handlers for message types

message_handlers = {
    status: function(status) {
        $(".content .status").html(status);
        tracker_api.resize();
    },
    tree: function(tree_root) {
        $(".tree").empty();
        $.each(tree_root, function(index, item) {
            $(".tree").append(render_tree(item));
            if (item.type == "todo bucket") {
                $(".todo").empty();
                if (item.children) {
                    $.each(item.children, function(index, item) {
                        $(".todo").append(render_tree(item));
                    });
                }
            }
        });
        tracker_api.resize();
    },
    prompt: function(prompt) {
        tracker_api.setMenuText(JSON.stringify(prompt));
    },
    should_quit: function(should_quit) {
        if (should_quit) {
            tracker_api.quit();
        }
    },
    display: function(display) {
        tracker_api.setPanelShown(display);
        if (display) {
            setTimeout(function() {
                tracker_api.resize();
            }, 1);
            setTimeout(function() {
                tracker_api.resize();
            }, 1000);
        }
    },
    max_width: function(width) {
        tracker_api.setMaxWidth(width);
    },
    input: function(input) {
        $(".command-box input").val(input);
    },
    error: function(error) {
        var error_count = parseInt($.trim($(".error-count").text()));

        error_count += 1;
        $(".error-count").text("" + error_count);
        $(".error").text(error);
        $(".error").show();

        setTimeout(function() {
            var error_count_2 = parseInt($.trim($(".error-count").text()));
            if (error_count != error_count_2) {
                return;
            }
            $(".error").hide();

            tracker_api.resize();
        }, 30000);
        tracker_api.resize();
    },
    editor_running: function(editor_running) {
        if (editor_running) {
            $(".editor-running").show();
            $(".tree").hide();
            $(".todo").hide();
        } else {
            $(".editor-running").hide();
            $(".tree").show();
            $(".todo").show();
        }
        tracker_api.resize();
    }
}

function message(obj) {
    tracker_api.sendline(JSON.stringify(obj));
}

//////////////////////////
// ui handlers

ui_handlers = {
    toggle_bottom: function(event) {
        event.preventDefault();
        if ($(".bottom-content").is(":visible")) {
            $(".bottom-content").hide();
            $(".toggle-bottom").removeClass("bottom-line");
        } else {
            $(".bottom-content").show();
            $(".toggle-bottom").addClass("bottom-line");
            $("._js_messages_scroller").scrollTop($("._js_messages").height());
        }
        tracker_api.resize();
    },
    enter_handler: function(event) {
        if(event.which == 13) {
            message({command: $(".command-box input").val()});
            $(".command-box input").val("");
        }
    },
    typing: function(event) {
        if (event.which == 38) {
            message({navigate: "up"});
        } else if (event.which == 40) {
            message({navigate: "down"});
        } else if (event.which == 13) {
            return;
        } else {
            message({input: $(".command-box input").val()});
        }
    },
    quit: function() {
        tracker_api.quit();
    }
}

/////////////////////////
// registration
$(document).ready(function() {
    $(".toggle-bottom").click(ui_handlers.toggle_bottom);
    $(".command-box input").keypress(ui_handlers.enter_handler);
    $(".command-box input").keydown(ui_handlers.typing);
    $(".quit").click(ui_handlers.quit);

    var d = new Date();
    var n = d.getTime();
    $(".loaded-at").text("" + n);
    tracker_api.resize();
    tracker_api.connect();
});
