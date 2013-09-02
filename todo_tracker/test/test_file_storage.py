import pytest

from todo_tracker.file_storage import parse_line
from todo_tracker.tracker import LoadError


class TestParseLine(object):
    def test_basic(self):
        line = "category: personal projects"
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_type == "category"
        assert text == "personal projects"

    def test_indent(self):
        line = "    project: todo tracker"
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 1
        assert not is_metadata
        assert node_type == "project"
        assert text == "todo tracker"

    def test_empty_line(self):
        line = ""
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_type == ""
        assert text is None

    def test_empty_line_indent(self):
        line = "      "
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 0
        assert not is_metadata
        assert node_type == ""
        assert text is None

    def test_notext(self):
        line = "        minor tasks"
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 2
        assert not is_metadata
        assert node_type == "minor tasks"
        assert text is None

    def test_metadata(self):
        line = "    @option: value"
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 1
        assert is_metadata
        assert node_type == "option"
        assert text == "value"

    def test_metadata_notext(self):
        line = "    @option"
        indent, is_metadata, node_type, text = parse_line(line)
        assert indent == 1
        assert is_metadata
        assert node_type == "option"
        assert text is None

    def test_bad_indentation(self):
        with pytest.raises(LoadError):
            parse_line("  @option")

    def test_no_space(self):
        with pytest.raises(LoadError):
            parse_line("herp:derp")
