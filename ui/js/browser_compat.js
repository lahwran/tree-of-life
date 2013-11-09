function __delaycall(data, amount) {
    setTimeout(function() {
        on_message_received(data);
    }, amount);
}
tracker_api_browser = {
    connect: function() {
        ui_console.log("COMPAT: connecting");
        _handlers.browser_compat_mode();

        tracker_api.socket = new WebSocket("ws://localhost:18083");

        tracker_api.socket.onopen = function(event) {
            tracker_api._data = "";
            tracker_api.socket.onmessage = function(event) {
                if (event.data === undefined) return;
                tracker_api._data += event.data;
                var index = 0;
                var pattern = /^([^\n]*\n)(.*)$/;
                while (true) {
                    var match = pattern.exec(tracker_api._data)
                    if (!match) return;
                    tracker_api._data = match[2];
                    __delaycall(match[1], index);
                    index += 1;
                }
            }

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
    quit: function() {
        ui_console.log("COMPAT: quit attempted");
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

function browser_compat($rootScope) {
    var $scope = $rootScope;
    $scope.browser = {
        signals: [
            "panel_shown",
            "panel_hidden",
            "attempting_reconnect",
            "connected",
            "disconnected"
        ],
        send_signal: function(s) {
            setTimeout(function() {
                var handler = _handlers[s];
                console.log(handler);
                handler();
            }, 1);
        },
        menuTextUnparsed: "no menu text provided yet",
        menuText: ["no menu text provided yet"],
        screenWidth: 1280,
        screenHeight: 1024,
        panelShown: false
    };
    var browser = $scope.browser;

    tracker_api_browser.setMenuText = function(input) {
        browser.menuTextUnparsed = input;
        browser.menuText = JSON.parse(input);
    };
    tracker_api_browser.getScreenWidth = function() {
        return browser.screenWidth;
    };
    tracker_api_browser.getScreenHeight = function() {
        return browser.screenHeight;
    };
    tracker_api_browser.setPanelShown = function(shown) {
        browser.panelShown = shown;
    };
}
