import functools

import datetime
from ometa.runtime import ParseError
from todo_tracker.parseutil import Grammar


from todo_tracker.nodes import Option

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
    accuracy_delta = str_to_timedelta(result_str) - delta
    minimum = datetime.timedelta(seconds=-1)
    maximum = datetime.timedelta(seconds=1)
    assert minimum < accuracy_delta < maximum, "%r != %r" % (result_str,
            delta)
    return result_str


class DatetimeOption(Option):
    incoming = staticmethod(str_to_datetime)
    outgoing = staticmethod(datetime_to_str)
