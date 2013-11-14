from todo_tracker.tracker import Tracker


def test_archival():
    tracker = Tracker(False)
    tracker.deserialize("str",
        "archived: task#abcde: test\n"
        "    task#zxcvb: derp\n"
        "        task#qwert: derk\n"
        "    task#hjklo: herp\n"
    )

    assert tracker.serialize("str") == (
        "archived#abcde: task#abcde: test\n"
        "    @_af\n"
        "    archived#zxcvb: task#zxcvb: derp\n"
        "        @_af\n"
        "        archived#qwert: task#qwert: derk\n"
        "            @_af\n"
        "    archived#hjklo: task#hjklo: herp\n"
        "        @_af\n"
    )

    tracker.deserialize("str",
        "unarchive: archived#abcde: task#abcde: test\n"
        "    @_af\n"
        "    archived#zxcvb: task#zxcvb: derp\n"
        "        @_af\n"
        "        archived#qwert: task#qwert: derk\n"
        "            @_af\n"
        "    archived#hjklo: task#hjklo: herp\n"
        "        @_af\n"
    )

    assert tracker.serialize("str") == (
        "task#abcde: test\n"
        "    task#zxcvb: derp\n"
        "        task#qwert: derk\n"
        "    task#hjklo: herp\n"
    )
