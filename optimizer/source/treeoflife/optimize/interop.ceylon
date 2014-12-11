import java.util { JList = List }
import ceylon.interop.java { JavaList, CeylonList }
import org.uncommons.watchmaker.framework {
    EvolutionaryOperator, FitnessEvaluator }
import org.uncommons.watchmaker.framework.operators {
    EvolutionPipeline }
import org.uncommons.watchmaker.framework.factories {
    ListPermutationFactory }

EvolutionPipeline<T> makePipeline<T>([EvolutionaryOperator<T>*] operators) {
    return EvolutionPipeline<T>(JavaList(operators));
}

ListPermutationFactory<T> listPermutations<T>(List<T> base)
        given T satisfies Object {
    return ListPermutationFactory(JavaList(base));
}

FitnessEvaluator<JList<T>> makeListEvaluator<T>(Boolean ascending,
        Integer(List<T>)|Float(List<T>) evaluator)
        given T satisfies Object {

    object fitnessEvaluator satisfies FitnessEvaluator<JList<T>> {
        shared actual Float getFitness(JList<T> candidate,
                JList<out JList<T>> ignored) {
            value result = evaluator(CeylonList(candidate).coalesced.sequence());
            switch(result)
            case(is Integer) {
                return result.float;
            }
            case(is Float) {
                return result;
            }
        }
        shared actual Boolean natural = ascending;
    }
    return fitnessEvaluator;
}
