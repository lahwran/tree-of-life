import java.lang { IllegalArgumentException }
import java.util { JList = List }
import ceylon.interop.java { CeylonList }

import org.uncommons.maths.random { MersenneTwisterRNG, PoissonGenerator }
import org.uncommons.watchmaker.framework { CandidateFactory,
    EvolutionEngine, EvolutionObserver, EvolutionaryOperator,
    GenerationalEvolutionEngine, PopulationData, SelectionStrategy,
    FitnessEvaluator }
import org.uncommons.watchmaker.framework.operators {
    ListOrderCrossover, ListOrderMutation }
import org.uncommons.watchmaker.framework.termination { GenerationCount }


List<String> calculateShortestRoute(List<String> cities,
        DistanceLookup distances,
        SelectionStrategy<in JList<String>> selectionStrategy,
        Integer populationSize, Integer eliteCount,
        Integer generationCount) {

    value evaluator = makeListEvaluator<String>(false, distances.routeLength);

    value rng = MersenneTwisterRNG();

    // Set-up evolution pipeline (cross-over followed by mutation).
    value pipeline = makePipeline([
        ListOrderCrossover<String>(),
        ListOrderMutation<String>(
            PoissonGenerator(1.5, rng),
            PoissonGenerator(1.5, rng)
        )
    ]);

    value candidateFactory = listPermutations(cities);
    value engine = GenerationalEvolutionEngine<JList<String>>(
        candidateFactory,
        pipeline,
        evaluator,
        selectionStrategy,
        rng
    );
    return CeylonList(engine.evolve(populationSize, eliteCount,
                            GenerationCount(generationCount)));
}
