from __future__ import unicode_literals, print_function

from treeoflife.tracker import Tracker


def test_archival():
    tracker = Tracker(False)
    tracker.deserialize({"life":
        "archived: task#abcde: \xfctest\n"
        "    task#zxcvb: \xfcderp\n"
        "        task#qwert: \xfcderk\n"
        "    task#hjklo: \xfcherp\n"
    })

    assert tracker.serialize()["life"] == (
        "archived#abcde: task#abcde: \xfctest\n"
        "    @_af\n"
        "    archived#zxcvb: task#zxcvb: \xfcderp\n"
        "        @_af\n"
        "        archived#qwert: task#qwert: \xfcderk\n"
        "            @_af\n"
        "    archived#hjklo: task#hjklo: \xfcherp\n"
        "        @_af\n"
    )

    tracker.deserialize({"life":
        "unarchive: archived#abcde: task#abcde: \xfctest\n"
        "    @_af\n"
        "    archived#zxcvb: task#zxcvb: \xfcderp\n"
        "        @_af\n"
        "        archived#qwert: task#qwert: \xfcderk\n"
        "            @_af\n"
        "    archived#hjklo: task#hjklo: \xfcherp\n"
        "        @_af\n"
    })

    assert tracker.serialize()["life"] == (
        "task#abcde: \xfctest\n"
        "    task#zxcvb: \xfcderp\n"
        "        task#qwert: \xfcderk\n"
        "    task#hjklo: \xfcherp\n"
    )
