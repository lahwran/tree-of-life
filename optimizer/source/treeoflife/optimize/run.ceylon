import ceylon.time { systemTime }
import org.uncommons.watchmaker.framework.selection { RankSelection }


shared void run(Anything(String) log=print) {
    for (x in 1..1000) {
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
