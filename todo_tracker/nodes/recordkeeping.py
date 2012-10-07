
import re
from datetime import datetime

from todo_tracker import timefmt
from todo_tracker.tracker import Tree, nodecreator
from todo_tracker.exceptions import LoadError

@nodecreator("fitness log")
class FitnessLog(Tree):
    toplevel = True
    allowed_children = ["weight", "waist", "cals", "workout", "_"]

    def load_finished(self):
        self.tracker.fitness_log = self

class FitnessLogNode(Tree):
    children_of = ["fitness log"]
    allowed_children = []
    preferred_parent = ["fitness log"]
    options = (
        ("time", timefmt.datetime_option),
    )


def full_match(regex, *args):
    return re.match(regex+"$", *args)

class Measurement(FitnessLogNode):
    value = None
    regex = None
    format = None

    def __init__(self, *args, **kw):
        setattr(self, self.value, None)
        self.clothes = None

        super(Measurement, self).__init__(*args, **kw)

    @property
    def text(self):
        value = getattr(self, self.value)
        if value is None:
            return None

        result = self.format % value
        if self.clothes:
            result += " wearing %s" % self.clothes
        return result

    @text.setter
    def text(self, newtext):
        self.time = datetime.now()

        match = full_match(self.regex + r'(?: wearing (.+))?', newtext.strip(), re.IGNORECASE)
        if match:
            value = float(match.group(1))
            setattr(self, self.value, value)
            clothes = match.group(2)
            if clothes and clothes.strip():
                self.clothes = clothes.strip()
            else:
                self.clothes = None
        else:
            raise LoadError("Bad %s format: %r" % (self.value, newtext))

@nodecreator("weight")
class Weight(Measurement):
    regex = (r'([0-9.]+)'
            r'(?:\s*lbs)?')
    format = "%.03flbs"
    value = "weight"

@nodecreator("waist")
class Waist(Measurement):
    regex = (r'([0-9.]+)'
            r'(?:\s*(?:in|inch|inches|"))?')
    format = "%.03fin"
    value = "waist"

class Calories(object):
    pass

class Workout(object):
    pass
