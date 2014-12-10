import java.util { JList = List }
import ceylon.interop.java { JavaList, CeylonList }
import org.uncommons.watchmaker.framework {
    EvolutionaryOperator, FitnessEvaluator }
import org.uncommons.watchmaker.framework.operators {
    EvolutionPipeline }
EvolutionPipeline<T> makePipeline<T>([EvolutionaryOperator<T>*] operators) {
    return EvolutionPipeline<T>(JavaList(operators));
}

ListPermutationFactory<T> listPermutations<T>([T+] base) {
    return ListPermutationFactory(JavaList(base));
}

FitnessEvaluator<JList<T>> makeListEvaluator<T>(Boolean ascending,
        Integer(List<T>)|Float(List<T>) evaluator) {

    object fitnessEvaluator satisfies FitnessEvaluator<JList<T>> {
        shared actual Float getFitness(JList<T> candidate,
                JList<out JList<T>> ignored) {
            value result = evaluator(CeylonList(candidate));
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
