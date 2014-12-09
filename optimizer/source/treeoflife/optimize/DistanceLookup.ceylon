import java.util { List }

interface DistanceLookup {
    "The list of cities that this object knows about."
    shared formal Genome knownCities;

     "Look up the distance between two cities in km."
    shared formal Integer getDistance(Gene startingCity,
            Gene destinationCity);

    shared default Float routeLength(Genome candidate) {
        variable value totalDistance = 0;
        value cityCount = candidate.size();
        for (i in 0..cityCount-1) {
            value nextIndex = i < cityCount - 1 then i + 1 else 0;
            totalDistance += getDistance(
                    candidate.get(i), candidate.get(nextIndex));
        }
        return totalDistance.float;
    }
}
