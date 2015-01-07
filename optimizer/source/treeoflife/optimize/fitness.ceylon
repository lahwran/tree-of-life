import ceylon.collection { HashMap, unlinked, ArrayList }
import ceylon.math.float { sqrt }

class NodeState() {
    shared variable Integer msSoFar = 0;
}

class TreeState(LifeTree tree) {
    value state = HashMap<BaseNode, NodeState>(unlinked);

    shared NodeState get(BaseNode node) {
        if (exists existing = state[node]) {
            return existing;
        }
        value new_ = NodeState();
        state.put(node, new_);
        return new_;
    }

    value projectStates = ArrayList<NodeState>();
    tree.walk(void(node) {
        if (is Project node) {
            projectStates.add(get(node));
        }
    });


    shared Float balanceQuality() {
        value mstimes = [ for (state in projectStates) state.msSoFar ];
        // TODO: check empty, return 1
        value average = mstimes.fold(0)(plus) / mstimes.size;
        value deltas = { for(ms in mstimes) (ms - average) ^ 2 };
        value variance = deltas.fold(0)(plus);
        value stddev = sqrt(variance.float);
        // had to look this one up:
        // http://en.wikipedia.org/wiki/Coefficient_of_variation
        value cv = stddev / average;
        // cv is typically 0.1-ish, but ranges to infinity.
        // to get the result to be returned as a quality percentage,
        // 1 / (1.1)  which is 0.9 or so is preferable.
        return 1 / (cv - 1);
    }
}

Float fitness(LifeTree tree, Genome schedule) {
    value treestate = TreeState(tree);
    variable Float fitness = 100.0;

    for ([first, second] in schedule.paired) {
        if (is NoTask first) {
            continue;
        }
        value delta = first.start.durationTo(second.start);
        if (is DoTask first) {
            fitness *= 0.5;
            continue;
        }
        assert (is WorkOn task = first);

        value state = treestate.get(task.activity);
        state.msSoFar += delta.milliseconds;
    }
    fitness *= treestate.balanceQuality();

    //if (!schedule.last is NoTask) {
    //    fitness *= 0.5;
    //}
    return fitness;
}

shared void fitnessrun() {
    
}
