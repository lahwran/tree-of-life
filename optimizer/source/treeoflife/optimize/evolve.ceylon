import java.util { JList = List, Random }
import ceylon.interop.java { CeylonList, JavaList }

import org.uncommons.maths.random {
    MersenneTwisterRNG, PoissonGenerator, Probability }
import org.uncommons.watchmaker.framework {
    GenerationalEvolutionEngine, SelectionStrategy, EvolutionaryOperator, FitnessEvaluator }
import org.uncommons.watchmaker.framework.operators {
    ListOrderCrossover, ListOrderMutation, AbstractCrossover }
import org.uncommons.watchmaker.framework.factories {
    AbstractCandidateFactory }
import org.uncommons.watchmaker.framework.termination { GenerationCount }


Genome evolveSchedule(ScheduleParams params,
        SelectionStrategy<in Genome> selectionStrategy,
        Integer populationSize,
        Integer eliteCount,
        Integer generationCount) {
    object fitnessEvaluator satisfies FitnessEvaluator<Genome> {
        shared actual Float getFitness(Genome candidate,
                JList<out Genome> ignored) {
            return fitness(params, candidate);
        }
        shared actual Boolean natural = true; // true -> it is ascending
    }

    // TODO: for maximum repeatability, each phase of random should
    // have its own seed
    value rng = MersenneTwisterRNG(seed);

    object crossoverObj
            extends AbstractCrossover<Genome>(1, Probability.\iONE) {
        shared actual JavaList<Genome> mate(
                Genome parent1, Genome parent2,
                Integer points, Random rng) {
            value times = randomTimes(params, rng);
            return JavaList(crossover(params, parent1, parent2, times));
        }
    }

    object mutationObj satisfies EvolutionaryOperator<Genome> {
        shared actual JList<Genome> apply(
                JList<Genome> population, Random rng) {
            value converted = CeylonList(population);
            return JavaList([
                for (candidate in converted)
                mutate(params, candidate, rng)
            ]); 
        }
    }

    value pipeline = makePipeline([
        crossoverObj, mutationObj
    ]);

    object candidateFactory extends AbstractCandidateFactory<Genome>() {
        shared actual Genome generateRandomCandidate(Random rng) {
            value addCount = rng.nextInt(25);
            Genome g = Genome();
            for (i in 0:addCount) {
                addGene(params, g, rng);
            }
            return g;
        }
    }

    value engine = GenerationalEvolutionEngine<Genome>(
        candidateFactory,
        pipeline,
        fitnessEvaluator,
        selectionStrategy,
        rng
    );
    engine.setSingleThreaded(true);
    return engine.evolve(populationSize, eliteCount,
                GenerationCount(generationCount));
}


List<String> calculateShortestRoute(
        List<String> cities,
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
    engine.setSingleThreaded(true);
    return CeylonList(engine.evolve(populationSize, eliteCount,
                            GenerationCount(generationCount)));
}
