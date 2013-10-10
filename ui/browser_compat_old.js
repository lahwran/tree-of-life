function __delaycall(data, amount) {
    setTimeout(function() {
        on_message_received(data);
    }, amount);
}
tracker_api_browser = {
    connect: function() {
        ui_console.log("COMPAT: connecting");
        $(".browser-compat").show();
        $(".command-box .input").addClass("taller");

        tracker_api.socket = new WebSocket("ws://localhost:18083");
        on_status_changed("connecting...");

        tracker_api.socket.onopen = function(event) {
            tracker_api.socket.onmessage = function(event) {
                if (event.data === undefined) return;
                tracker_api._data += event.data;
                var index = 0;
                var pattern = /^([^\n]*\n)(.*)$/;
                while (true) {
                    var match = pattern.exec(tracker_api._data)
                    if (!match) return;
                    console.log(match);
                    tracker_api._data = match[2];
                    __delaycall(match[1], index);
                    index += 1;
                }
            }

            on_status_changed("connected");
            on_connected();
        }
    },
    resize: function() {
        ui_console.log("COMPAT: calculating height")
        var width = on_calculate_width();
        var height = on_calculate_height();
        $(".browser-compat .height").text(height);
        $(".browser-compat .width").text(width);
        ui_console.log("COMPAT: done");
    },
    setMenuText: function(input) {
        ui_console.log("COMPAT: menu text set:", input);
        $(".browser-compat .prompt").text(repr(input));
    },
    getScreenWidth: function() {
        return parseInt($(".browser-compat .screen-width").val());
    },
    getScreenHeight: function() {
        return parseInt($(".browser-compat .screen-height").val());
    },
    quit: function() {
        ui_console.log("COMPAT: quit attempted");
    },
    setPanelShown: function(shown) {
        ui_console.log("COMPAT: setting panel shown:", shown);
        $(".browser-compat .visibilty").text(repr(shown));
    },
    sendline: function(line) {
        ui_console.log("COMPAT sending line:", line);
        tracker_api.socket.send("" + line + "\n");
    }
}
if (typeof tracker_api === "undefined") {
    tracker_api = tracker_api_browser;
    ui_console = console;
}
