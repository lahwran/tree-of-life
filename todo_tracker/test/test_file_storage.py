import pytest

from todo_tracker.file_storage import parse_line
from todo_tracker.tracker import LoadError

class TestParseLine(object):
    def test_basic(self):
        indent, is_metadata, node_type, text = parse_line("category: personal projects")
        assert indent == 0
        assert not is_metadata
        assert node_type == "category"
        assert text == "personal projects"

    def test_indent(self):
        indent, is_metadata, node_type, text = parse_line("    project: todo tracker")
        assert indent == 1
        assert not is_metadata
        assert node_type == "project"
        assert text == "todo tracker"

    def test_notext(self):
        indent, is_metadata, node_type, text = parse_line("        minor tasks")
        assert indent == 2
        assert not is_metadata
        assert node_type == "minor tasks"
        assert text == None

    def test_metadata(self):
        indent, is_metadata, node_type, text = parse_line("    @option: value")
        assert indent == 1
        assert is_metadata
        assert node_type == "option"
        assert text == "value"

    def test_metadata_notext(self):
        indent, is_metadata, node_type, text = parse_line("    @option")
        assert indent == 1
        assert is_metadata
        assert node_type == "option"
        assert text == None

    def test_bad_indentation(self):
        with pytest.raises(LoadError):
            parse_line("  @option")

    def test_no_space(self):
        with pytest.raises(LoadError):
            parse_line("herp:derp")
