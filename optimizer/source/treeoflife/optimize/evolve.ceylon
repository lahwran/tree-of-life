import java.lang { IllegalArgumentException }

import org.uncommons.maths.random { MersenneTwisterRNG, PoissonGenerator }
import org.uncommons.watchmaker.framework { CandidateFactory,
    EvolutionEngine, EvolutionObserver, EvolutionaryOperator,
    GenerationalEvolutionEngine, PopulationData, SelectionStrategy,
    FitnessEvaluator }
import org.uncommons.watchmaker.framework.operators {
    ListOrderCrossover, ListOrderMutation }
import org.uncommons.watchmaker.framework.factories {
    ListPermutationFactory }
import org.uncommons.watchmaker.framework.termination { GenerationCount }


alias Gene => String;
alias Genome => List<String>;


Genome calculateShortestRoute(Genome cities,
        DistanceLookup distances,
        SelectionStrategy<in Genome> selectionStrategy,
        Integer populationSize, Integer eliteCount,
        Integer generationCount) {

    value evaluator = makeListEvaluator<Gene>(false, distances.routeLength);

    value rng = MersenneTwisterRNG();

    // Set-up evolution pipeline (cross-over followed by mutation).
    value pipeline = makePipeline([
        ListOrderCrossover<Gene>(),
        ListOrderMutation<Gene>(
            PoissonGenerator(1.5, rng),
            PoissonGenerator(1.5, rng)
        )
    ]);

    value candidateFactory = listPermutations(genome);
    value engine = GenerationalEvolutionEngine(
        candidateFactory,
        pipeline,
        evaluator,
        selectionStrategy,
        rng
    );
    return engine.evolve(populationSize, eliteCount,
                            GenerationCount(generationCount));
}
