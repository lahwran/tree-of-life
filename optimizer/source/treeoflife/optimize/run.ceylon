import org.uncommons.watchmaker.framework.selection { RankSelection }
shared void run() {
    print("Starting...");
    value route = calculateShortestRoute {
        cities = europeanDistanceLookup.knownCities;
        distances = europeanDistanceLookup;
        selectionStrategy = RankSelection();
        populationSize = 300;
        eliteCount = 50;
        generationCount = 90;
        crossover = true;
        mutation = true;
    };
    print("Done. Best route:");
    value fitness = europeanDistanceLookup.routeLength(route);
    value cityCount = route.size();
    for (i in 0..cityCount-1) {
       print(route.get(i));
    }
    print("-----------------");
    print("Fitness: ``fitness``");
}
