
import java.util { List }
import org.uncommons.watchmaker.framework { FitnessEvaluator }

class RouteEvaluator(shared DistanceLookup distances)
            satisfies FitnessEvaluator<Genome> {

    shared actual Float getFitness(Genome candidate,
            List<out Genome> population) {
        return distances.routeLength(candidate);
    }

    shared actual Boolean natural = false;
}
