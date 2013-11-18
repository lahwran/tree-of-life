from __future__ import unicode_literals, print_function

import pytest

from todo_tracker.file_storage import parse_line
from todo_tracker.tracker import LoadError


class TestParseLine(object):
    def test_basic(self):
        line = u"\xfccategory: \xfcpersonal \xfcprojects"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_id is None
        assert node_type == u"\xfccategory"
        assert text == u"\xfcpersonal \xfcprojects"

    def test_basic_nodeid(self):
        line = u"\xfccategory#asdfg: \xfcpersonal \xfcprojects"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_id == u"asdfg"
        assert node_type == u"\xfccategory"
        assert text == u"\xfcpersonal \xfcprojects"

    def test_indent(self):
        line = u"    \xfcproject: \xfctodo \xfctracker"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 1
        assert not is_metadata
        assert node_id is None
        assert node_type == u"\xfcproject"
        assert text == u"\xfctodo \xfctracker"

    def test_indent_id(self):
        line = u"    \xfcproject#hjklo: \xfctodo \xfctracker"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 1
        assert not is_metadata
        assert node_id == u"hjklo"
        assert node_type == u"\xfcproject"
        assert text == u"\xfctodo \xfctracker"

    def test_empty_line(self):
        line = u""
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_id is None
        assert node_type == u""
        assert text is None

    def test_empty_line_indent(self):
        line = u"      "
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_id is None
        assert node_type == u""
        assert text is None

    def test_notext(self):
        line = u"        minor\xfc tasks"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 2
        assert not is_metadata
        assert node_id is None
        assert node_type == u"minor\xfc tasks"
        assert text is None

    def test_notext_id(self):
        line = u"        minor\xfc tasks#abcde"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 2
        assert not is_metadata
        assert node_id == u"abcde"
        assert node_type == u"minor\xfc tasks"
        assert text is None

    def test_metadata(self):
        line = u"    @option\xfc: \xfcvalue"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 1
        assert is_metadata
        assert node_id is None
        assert node_type == u"option\xfc"
        assert text == u"\xfcvalue"

    def test_metadata_notext(self):
        line = u"    @option\xfc"
        indent, is_metadata, node_id, node_type, text = parse_line(line)
        assert indent == 1
        assert is_metadata
        assert node_id is None
        assert node_type == u"option\xfc"
        assert text is None

    def test_bad_node_id(self):
        with pytest.raises(LoadError):
            parse_line(u"    option#longid: derp")
        with pytest.raises(LoadError):
            parse_line(u"    option#shrt: derp")

        with pytest.raises(LoadError):
            # invalid characters
            parse_line(u"    option#-----: derp")

    def test_metadata_node_id(self):
        with pytest.raises(LoadError):
            parse_line(u"    @option#badid: derp")

    def test_bad_indentation(self):
        with pytest.raises(LoadError):
            parse_line(u"  @option")

    def test_no_space(self):
        with pytest.raises(LoadError):
            parse_line(u"herp:derp")

    def test_non_unicode(self):
        with pytest.raises(AssertionError):
            parse_line(b"herp: derp")
