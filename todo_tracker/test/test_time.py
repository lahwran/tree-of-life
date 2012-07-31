from datetime import datetime, date, time

from crow2.adapterutil import IString

from todo_tracker import time as target

def test_string_date():
    assert target.IDate("June 7, 2012") == date(2012, 6, 7)

class FakeDatetime(object):
    def __init__(self, now):
        self._now = now

    def now(self):
        return self._now

def test_string_tomorrow(monkeypatch):
    monkeypatch.setattr(target, "datetime", FakeDatetime(datetime(2012, 6, 7)))
    assert target.IDate("tomorrow") == date(2012, 6, 8)

def test_string_today(monkeypatch):
    monkeypatch.setattr(target, "datetime", FakeDatetime(datetime(2012, 6, 7)))
    assert target.IDate("today") == date(2012, 6, 7)

def test_string_time():
    assert target.ITime("10:00 AM") == time(10)

def test_string_datetime():
    assert target.IDateTime("June 7, 2012 10:00 AM") == datetime(2012, 6, 7, 10)

def test_time_string():
    assert IString(time(10)) == "10:00 AM"
