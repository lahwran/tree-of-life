import ceylon.time { systemTime }
import org.uncommons.watchmaker.framework.selection { RankSelection }


shared void run(Anything(String) log=print, Integer n=1000) {
    for (x in 1..n) {
        value start = systemTime.milliseconds();
        value route = calculateShortestRoute {
            cities = europeanDistanceLookup.knownCities;
            distances = europeanDistanceLookup;
            selectionStrategy = RankSelection();
            populationSize = 300;
            eliteCount = 50;
            generationCount = 90;
        };
        value delta = systemTime.milliseconds() - start;

        value fitness = europeanDistanceLookup.routeLength(route);
        value cityCount = route.size;
        log("Fitness: ``fitness`` - delta: ``delta``ms");
    }
}
