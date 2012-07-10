import pytest

from todo_tracker.tracker import parse_line, Tracker, Tree, LoadError

class StubTree(Tree):
    def setoption(self, option, value):
        self.metadata[option] = value

    def continue_text(self, text):

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

class TestTrackerLoad(object):
    def test_basic(self):
        class FakeNodeCreator(object):
            def create(self, node_type, text, parent):
                return Tree(node_type, text, parent)

        tracker_obj = Tracker(nodecreator=FakeNodeCreator())
        lines = [
            "firstchild: args",
            "    secondchild: other args\n",
            "        @option: data",
            "        thirdchild: herp derp\n",
            "    fourthchild: ark dark"
        ]
        tracker_obj.load(lines)

        root = tracker_obj.root
        assert root.children[0].text == "args"
        assert root.children[0].node_type == "firstchild"

        assert root.children[0].children[0].text == "other args"
        assert root.children[0].children[0].node_type == "secondchild"
        assert root.children[0].children[0].metadata["option"] == "data"

        assert root.children[0].children[0].children[0].text == "herp derp"
        assert root.children[0].children[0].children[0].node_type == "thirdchild"

        assert root.children[0].children[1].text == "ark dark"
        assert root.children[0].children[1].node_type == "fourthchild"

    def test_bad_order(self):
        class FakeNodeCreator(object):
            def create(self, node_type, text, parent):
                return Tree(node_type, text, parent)

        tracker_obj = Tracker(nodecreator=FakeNodeCreator())

        lines = [
            "firstchild: args",
            "    secondchild: other args",
            "    @option: this won't work here"
        ]
        with pytest.raises(LoadError):
            tracker_obj.load(lines)

    def test_continued_text(self):
        tracker_obj = Tracker()
        lines = [
            "category: derp",
            "    - herp",
            "    - derp"
        ]
        tracker_obj.load(lines)

class TestTrackerSave(object):
    def test_basic(self):
        tracker = Tracker()

        node1 = Tree("node1", "node1_text", tracker.root)
        tracker.root.addchild(node1)
        node2 = Tree("node2", "node2_text", tracker.root)
        tracker.root.addchild(node2)
        node3 = Tree("node3", None, tracker.root)
        tracker.root.addchild(node3)

        node1_1 = Tree("node1_1", "node1_1_text", node1)
        node1_1.setoption("herp", "derp")
        node1.addchild(node1_1)

        node1_2 = Tree("node1_2", "node1_2_text", node1)
        node1_2.continue_text("herk derk")
        node1.addchild(node1_2)

        node2_1 = Tree("node2_1", "node2_1_text", node2)
        node2_1.setoption("hark", "dark")
        node2_1.continue_text('honk donk')
        node2.addchild(node2_1)

        class WriteTarget(object):
            def __init__(self):
                self.text = ""

            def write(self, text):
                self.text = text

        target = WriteTarget()
        tracker.save(target)
        assert target.text == (
            "node1: node1_text\n"
            "    node1_1: node1_1_text\n"
            "        @herp: derp\n"
            "    node1_2: node1_2_text\n"
            "        - herk derk\n"
            "node2: node2_text\n"
            "    node2_1: node2_1_text\n"
            "        - honk donk\n"
            "        @hark: dark\n"
            "node3"
        )


