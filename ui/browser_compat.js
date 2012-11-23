tracker_api_browser = {
    connect: function() {
        console.log("COMPAT: connecting");
        $(".browser-compat").show();
        $(".command-box .input").addClass("taller");

        on_message_received(JSON.stringify({
            suggestions: ["vim running"],
            messages: [
                "todo: herp",
                "todo: derp"
            ],
            context: [
                "  days",
                "      day: today",
                ">         task: herp",
                "          task: derp",
            ],
            prompt: ["days", "day: today", "task: herp"]
        }));
    },
    resize: function() {
        console.log("COMPAT: calculating height")
        var width = on_calculate_width();
        var height = on_calculate_height();
        $(".browser-compat .height").text(height);
        $(".browser-compat .width").text(width);
        console.log("COMPAT: done");
    },
    setMenuText: function(input) {
        console.log("COMPAT: menu text set:", input);
        $(".browser-compat .prompt").text(repr(input));
    },
    getScreenWidth: function() {
        return parseInt($(".browser-compat .screen-width").val());
    },
    getScreenHeight: function() {
        return parseInt($(".browser-compat .screen-height").val());
    },
    quit: function() {
        console.log("COMPAT: quit attempted");
    },
    setPanelShown: function(shown) {
        console.log("COMPAT: setting panel shown:", shown);
        $(".browser-compat .visibilty").text(repr(shown));
    },
    sendline: function(line) {
        console.log("COMPAT sending line:", line);
    }
}
if (typeof tracker_api === "undefined") {
    tracker_api = tracker_api_browser;
}
