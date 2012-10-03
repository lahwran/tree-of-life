from datetime import datetime, date, time, timedelta

from todo_tracker.tracker import Option

date_format = "%B %d, %Y"
time_format = "%I:%M %p"
datetime_format = "%s %s" % (date_format, time_format)


def str_to_date(string):
    if string.lower() == "today":
        return datetime.now().date()
    if string.lower() == "tomorrow":
        return (datetime.now() + timedelta(days=1)).date()
    return datetime.strptime(string, date_format).date()

str_to_time = lambda string: datetime.strptime(string, time_format).time()
str_to_datetime = lambda string: datetime.strptime(string, datetime_format)

datetime_to_str = lambda dt: dt.strftime(datetime_format)
date_to_str = lambda date: date.strftime(date_format)
time_to_str = lambda time: time.strftime(time_format)

datetime_option = Option(str_to_datetime, datetime_to_str)
