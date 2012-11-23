/////////////////////////
// chrome compat




//////////////////////////
// call-in handlers
function on_panel_shown() {
    console.log("on_panel_shown");
    setTimeout(function(){
      $(".command-box input").focus();
        console.log("focused input box");
    }, 10);
}
function on_panel_hidden () {
    // nothing to do here for now
}
function on_attempting_reconnect () {
    console.log("attempting_reconnect");
}
function on_message_received(message) {
    try {
        console.log("received message:", message);
        var loaded = $.parseJSON(message);
        $.each(loaded, function(key, value) {
            var func = message_handlers[key];
            console.log("calling func", func, "with", value);
            if (func) {
                func(value);
            }
        });
        tracker_api.resize();
    } catch(err) {
        console.log("ERROR:", err);
    }
}
function on_status_changed(message) {
    console.log("status_changed: ", message);
}
function on_calculate_width() {
    var width = min($(".size-container").width(), tracker_api.getScreenWidth()/2);
    return width;
}
function on_calculate_height() {
    var max_height = tracker_api.getScreenHeight() - 50;

    set_heights(max_height);

    var context_height = $(".content .context-outer").height();
    var context_real_height = $(".content .context").height();
    if (context_real_height > context_height) {
        $(".context-outer").parents(".shadow-container").addClass("well");
    } else {
        $(".context-outer").parents(".shadow-container").removeClass("well");
    }

    var height = min($(".size-container").outerHeight(true), max_height);
    return height;
}

/////////////////////////
// height calc

function get_height_adds() {
    var total_height = {value: 0};
    $(".height-add").each(function(item) {
        var height = $(this).outerHeight(true);
        console.log("item:", $(this).getPath(), "outerheight:", height);
        total_height.value += height;
    });
    return total_height.value;
}

function set_heights(max_height) {
    var used = get_height_adds();
    assert(used <= max_height, "height-add elements taller than max height");
    console.log("max-height:", max_height);
    console.log("used height:", used);

    var height_remaining = $(".height-remaining");
    assert(height_remaining.length == 1, "wrong number of height-remaining elements");
    var height_vestigial = height_remaining.outerHeight(true);

    if (height_remaining.parents(".height-add").length) {
        used -= height_vestigial;
        console.log("used changed to", used, "because vestigial", height_vestigial);
    }

    var fat = height_vestigial - height_remaining.height();
    console.log("fat:", fat);
    var target_max = max_height - (used + fat);
    console.log("target_max:", target_max);
    assert(target_max > 0, "too much fat on height-remaining element");
    assert(target_max + used + fat == max_height, "calculation error");
    height_remaining.css("max-height", "" + target_max + "px");
}

handlers = {
    on_panel_hidden: function() {
        console.log("secondary panel hidden");
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

/////////////////////////
// handlers for message types

message_handlers = {
    suggestions: function(suggestions) {
        console.log("suggestions:", suggestions);
        $(".suggestions .suggestion").remove();
        $.each(suggestions, function(index, item) {
            $(".suggestions").append($handlebars(".suggestions .template", {"suggestion": item}));
        });
        console.log("suggestions done");
    },
    messages: function(messages) {
        console.log("messages:", messages);
        $(".messages .message").remove();
        $.each(messages, function(index, item) {
            $(".messages").append($handlebars(".messages .template", {"message": item}));
        });
        console.log("messages done");
    },
    context: function(context) {
        console.log("context:", context);
        $(".context").html(context.join("\n"));
        console.log("context done");
    },
    prompt: function(prompt) {
        tracker_api.setMenuText(JSON.stringify(prompt));
    },
    should_quit: function(should_quit) {
        if (should_quit) {
            tracker_api.quit();
        }
    },
    display: tracker_api.setPanelShown,
    max_width: tracker_api.setMaxWidth
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
    command_typing: function(event) {
        if(event.which == 13) {
            message({command: $(".command-box input").val()});
            $(".command-box input").val("");
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
    $(".command-box input").keypress(ui_handlers.command_typing);
    $(".quit").click(ui_handlers.quit);

    var d = new Date();
    var n = d.getTime();
    $(".loaded-at").text("" + n);
    tracker_api.resize();
    tracker_api.connect();
});
