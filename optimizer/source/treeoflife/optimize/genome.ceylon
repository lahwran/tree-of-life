import ceylon.time { Instant, dateTime, DateTime }
import ceylon.collection { ArrayList }


class Genome({ScheduleItem+} genes)
        extends ArrayList<ScheduleItem>(0, 1.5, genes) {
}

abstract class ScheduleItem(start)
    of NoTask, WorkOn, DoTask {
    shared Instant start;
    shared DateTime startdt => start.dateTime();
}

class NoTask(Instant start)
    extends ScheduleItem(start) {
    shared actual String string => "[@``startdt`` NoTask]";
}

class WorkOn(Instant start, activity)
        extends ScheduleItem(start) {
    shared Node activity;
    shared actual String string => "[@``startdt`` WorkOn ``activity``]";
}

class DoTask(Instant start, activity)
        extends ScheduleItem(start) {
    shared Node activity;
    shared actual String string => "[@``startdt`` DoTask ``activity``]";
}


// tree is intended to be immutable; hence no need for linked list between nodes

class BaseNode(type, text, {Node*} children_) {
    shared [Node*] children = children_.sequence();

    shared String? text;
    shared String type;
    shared actual String string {
        String childinfo;
        if (nonempty children) {
            childinfo = " (``children.size`` children)";
        } else {
            childinfo = "";
        }
        if (exists text) {
            return "``type``: ``text````childinfo``";
        } else {
            return "``type````childinfo``";
        }
    }

    for (child in children) {
        child.parent = this;
    }

    shared void walk(Anything(BaseNode) callback) {
        callback(this);
        for (node in children) {
            node.walk(callback);
        }
    }
}

class Node(String type, String text, {Node*} children)
        extends BaseNode(type, text, children) {
    shared late BaseNode parent;
}

class Project(String text, {Node*} children)
        extends Node("project", text, children) {
}

class Task(String text, {Node*} children)
        extends Node("task", text, children) {
}

class LifeTree({Node*} children)
        extends BaseNode("life", null, children) {
    shared Float getFitness(Genome schedule) {
        return fitness(this, schedule);
    }
}

LifeTree testtree = LifeTree {
    Project {
        text = "some project";
        Task {
            text = "derp";
        }
    },
    Project {
        text = "another project";
    },
    Project {
        text = "yet another project";
    }
};

T nn<T>(T? input) {
    assert (exists result = input);
    return result;
}

shared void genomerun() {
    print("tree: ``testtree``");
    print("children: ``testtree.children``");

    value genome = Genome {
        NoTask(dateTime(2015, 1, 1).instant()),
        WorkOn(dateTime(2015, 1, 1, 15, 0).instant(), nn(testtree.children[0])),
        //DoTask(dateTime(2015, 1, 1, 15, 10).instant(), nn(nn(testtree.children[0]).children[0])),
        WorkOn(dateTime(2015, 1, 1, 15, 20).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 15, 30).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 1, 15, 40).instant(), nn(testtree.children[2]))
    };

    print("test genome:");
    for (item in genome) {
        print("Genome item: ``item``");
    }
}
