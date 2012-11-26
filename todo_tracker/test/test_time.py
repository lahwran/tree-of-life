import datetime

from ometa.runtime import ParseError
import pytest

from todo_tracker import timefmt


def test_string_date():
    assert timefmt.str_to_date("June 7, 2012") == datetime.date(2012, 6, 7)


class _FakeDatetime(object):
    def __init__(self, *args, **kwargs):
        self._now = datetime.datetime(*args, **kwargs)

    def now(self):
        return self._now


def test_string_tomorrow(monkeypatch):
    monkeypatch.setattr(datetime, "datetime", _FakeDatetime(2012, 6, 7))
    assert timefmt.str_to_date("tomorrow") == datetime.date(2012, 6, 8)


def test_string_today(monkeypatch):
    monkeypatch.setattr(datetime, "datetime", _FakeDatetime(2012, 6, 7))
    assert timefmt.str_to_date("today") == datetime.date(2012, 6, 7)


def test_string_time():
    assert timefmt.str_to_time("10:00 AM") == datetime.time(10)


def test_string_datetime():
    target = datetime.datetime(2012, 6, 7, 10)
    assert timefmt.str_to_datetime("June 7, 2012 10:00 AM") == target


def test_time_string():
    assert timefmt.time_to_str(datetime.time(10)) == "10:00 AM"


class TestParsers(object):
    def test_months(self):
        with pytest.raises(ParseError):
            timefmt.parse_time("March"   ).month()
        with pytest.raises(ParseError):
            timefmt.parse_time("April"   ).month()
        assert timefmt.parse_time("April").month_optional() is None
        with pytest.raises(ParseError):
            timefmt.parse_time("janruary").month()
        with pytest.raises(ParseError):
            timefmt.parse_time("ferbuary").month()

        assert timefmt.parse_time("jan"      ).month() == 1
        assert timefmt.parse_time("january"  ).month() == 1
        assert timefmt.parse_time("feb"      ).month() == 2
        assert timefmt.parse_time("febuary"  ).month() == 2  # misspelling case
        assert timefmt.parse_time("february" ).month() == 2
        assert timefmt.parse_time("mar"      ).month() == 3
        assert timefmt.parse_time("march"    ).month() == 3
        assert timefmt.parse_time("apr"      ).month_optional() == 4
        assert timefmt.parse_time("april"    ).month() == 4
        assert timefmt.parse_time("apr"      ).month() == 4
        assert timefmt.parse_time("may"      ).month() == 5
        assert timefmt.parse_time("jun"      ).month() == 6
        assert timefmt.parse_time("june"     ).month() == 6
        assert timefmt.parse_time("jul"      ).month() == 7
        assert timefmt.parse_time("july"     ).month() == 7
        assert timefmt.parse_time("august"   ).month() == 8
        assert timefmt.parse_time("aug"      ).month() == 8
        assert timefmt.parse_time("sep"      ).month() == 9
        assert timefmt.parse_time("sept"     ).month() == 9
        assert timefmt.parse_time("september").month() == 9
        assert timefmt.parse_time("oct"      ).month() == 10
        assert timefmt.parse_time("october"  ).month() == 10
        assert timefmt.parse_time("nov"      ).month() == 11
        assert timefmt.parse_time("november" ).month() == 11
        assert timefmt.parse_time("dec"      ).month() == 12
        assert timefmt.parse_time("december" ).month() == 12

    def test_time(self):
        assert timefmt.parse_time("12:00 am").time() == datetime.time(0, 0)
        assert timefmt.parse_time("00:00 am").time() == datetime.time(0, 0)
        assert timefmt.parse_time("00:00"   ).time() == datetime.time(0, 0)
        assert timefmt.parse_time("1:00 am" ).time() == datetime.time(1, 0)
        assert timefmt.parse_time("1:00"    ).time() == datetime.time(1, 0)
        assert timefmt.parse_time("01:00"   ).time() == datetime.time(1, 0)
        assert timefmt.parse_time("09:00"   ).time() == datetime.time(9, 0)

        with pytest.raises(ParseError):
            timefmt.parse_time("13:00 am").time()
        with pytest.raises(ParseError):
            timefmt.parse_time("13:00 pm").time()
        with pytest.raises(ParseError):
            timefmt.parse_time("1300").time()
        with pytest.raises(ParseError):
            timefmt.parse_time("1300").time()

        assert timefmt.parse_time("12:00"   ).time() == datetime.time(12, 0)
        assert timefmt.parse_time("12:00 pm").time() == datetime.time(12, 0)
        assert timefmt.parse_time("00:00 pm").time() == datetime.time(12, 0)
        assert timefmt.parse_time("01:00 pm").time() == datetime.time(13, 0)
        assert timefmt.parse_time("13:00"   ).time() == datetime.time(13, 0)
