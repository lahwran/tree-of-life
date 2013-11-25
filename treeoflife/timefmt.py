from __future__ import unicode_literals, print_function

import functools

import datetime
from treeoflife.parseutil import Grammar
from ometa.runtime import ParseError


from treeoflife.nodes.node import Option

date_format = "%B %d, %Y"
time_format = "%I:%M:%S %p"
datetime_format = "%s %s" % (date_format, time_format)


class TimeGrammar(Grammar):
    grammar = """
    days_name = ( 'd' ('ay' 's'? )? )
    hours_name = ( 'h' (('ou')? 'r' 's'?)? )
    minutes_name = ( 'm' ('in' ('ute' 's'?)?)? )
    seconds_name = ('s' ('ec' ('ond' 's'?)?)?)

    days_delta = ws number:days ws days_name ','? -> "days", days
    hours_delta = ws number:hours ws hours_name ','? -> "hours", hours
    minutes_delta = ws number:minutes ws minutes_name ','?
            -> "minutes", minutes
    seconds_delta = ws number:seconds ws seconds_name ','?
            -> "seconds", seconds
    timedelta = (
        (   days_delta |
            hours_delta |
            minutes_delta |
            seconds_delta
        )+:result ?(len(dict(result).keys()) == len(result))
        -> datetime.timedelta(**dict(result))
    )

    month = (
        ('jan' 'uary'? -> 1) |
        ('feb' ('r'? 'uary')? -> 2) |
        ('mar' 'ch'? -> 3) |
        ('apr' 'il'? -> 4) |
        ('may' -> 5) |
        ('jun' 'e'? -> 6) |
        ('jul' 'y'? -> 7) |
        ('aug' 'ust'? -> 8) |
        ('sep' ('t' 'ember'?)? -> 9) |
        ('oct' 'ober'? -> 10) |
        ('nov' 'ember'? -> 11) |
        ('dec' 'ember'? -> 12)
    )
    month_optional = month?:result anything* -> result

    date_primary = month:month wss number:day c_wss number:year
            -> year, month, day
    date_tomorrow = 'tomorrow'
            -> (datetime.datetime.now() + datetime.timedelta(days=1)).date()
    date_today = 'today' -> datetime.datetime.now().date()

    date = ((date_primary:d -> datetime.date(*d)) |
           date_tomorrow |
           date_today)

    # time
    time_peak = '12' ':' number_2dg:m (':' number_2dg)?:s (
            (c_wss 'am' -> (0, m, s or 0)) |
            (c_wss 'pm' -> (12, m, s or 0))
    )
    time_morning = number_2dg:h ':' number_2dg:m (':' number_2dg)?:s (
             (c_wss 'pm' ?(h < 12) -> (h + 12, m, s or 0)) |
             (c_wss 'am' ?(h < 12) -> (h, m, s or 0)) |
             ( -> (h, m, s or 0))
    )
    time = (time_peak | time_morning):t -> datetime.time(*t)

    datetime = date:d c_wss time:t -> datetime.datetime.combine(d, t)
    """
    bindings = {
        "datetime": datetime
    }


str_to_timedelta = TimeGrammar.wraprule("timedelta")
str_to_date = TimeGrammar.wraprule("date")
str_to_time = TimeGrammar.wraprule("time")
str_to_datetime = TimeGrammar.wraprule("datetime")


datetime_to_str = lambda dt: dt.strftime(datetime_format)
date_to_str = lambda date: date.strftime(date_format)
time_to_str = lambda time: time.strftime(time_format)


def timedelta_to_str(delta):
    days = delta.days
    hours = int(delta.seconds / 3600)
    minutes = int((delta.seconds / 60) - (hours * 60))
    seconds = int(delta.seconds - (hours * 3600) - (minutes * 60))
    result = []
    if days > 0:
        result.append("%dd" % days)
    if hours > 0:
        result.append("%dh" % hours)
    if minutes > 0:
        result.append("%dm" % minutes)
    if seconds > 0 or not len(result):
        result.append("%ds" % seconds)
    result_str = " ".join(result)
    return result_str

week_length = 7
month_length = 365.0 / 12.0
year_length = 365.25


def approx_delta(cur_date, other_date):
    if other_date == cur_date:
        return 'today'

    delta = other_date - cur_date
    days = abs(delta.days)
    if delta.days == 1:
        return 'tomorrow'
    elif delta.days == -1:
        return 'yesterday'
    elif days < week_length:
        value = days
        unit = 'day'
    elif days < month_length:
        value = float(days) / week_length
        unit = 'week'
    elif days < year_length:
        value = days / month_length
        unit = 'month'
    else:
        value = days / year_length
        unit = 'year'

    value_float = value
    value = int(value)

    # plurals
    if value > 1:
        unit += 's'

    if other_date < cur_date:
        return '%d %s ago' % (value, unit)
    elif value_float == value:
        return '%d %s' % (value, unit)
    else:
        return '%d+ %s' % (value, unit)


class DatetimeOption(Option):
    incoming = staticmethod(str_to_datetime)
    outgoing = staticmethod(datetime_to_str)


class TimedeltaOption(Option):
    incoming = staticmethod(str_to_timedelta)
    outgoing = staticmethod(timedelta_to_str)


class TimeOption(Option):
    incoming = staticmethod(str_to_time)
    outgoing = staticmethod(time_to_str)
