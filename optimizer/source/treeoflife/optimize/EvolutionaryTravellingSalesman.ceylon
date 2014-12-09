import java.util {
    ArrayList,
    Collection,
    LinkedList,
    List,
    Random
}
import java.lang { IllegalArgumentException }
import org.uncommons.maths.random { MersenneTwisterRNG, PoissonGenerator }
import org.uncommons.watchmaker.framework {
    CandidateFactory,
    EvolutionEngine,
    EvolutionObserver,
    EvolutionaryOperator,
    GenerationalEvolutionEngine,
    PopulationData,
    SelectionStrategy
}
import org.uncommons.watchmaker.framework.factories { ListPermutationFactory }
import org.uncommons.watchmaker.framework.operators {
    EvolutionPipeline,
    ListOrderCrossover,
    ListOrderMutation
}
import org.uncommons.watchmaker.framework.termination { GenerationCount }

alias Gene => String;
alias Genome => List<String>;

Genome calculateShortestRoute(
        Collection<Gene> cities, DistanceLookup distances,
        SelectionStrategy<in Genome> selectionStrategy,
        Integer populationSize, Integer eliteCount,
        Integer generationCount, Boolean crossover,
        Boolean mutation) {

    if (!crossover && !mutation) {
        throw IllegalArgumentException(
                "At least one of cross-over or mutation must be selected.");
    }

    value rng = MersenneTwisterRNG();

    // Set-up evolution pipeline (cross-over followed by mutation).
    value operators = ArrayList<EvolutionaryOperator<Genome>>(2);
    if (crossover) {
        operators.add(ListOrderCrossover<Gene>());
    }
    if (mutation) {
        operators.add(ListOrderMutation<Gene>(
            PoissonGenerator(1.5, rng),
            PoissonGenerator(1.5, rng)
        ));
    }

    value pipeline = EvolutionPipeline<List<Gene>>(operators);

    value candidateFactory = ListPermutationFactory<Gene>(
            LinkedList<Gene>(cities));
    value engine = GenerationalEvolutionEngine<Genome>(
        candidateFactory,
        pipeline,
        RouteEvaluator(distances),
        selectionStrategy,
        rng
    );
    return engine.evolve(populationSize, eliteCount,
                            GenerationCount(generationCount));
}
