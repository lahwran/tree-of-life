
import java.util { List }
import org.uncommons.watchmaker.framework { FitnessEvaluator }

shared class RouteEvaluator(shared DistanceLookup distances)
            satisfies FitnessEvaluator<List<String>> {

    shared actual Float getFitness(List<String> candidate,
                             List<out List<String>> population)
    {
        variable value totalDistance = 0;
        value cityCount = candidate.size();
        for (i in 0..cityCount-1) {
            value nextIndex = i < cityCount - 1 then i + 1 else 0;
            totalDistance += distances.getDistance(candidate.get(i),
                                                   candidate.get(nextIndex));
        }
        return totalDistance.float;
    }

    shared actual Boolean natural = false;
}
