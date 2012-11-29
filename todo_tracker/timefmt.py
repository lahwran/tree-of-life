import functools

import datetime
import parsley
from ometa.runtime import ParseError


from todo_tracker.nodes import Option

date_regexes = {
    "%d": "[0-9]+",
    "%Y": "[12][0-9]{3}",
    "%I": "[0-9][0-9]?",
    "%M": "[0-9][0-9]?",
    "%p": "(?i)(?:am|pm)"
}


def to_regex(format):
    for x, y in date_regexes.items():
        format = format.replace(x, y)
    return format


date_format = "%B %d, %Y"
time_format = "%I:%M %p"
datetime_format = "%s %s" % (date_format, time_format)
date_re = to_regex(date_format)
time_re = to_regex(time_format)
datetime_re = to_regex(datetime_format)

parse_time = parsley.makeGrammar("""
number = <digit+>:ds -> int(ds)
ws = ' '*

days_name = ws ( 'd' ('a' 'y' 's'? )? )
hours_name = ws ( 'h' (('o' 'u')? 'r' 's'?)? )
minutes_name = ws ( 'm' ('i' 'n' ('u' 't' 'e' 's'?)?)? )
seconds_name = ws ('s' ('e' 'c' (s('ond') 's'?)?)?)

days_delta = number:days ws days_name ','? ws -> "days", days
hours_delta = number:hours ws hours_name ','? ws -> "hours", hours
minutes_delta = number:minutes ws minutes_name ','? ws -> "minutes", minutes
seconds_delta = number:seconds ws seconds_name ','? ws -> "seconds", seconds

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

number_twodigit = <digit{1,2}>:ds -> int(ds)
c_wss = ','? ' '+
wss = ' '+

date_primary = month:month wss number:day c_wss number:year
        -> year, month, day
date_tomorrow = s('tomorrow')
        -> (datetime.datetime.now() + datetime.timedelta(days=1)).date()
date_today = s('today') -> datetime.datetime.now().date()

date = ((date_primary:d -> datetime.date(*d)) |
       date_tomorrow |
       date_today)
date_or_none = date?:r anything* -> r

# time
time_peak = s('12') ':' number_twodigit:minute c_wss (
        (s('am') -> (0, minute)) |
        (s('pm') -> (12, minute)) )
time_morning = (number_twodigit:hour ':' number_twodigit:minute (
         (wss s('pm') ?(hour < 12) -> (hour + 12, minute)) |
         (wss s('am') ?(hour < 12) -> (hour, minute)) |
         ( -> (hour, minute))
))
time = (time_peak | time_morning):t -> datetime.time(*t)
time_or_none = time?:r anything* -> r

datetime = date:d c_wss time:t -> datetime.datetime.combine(d, t)
datetime_or_none = datetime?:r anything* -> r

timedelta = ( ws
    (   days_delta |
        hours_delta |
        minutes_delta |
        seconds_delta
    )+:result ?(len(dict(result).keys()) == len(result))
    -> datetime.timedelta(**dict(result))
)
timedelta_optional = timedelta?:result anything* -> result


timespan_primary = timedelta:td wss 'after' wss datetime:dt -> (td, dt)
timespan = (timespan_primary):ts -> ts
""", {"datetime": datetime})

str_to_timedelta = lambda s: parse_time(s.lower()).timedelta_or_none()
str_to_date = lambda s: parse_time(s.lower()).date()
str_to_time = lambda s: parse_time(s.lower()).time()


def str_to_datetime(string):
    return datetime.datetime.strptime(string, datetime_format)


datetime_to_str = lambda dt: dt.strftime(datetime_format)
date_to_str = lambda date: date.strftime(date_format)
time_to_str = lambda time: time.strftime(time_format)


class DatetimeOption(Option):
    incoming = staticmethod(str_to_datetime)
    outgoing = staticmethod(datetime_to_str)
