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
seconds_name = ws ('s' ('e' 'c' ('o' 'n' 'd' 's'?)?)?)

days_delta = number:days ws days_name ','? ws -> "days", days
hours_delta = number:hours ws hours_name ','? ws -> "hours", hours
minutes_delta = number:minutes ws minutes_name ','? ws -> "minutes", minutes
seconds_delta = number:seconds ws seconds_name ','? ws -> "seconds", seconds

month = (
    ('j' 'a' 'n' ('u' 'a' 'r' 'y')? -> 1) |
    ('f' 'e' 'b' ('r'? 'u' 'a' 'r' 'y')? -> 2) |
    ('m' 'a' 'r' ('c' 'h')? -> 3) |
    ('a' 'p' 'r' ('i' 'l')? -> 4) |
    ('m' 'a' 'y' -> 5) |
    ('j' 'u' 'n' 'e'? -> 6) |
    ('j' 'u' 'l' 'y'? -> 7) |
    ('a' 'u' 'g' ('u' 's' 't')? -> 8) |
    ('s' 'e' 'p' ('t' ('e' 'm' 'b' 'e' 'r')?)? -> 9) |
    ('o' 'c' 't' ('o' 'b' 'e' 'r')? -> 10) |
    ('n' 'o' 'v' ('e' 'm' 'b' 'e' 'r')? -> 11) |
    ('d' 'e' 'c' ('e' 'm' 'b' 'e' 'r')? -> 12)
)
month_optional = month?:result anything* -> result

date_primary = (month:month ' ' number:day ','? ' ' number:year
        -> (year, month, day))
number_twodigit = <digit{1,2}>:ds -> int(ds)

time_peak = ('1' '2' ':' number_twodigit:minute ws (
        ('a' 'm' -> (0, minute)) |
        ('p' 'm' -> (12, minute))
))
time_morning = (number_twodigit:hour ':' number_twodigit:minute (
         (' '+ 'p' 'm' ?(hour < 12) -> (hour + 12, minute)) |
         (' '+ 'a' 'm' ?(hour < 12) -> (hour, minute)) |
         ( -> (hour, minute))
))
time = (time_peak | time_morning):t -> datetime.time(*t)

timedelta = ( ws
    (   days_delta |
        hours_delta |
        minutes_delta |
        seconds_delta
    )+:result ?(len(dict(result).keys()) == len(result))
    -> datetime.timedelta(**dict(result))
)
timedelta_optional = timedelta?:result anything* -> result
""", {"datetime": datetime})


def str_to_timedelta(string):
    return parse_time(string).timedelta_check()


def str_to_date(string):
    if string.lower() == "today":
        return datetime.datetime.now().date()
    if string.lower() == "tomorrow":
        return (datetime.datetime.now() + datetime.timedelta(days=1)).date()
    return datetime.datetime.strptime(string, date_format).date()


def str_to_time(string):
    return datetime.datetime.strptime(string, time_format).time()


def str_to_datetime(string):
    return datetime.datetime.strptime(string, datetime_format)


datetime_to_str = lambda dt: dt.strftime(datetime_format)
date_to_str = lambda date: date.strftime(date_format)
time_to_str = lambda time: time.strftime(time_format)


class DatetimeOption(Option):
    incoming = staticmethod(str_to_datetime)
    outgoing = staticmethod(datetime_to_str)
