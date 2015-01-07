import ceylon.time { Instant, dateTime, DateTime, Duration }

shared void run() {
    value time1 = dateTime(2015, 1, 4, 14, 14).instant();
    value time2 = dateTime(2015, 1, 4, 14, 58).instant();
    Duration d = time1.durationTo(time2);
    print(d);
}
