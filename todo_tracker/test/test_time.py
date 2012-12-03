import datetime
real_datetime = datetime.datetime

from ometa.runtime import ParseError
import pytest

from todo_tracker import timefmt


def test_string_date():
    assert timefmt.str_to_date("june 7, 2012") == datetime.date(2012, 6, 7)


def fakedatetime(*args, **kwargs):
    class Datetime(real_datetime):
        _now = real_datetime(*args, **kwargs)

        @classmethod
        def now(cls):
            return cls._now

    return Datetime


def test_string_tomorrow(monkeypatch):
    monkeypatch.setattr(datetime, "datetime", fakedatetime(2012, 6, 7))
    assert timefmt.str_to_date("tomorrow") == datetime.date(2012, 6, 8)


def test_string_today(monkeypatch):
    monkeypatch.setattr(datetime, "datetime", fakedatetime(2012, 6, 7))
    assert timefmt.str_to_date("today") == datetime.date(2012, 6, 7)


def test_string_time():
    assert timefmt.str_to_time("10:00 AM") == datetime.time(10)


def test_string_datetime():
    target = datetime.datetime(2012, 6, 7, 10)
    assert timefmt.str_to_datetime("june 7, 2012 10:00 AM") == target


def test_time_string():
    assert timefmt.time_to_str(datetime.time(10)) == "10:00:00 AM"


class TestParsers(object):
    def test_months(self):
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("Marceh"   ).month()
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("Apiril"   ).month()
        assert timefmt.TimeGrammar("Apiril").month_optional() is None
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("janruary").month()
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("ferbuary").month()

        assert timefmt.TimeGrammar("jan"      ).month() == 1
        assert timefmt.TimeGrammar("january"  ).month() == 1
        assert timefmt.TimeGrammar("January"  ).month() == 1
        assert timefmt.TimeGrammar("feb"      ).month() == 2
        assert timefmt.TimeGrammar("febuary"  ).month() == 2  # misspelling
        assert timefmt.TimeGrammar("february" ).month() == 2
        assert timefmt.TimeGrammar("February" ).month() == 2
        assert timefmt.TimeGrammar("mar"      ).month() == 3
        assert timefmt.TimeGrammar("march"    ).month() == 3
        assert timefmt.TimeGrammar("March"    ).month() == 3
        assert timefmt.TimeGrammar("apr"      ).month_optional() == 4
        assert timefmt.TimeGrammar("april"    ).month() == 4
        assert timefmt.TimeGrammar("apr"      ).month() == 4
        assert timefmt.TimeGrammar("may"      ).month() == 5
        assert timefmt.TimeGrammar("jun"      ).month() == 6
        assert timefmt.TimeGrammar("june"     ).month() == 6
        assert timefmt.TimeGrammar("jul"      ).month() == 7
        assert timefmt.TimeGrammar("july"     ).month() == 7
        assert timefmt.TimeGrammar("august"   ).month() == 8
        assert timefmt.TimeGrammar("aug"      ).month() == 8
        assert timefmt.TimeGrammar("sep"      ).month() == 9
        assert timefmt.TimeGrammar("sept"     ).month() == 9
        assert timefmt.TimeGrammar("september").month() == 9
        assert timefmt.TimeGrammar("oct"      ).month() == 10
        assert timefmt.TimeGrammar("october"  ).month() == 10
        assert timefmt.TimeGrammar("nov"      ).month() == 11
        assert timefmt.TimeGrammar("november" ).month() == 11
        assert timefmt.TimeGrammar("dec"      ).month() == 12
        assert timefmt.TimeGrammar("december" ).month() == 12

    def test_time(self):
        assert timefmt.TimeGrammar("12:00 am").time() == datetime.time(0, 0)
        assert timefmt.TimeGrammar("00:00 am").time() == datetime.time(0, 0)
        assert timefmt.TimeGrammar("00:00"   ).time() == datetime.time(0, 0)
        assert timefmt.TimeGrammar("1:00 am" ).time() == datetime.time(1, 0)
        assert timefmt.TimeGrammar("1:00"    ).time() == datetime.time(1, 0)
        assert timefmt.TimeGrammar("01:00"   ).time() == datetime.time(1, 0)
        assert timefmt.TimeGrammar("09:00"   ).time() == datetime.time(9, 0)

        with pytest.raises(ParseError):
            timefmt.TimeGrammar("13:00 am").time()
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("13:00 pm").time()
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("1300").time()
        with pytest.raises(ParseError):
            timefmt.TimeGrammar("1300").time()

        assert timefmt.TimeGrammar("12:00"   ).time() == datetime.time(12, 0)
        assert timefmt.TimeGrammar("12:00 pm").time() == datetime.time(12, 0)
        assert timefmt.TimeGrammar("00:00 pm").time() == datetime.time(12, 0)
        assert timefmt.TimeGrammar("01:00 pm").time() == datetime.time(13, 0)
        assert timefmt.TimeGrammar("13:00"   ).time() == datetime.time(13, 0)
