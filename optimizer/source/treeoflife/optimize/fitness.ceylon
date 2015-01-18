import ceylon.collection { HashMap, unlinked, ArrayList }
import ceylon.time { dateTime }
import ceylon.math.float { sqrt }
import ceylon.test { test }

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
        value times = [ for (state in projectStates) state.msSoFar.float/100000.0 ];
        // TODO: check empty, return 1
        value average = times.fold(0.0)(plus) / times.size;
        value deltas = { for(ms in times) (ms - average) ^ 2 };
        value variance = deltas.fold(0.0)(plus);
        value stddev = sqrt(variance);
        // had to look this one up:
        // http://en.wikipedia.org/wiki/Coefficient_of_variation
        value cv = stddev / average;
        // cv is typically 0.1-ish, but ranges to infinity.
        // to get the result to be returned as a quality percentage,
        // 1 / (1.1)  which is 0.9 or so is preferable.
        return 1 / (cv + 1);
    }
}

Float fitness(ScheduleParams params, Genome schedule) {
    value treestate = TreeState(params.tree);
    variable Float fitness = 100.0;

    assert(exists firstitem = schedule.first);
    assert(exists lastitem = schedule.last);
    // only do these checks when debugging - performance loss
    assert(firstitem.start == params.start);
    assert(lastitem.start <= params.end);
    assert(lastitem is NoTask);

    variable value totalMSWorking = 0;

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
        totalMSWorking += delta.milliseconds;
    }
    fitness *= totalMSWorking.float / params.length.milliseconds.float;
    fitness *= treestate.balanceQuality();

    //if (!schedule.last is NoTask) {
    //    fitness *= 0.5;
    //}
    return fitness;
}

shared void fitnessrun() {
    
}

test
void balancedGetsGoodRating() {
    value genome1 = Genome {
        WorkOn(dateTime(2015, 1, 1, 15, 20).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 15, 30).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 1, 15, 40).instant(), nn(testtree.children[2])),
        NoTask(dateTime(2015, 1, 1, 15, 50).instant())
    };
    value scheduleparams1 = ScheduleParams(testtree, dateTime(2015, 1, 1, 15, 20).instant());
    value f1 = fitness(scheduleparams1, genome1);
    value genome2 = Genome {
        WorkOn(dateTime(2015, 1, 1, 15, 0).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 15, 30).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 1, 15, 40).instant(), nn(testtree.children[2])),
        NoTask(dateTime(2015, 1, 1, 15, 50).instant())
    };
    value scheduleparams2 = ScheduleParams(testtree, dateTime(2015, 1, 1, 15, 0).instant());
    value f2 = fitness(scheduleparams2, genome2);
    assert(f1 > f2);
}

test
void testMoreTimeRating() {
    value genome1 = Genome {
        WorkOn(dateTime(2015, 1, 1, 15, 20).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 1, 15, 50).instant())
    };
    value scheduleparams1 = ScheduleParams(testtree, dateTime(2015, 1, 1, 15, 20).instant());
    value f1 = fitness(scheduleparams1, genome1);
    value genome2 = Genome {
        WorkOn(dateTime(2015, 1, 1, 15, 0).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 1, 15, 50).instant())
    };
    value scheduleparams2 = ScheduleParams(testtree, dateTime(2015, 1, 1, 15, 0).instant());
    value f2 = fitness(scheduleparams2, genome2);
    assert(f1 < f2);
}
