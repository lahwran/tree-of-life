import re

from todo_tracker.tracker import Tracker
from todo_tracker.file_storage import serialize_to_str

from todo_tracker.nodes.recordkeeping import (FitnessLog, Weight,
        Waist, Measurement, full_match)


class SimpleMeasurement(Measurement):
    value_name = "the_value"
    value_regex = "herp (1234) abc"
    value_format = "herp %d abc"


def test_measurement_noclothes():
    tracker = Tracker(skeleton=False)

    fitnesslog = FitnessLog("fitness log", None, tracker.root)
    fitnesslog._validate()
    tracker.root.addchild(fitnesslog)

    measurement = SimpleMeasurement("_", "herp 1234 abc", fitnesslog)
    measurement._validate()
    fitnesslog.addchild(measurement)

    assert measurement.the_value == 1234
    assert measurement.clothes is None


def test_measurement_withclothes():
    tracker = Tracker(skeleton=False)

    fitnesslog = FitnessLog("fitness log", None, tracker.root)
    fitnesslog._validate()
    tracker.root.addchild(fitnesslog)

    measurement = SimpleMeasurement("_",
            "herp 1234 abc wearing an office building", fitnesslog)
    measurement._validate()
    fitnesslog.addchild(measurement)

    assert measurement.the_value == 1234
    assert measurement.clothes == "an office building"


def test_measurement_text():
    tracker = Tracker(skeleton=False)

    fitnesslog = FitnessLog("fitness log", None, tracker.root)
    fitnesslog._validate()
    tracker.root.addchild(fitnesslog)

    measurement = SimpleMeasurement("_", "herp 1234 abc wearing a pot roast",
            fitnesslog)
    measurement._validate()
    fitnesslog.addchild(measurement)

    assert measurement.text == "herp 1234 abc wearing a pot roast"
    measurement.text = measurement.text
    assert measurement.text == "herp 1234 abc wearing a pot roast"


def test_measurement_time():
    tracker = Tracker(skeleton=False)

    fitnesslog = FitnessLog("fitness log", None, tracker.root)
    fitnesslog._validate()
    tracker.root.addchild(fitnesslog)

    measurement = SimpleMeasurement("_", "herp 1234 abc wearing a pot roast",
            fitnesslog)
    measurement._validate()
    fitnesslog.addchild(measurement)

    result = serialize_to_str(measurement, is_root=False)
    assert result.startswith(
        "_: herp 1234 abc wearing a pot roast\n"
        "    @time: "
    )


def test_weight_re():
    assert full_match(Weight.value_regex, "10.5lbs").group(1) == "10.5"
    assert full_match(Weight.value_regex, "10.5 lbs").group(1) == "10.5"
    assert full_match(Weight.value_regex,
            "0123456789.0123456789 lbs").group(1) == "0123456789.0123456789"
    assert full_match(Weight.value_regex, "1 lbs").group(1) == "1"
    assert full_match(Weight.value_regex, "1").group(1) == "1"
    assert full_match(Weight.value_regex, "15.6  lbs").group(1) == "15.6"
    assert not full_match(Weight.value_regex, "1  ")
    assert not full_match(Weight.value_regex, "no numerals")
    assert not full_match(Weight.value_regex, "alpha then numerals 1234")
    assert not full_match(Weight.value_regex, "1234 numerals then alpha")
    assert not full_match(Weight.value_regex, "1234 lbs wearing something")


def test_waist_re():
    assert full_match(Waist.value_regex, "10.5in").group(1) == "10.5"
    assert full_match(Waist.value_regex, "10.5 inches").group(1) == "10.5"
    assert full_match(Waist.value_regex,
            "0123456789.0123456789 inch").group(1) == "0123456789.0123456789"
    assert full_match(Waist.value_regex, "1 inch").group(1) == "1"
    assert full_match(Waist.value_regex, "1").group(1) == "1"
    assert full_match(Waist.value_regex, "15.6  in").group(1) == "15.6"
    assert not full_match(Waist.value_regex, "1  ")
    assert not full_match(Waist.value_regex, "no numerals")
    assert not full_match(Waist.value_regex, "alpha then numerals 1234")
    assert not full_match(Waist.value_regex, "1234 numerals then alpha")
    assert not full_match(Waist.value_regex, "1234 lbs wearing something")
