from datetime import datetime, date, time, timedelta

from zope.interface import Interface, implementer
from crow2.adapterutil import register, adapter_for, IString

date_format = "%B %d, %Y"
time_format = "%I:%M %p"
datetime_format = "%s %s" % (date_format, time_format)

class IDate(Interface):
    "datetime.date"

class ITime(Interface):
    "datetime.time"

class IDateTime(Interface):
    "datetime.datetime"

class IEstimatedDatetime(Interface):
    pass

@adapter_for(IString, IDate)
def adapt(string):
    if string.lower() == "today":
        return datetime.now().date()
    if string.lower() == "tomorrow":
        return (datetime.now() + timedelta(days=1)).date()
    return datetime.strptime(string, date_format).date()
register(lambda string: datetime.strptime(string, time_format).time(), IString, ITime)
register(lambda string: datetime.strptime(string, datetime_format), IString, IDateTime)

register(lambda dt: dt.strftime(datetime_format), datetime, IString)
register(lambda date: date.strftime(date_format), date, IString)
register(lambda time: time.strftime(time_format), time, IString)
