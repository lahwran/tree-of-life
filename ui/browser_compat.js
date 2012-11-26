tracker_api_browser = {
    connect: function() {
        ui_console.log("COMPAT: connecting");
        $(".browser-compat").show();
        $(".command-box .input").addClass("taller");

        on_message_received(JSON.stringify({
            status: "vim running",
            tree: [
                {"text": "herp derp", "type": "task", "options": [{"text": "November 11, 2012 03:24 PM", "type": "started"}], "children": [
                {"text": "test", "type": "task", "options": [{"text": "November 11, 2012 03:24 PM", "type": "started"}]}]}, {"text": "queue", "type": "category", "children": [
                {"text": "herp", "type": "task"}, {"text": "derp", "type": "task"}]}, {"text": null, "type": "days", "children": [
                {"text": "October 07, 2012", "type": "day", "options": [{"text": "October 07, 2012 04:35 PM", "type": "started"}]}, {"text": "October 08, 2012", "type": "day", "options": [{"text": "October 08, 2012 11:31 AM", "type": "started"}]}, {"text": "October 13, 2012", "type": "day", "options": [{"text": "October 13, 2012 06:38 PM", "type": "started"}]}, {"text": "October 14, 2012", "type": "day", "options": [{"text": "October 14, 2012 01:09 AM", "type": "started"}]}, {"text": "October 19, 2012", "type": "day", "options": [{"text": "October 19, 2012 10:51 AM", "type": "started"}]}, {"text": "October 20, 2012", "type": "day", "options": [{"text": "October 20, 2012 04:56 PM", "type": "started"}]}, {"text": "October 24, 2012", "type": "day", "options": [{"text": "October 24, 2012 06:54 PM", "type": "started"}, {"text": null, "type": "active"}], "children": [
                {"text": "test", "type": "task", "options": [{"text": "October 24, 2012 06:55 PM", "type": "started"}, {"text": "October 24, 2012 06:55 PM", "type": "finished"}]}]}, {"text": "October 25, 2012", "type": "day", "options": [{"text": "October 25, 2012 10:18 AM", "type": "started"}]}, {"text": "November 02, 2012", "type": "day", "options": [{"text": "November 02, 2012 11:11 PM", "type": "started"}, {"text": null, "type": "active"}]}, {"text": "November 04, 2012", "type": "day", "options": [{"text": "November 04, 2012 11:32 AM", "type": "started"}], "children":
                [{"text": "some thing", "type": "task", "options": [{"text": "November 04, 2012 07:34 PM", "type": "started"}], "children":
                [{"text": "active task", "type": "task", "options": [{"text": "November 04, 2012 07:34 PM", "type": "started"}]}]}, {"text": "some task that has to be started in 10 minutes, and needs 15 minutes to prepare", "type": "task"}]}, {"text": "November 11, 2012", "type": "day", "options": [{"text": "November 11, 2012 02:35 PM", "type": "started"}], "children":
                [{"text": "herp derp", "type": "work on", "options": [{"text": "November 11, 2012 03:24 PM", "type": "started"}], "children":
                [{"text": "test", "type": "work on"}]}, {"text": "test", "type": "task", "options": [{"text": "November 11, 2012 03:24 PM", "type": "started"}, {"text": "November 11, 2012 03:24 PM", "type": "finished"}]}]}, {"text": "November 13, 2012", "type": "day", "options": [{"text": "November 13, 2012 08:44 AM", "type": "started"}]}, {"text": "November 16, 2012", "type": "day", "options": [{"text": "November 16, 2012 11:03 AM", "type": "started"}, {"text": null, "type": "active"}]}, {"text": "November 19, 2012", "type": "day", "options": [{"text": "November 19, 2012 12:31 PM", "type": "started"}, {"text": null, "type": "active"}]}, {"text": "November 20, 2012", "type": "day", "options": [{"text": "November 20, 2012 10:14 AM", "type": "started"}, {"text": null, "type": "active"}]}, {"text": "November 21, 2012", "type": "day", "options": [{"text": "November 21, 2012 09:55 AM", "type": "started"}, {"text": null, "type": "active"}], "children":
                [{"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "tset", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}, {"text": "test", "type": "task"}]}, {"text": "November 22, 2012", "type": "day", "options": [{"text": "November 22, 2012 03:35 PM", "type": "started"}], "children":
                [{"text": "test", "type": "task", "options": [{"text": "November 22, 2012 03:35 PM", "type": "started"}]}]}, {"text": "November 23, 2012", "type": "day", "options": [{"text": "November 23, 2012 03:05 AM", "type": "started"}, {"text": null, "type": "active"}], "children":
                [{"text": null, "type": "todo review"}]}]}, {"text": null, "type": "todo bucket", "children":
                [{"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}, {"text": "test", "type": "todo"}]}, {"text": null, "type": "fitness log", "children":
                [{"text": "10.000lbs", "type": "weight", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}, {"text": "10.000in", "type": "waist", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}, {"text": "10min", "type": "workout", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}, {"text": "10", "type": "calories", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}, {"text": "test", "type": "log", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}, {"text": "10 from coding", "type": "calories", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}, {"text": "1000 from eating my computer", "type": "calories", "options": [{"text": "October 08, 2012 10:46 PM", "type": "time"}]}]}],
            prompt: ["days", "day: today", "task: herp"]
        }));
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
    }
}
if (typeof tracker_api === "undefined") {
    tracker_api = tracker_api_browser;
    ui_console = console;
}
