
import re
from datetime import datetime

from todo_tracker import timefmt
from todo_tracker.nodes.node import Node, nodecreator
from todo_tracker.exceptions import LoadError


@nodecreator("fitness log")
class FitnessLog(Node):
    toplevel = True
    allowed_children = ["weight", "waist", "calories", "workout", "_", "log"]

    def load_finished(self):
        self.root.fitness_log = self

    @classmethod
    def make_skeleton(cls, root):
        root.fitness_log = root.find_one("fitness log")
        if not root.fitness_log:
            root.fitness_log = root.createchild("fitness log")


def full_match(regex, *args):
    return re.match(regex + "$", *args)


# TODO: these names are a little wonky
@nodecreator("log")
class LogNode(Node):
    children_of = ["fitness log"]
    allowed_children = []
    preferred_parent = "< :{last} > fitness log"

    options = (
        timefmt.DatetimeOption("time"),
    )

    def __init__(self, *args, **kw):
        self.time = datetime.now()
        super(LogNode, self).__init__(*args, **kw)


class FitnessLogNode(LogNode):
    value_name = None
    value_format = None
    value_regex = None
    value_type = float

    context_name = None
    context_format = None
    context_regex = "()"

    def __init__(self, *args, **kw):
        setattr(self, self.value_name, None)
        setattr(self, self.context_name, None)

        super(FitnessLogNode, self).__init__(*args, **kw)

    @property
    def text(self):
        value = getattr(self, self.value_name)
        context = getattr(self, self.context_name)
        if value is None:
            return None

        result = self.value_format % value
        if context:
            result += self.context_format % context
        return result

    @text.setter
    def text(self, newtext):
        self.time = datetime.now()

        regex = self.value_regex + (r'(?:%s)?' % self.context_regex)
        match = full_match(regex, newtext.strip(), re.IGNORECASE)
        if match:
            value = self.value_type(match.group(1))
            setattr(self, self.value_name, value)
            context = match.group(2)
            if context and context.strip():
                setattr(self, self.context_name, context.strip())
            else:
                setattr(self, self.context_name, None)
        else:
            raise LoadError("Bad %s or %s format: %r" % (self.value_name,
                self.context_name, newtext))


class Measurement(FitnessLogNode):
    context_name = "clothes"
    context_format = " wearing %s"
    context_regex = " wearing (.+)"


@nodecreator("weight")
class Weight(Measurement):
    value_name = "weight"
    value_format = "%.03flbs"
    value_regex = (r'([0-9.]+)'
            r'(?:\s*lbs)?')


@nodecreator("waist")
class Waist(Measurement):
    value_name = "waist"
    value_format = "%.03fin"
    value_regex = (r'([0-9.]+)'
            r'(?:\s*(?:in|inch|inches|"))?')


@nodecreator("cal")
@nodecreator("cals")
@nodecreator("calories")
class Calories(FitnessLogNode):
    context_name = "food"
    context_format = " from %s"
    context_regex = " from (.+)"

    value_name = "calories"
    value_format = "%d"
    value_regex = r'([0-9]+)'

    def __init__(self, node_type, *args, **kwargs):
        if node_type == "cal" or node_type == "cals":
            node_type = "calories"
        super(Calories, self).__init__(node_type, *args, **kwargs)


@nodecreator("workout")
class Workout(FitnessLogNode):
    context_name = "activity"
    context_format = " %s"
    context_regex = " (.+)"

    value_name = "minutes"
    value_format = "%dmin"
    value_regex = (r'([0-9]+)'
            r'(?:\s*(?:min|minutes))?')


@nodecreator("tzchange")
class TZChangeNode(Node):
    text_required = True
    preferred_parent = None
    children_of = None

    options = (
        timefmt.DatetimeOption("origin_time"),
    )

    def __init__(self, *args, **kw):
        self.origin_time = datetime.now()
        Node.__init__(self, *args, **kw)
