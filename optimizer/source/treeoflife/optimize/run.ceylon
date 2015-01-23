import ceylon.time { systemTime, dateTime }
import org.uncommons.watchmaker.framework.selection { RankSelection }


shared void run(Anything(String) log=print, Integer n=1000) {
    value start = systemTime.milliseconds();
    value params = ScheduleParams(testtree,
            dateTime(2015, 1, 1, 11, 00).instant());
    value result = evolveSchedule {
        params = params;
        selectionStrategy = RankSelection();
        populationSize = 300;
        eliteCount = 50;
        generationCount = 90;
    };
    value delta = systemTime.milliseconds() - start;

    value f = fitness(params, result);
    log("Result: ``result``");
    log("Fitness: ``f`` - delta: ``delta``ms");
}
