//import ceylon.time { systemTime }
import org.uncommons.watchmaker.framework.selection { RankSelection }


shared void run() {
    for (x in 1..100) {
        //value start = systemTime.instant();
        value route = calculateShortestRoute {
            cities = europeanDistanceLookup.knownCities;
            distances = europeanDistanceLookup;
            selectionStrategy = RankSelection();
            populationSize = 300;
            eliteCount = 50;
            generationCount = 90;
        };
        //value delta = systemTime.instant() - start;

        value fitness = europeanDistanceLookup.routeLength(route);
        value cityCount = route.size;
        print("Fitness: ``fitness``");
    }
}
