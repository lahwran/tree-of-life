from __future__ import unicode_literals, print_function

import datetime

from ometa.runtime import ParseError
import pytest

from treeoflife import timefmt


def test_string_date():
    assert timefmt.str_to_date("june 7, 2012") == datetime.date(2012, 6, 7)


def test_string_tomorrow(setdt):
    setdt(2012, 6, 7)
    assert timefmt.str_to_date("tomorrow") == datetime.date(2012, 6, 8)


def test_string_today(setdt):
    setdt(2012, 6, 7)
    assert timefmt.str_to_date("today") == datetime.date(2012, 6, 7)


def test_string_time():
    assert timefmt.str_to_time("10:00 AM") == datetime.time(10)


def test_string_datetime():
    target = datetime.datetime(2012, 6, 7, 10)
    assert timefmt.str_to_datetime("june 7, 2012 10:00 AM") == target


def test_time_string():
    assert timefmt.time_to_str(datetime.time(10)) == "10:00:00 AM"


def test_timedelta_to_str():
    x = datetime.timedelta(days=2, hours=2, minutes=2, seconds=2)
    assert timefmt.str_to_timedelta(timefmt.timedelta_to_str(x)) == x


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


def test_approx_delta():
    now = datetime.date(2012, 12, 26)
    approx_delta = timefmt.approx_delta
    assert approx_delta(now, datetime.date(2012, 12, 31)) == '5 days'
    assert approx_delta(now, datetime.date(2013, 12, 31)) == '1.1 years'
    assert approx_delta(now, datetime.date(2013, 1, 31)) == '1.2 months'
    assert approx_delta(now, datetime.date(2013, 4, 7)) == '3.4 months'
    assert approx_delta(now, datetime.date(2013, 3, 21)) == '2.8 months'
    assert approx_delta(now, datetime.date(2013, 1, 15)) == '2.9 weeks'
    assert approx_delta(now, datetime.date(2012, 12, 27)) == 'tomorrow'
    assert approx_delta(now, datetime.date(2012, 12, 26)) == 'today'
    assert approx_delta(now, datetime.date(2012, 12, 25)) == 'yesterday'
    assert approx_delta(now, datetime.date(2011, 12, 25)) == '1.1 years ago'
    assert approx_delta(now, datetime.date(2011, 12, 26)) == '1.1 years ago'
    # can't get 1 year because 365.25
    assert approx_delta(now, datetime.date(2011, 12, 27)) == '12 months ago'
    assert approx_delta(now, datetime.date(2012, 12, 20)) == '6 days ago'
    assert approx_delta(now, datetime.date(2012, 12, 19)) == '1 week ago'
