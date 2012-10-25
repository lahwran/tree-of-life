from datetime import datetime, date, time

from crow2.adapterutil import IString

from todo_tracker import timefmt


def test_string_date():
    assert timefmt.str_to_date("June 7, 2012") == date(2012, 6, 7)


class FakeDatetime(object):
    def __init__(self, now):
        self._now = now

    def now(self):
        return self._now


def test_string_tomorrow(monkeypatch):
    monkeypatch.setattr(timefmt, "datetime",
            FakeDatetime(datetime(2012, 6, 7)))
    assert timefmt.str_to_date("tomorrow") == date(2012, 6, 8)


def test_string_today(monkeypatch):
    monkeypatch.setattr(timefmt, "datetime",
            FakeDatetime(datetime(2012, 6, 7)))
    assert timefmt.str_to_date("today") == date(2012, 6, 7)


def test_string_time():
    assert timefmt.str_to_time("10:00 AM") == time(10)


def test_string_datetime():
    target = datetime(2012, 6, 7, 10)
    assert timefmt.str_to_datetime("June 7, 2012 10:00 AM") == target


def test_time_string():
    assert timefmt.time_to_str(time(10)) == "10:00 AM"
