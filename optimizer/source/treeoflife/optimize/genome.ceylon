import java.util { Random }
import ceylon.time { Instant, dateTime, DateTime, Duration }
import ceylon.collection { ArrayList }
import ceylon.test { test }


class Genome({ScheduleItem*} genes = {})
        extends ArrayList<ScheduleItem>(0, 1.5, genes) {
    shared Integer findIndex(Instant time) {
        variable value lowest = 0;
        variable value highest = this.size; 

        while(lowest < highest){
            value difference = highest - lowest;
            value middle = (difference / 2) + lowest;
            if(exists gene = this[middle]) {
                switch (gene.start <=> time)
                case (equal) {
                    lowest = middle;
                    highest = middle;
                }
                case (smaller) { // gene smaller
                    lowest = middle + 1;
                }
                case (larger) { // gene larger
                    highest = middle;
                }
            } else {
                return middle;
            }
        }
        return highest;
    }
}

test void findIndexCorrect1() {
    value genome = Genome {
        NoTask(dateTime(2015, 1, 1, 1, 5).instant())
    };

    assert(genome.findIndex(dateTime(2015, 1, 1, 1, 10).instant())
            == 1);
    assert(genome.findIndex(dateTime(2015, 1, 1, 1, 5).instant())
            == 0);
    assert(genome.findIndex(dateTime(2015, 1, 1, 1, 1).instant())
            == 0);

    value genome2 = Genome {
        WorkOn(dateTime(2015, 1, 1, 1, 30).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 1, 2, 00).instant())
    };

    assert(genome2.findIndex(dateTime(2015, 1, 1, 1, 1).instant())
            == 0);
    assert(genome2.findIndex(dateTime(2015, 1, 1, 1, 30).instant())
            == 0);
    assert(genome2.findIndex(dateTime(2015, 1, 1, 1, 45).instant())
            == 1);
    assert(genome2.findIndex(dateTime(2015, 1, 1, 2, 00).instant())
            == 1);
    assert(genome2.findIndex(dateTime(2015, 1, 1, 2, 30).instant())
            == 2);
   
    value genome3 = Genome {
        WorkOn(dateTime(2015, 1, 1, 1, 30).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 1, 40).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 1, 50).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 2, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 2, 10).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 2, 20).instant(), nn(testtree.children[0]))
    };

    assert(genome3.findIndex(dateTime(2015, 1, 1, 1, 1).instant())
            == 0);
    assert(genome3.findIndex(dateTime(2015, 1, 1, 1, 45).instant())
            == 2);
    assert(genome3.findIndex(dateTime(2015, 1, 1, 2, 00).instant())
            == 3);
    assert(genome3.findIndex(dateTime(2015, 1, 1, 2, 30).instant())
            == 6);

    value genome4 = Genome {
        WorkOn(dateTime(2015, 1, 1, 1, 30).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 1, 45).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 2, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 2, 15).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 2, 30).instant(), nn(testtree.children[0]))
    };

    assert(genome4.findIndex(dateTime(2015, 1, 1, 1, 1).instant())
            == 0);
    assert(genome4.findIndex(dateTime(2015, 1, 1, 1, 35).instant())
            == 1);
    assert(genome4.findIndex(dateTime(2015, 1, 1, 1, 50).instant())
            == 2);
    assert(genome4.findIndex(dateTime(2015, 1, 1, 2, 20).instant())
            == 4);
    assert(genome4.findIndex(dateTime(2015, 1, 1, 2, 30).instant())
            == 4);
}

abstract class ScheduleItem(start)
    of NoTask, WorkOn, DoTask {
    shared Instant start;
    shared DateTime startdt => start.dateTime();
}

class NoTask(Instant start)
    extends ScheduleItem(start) {
    shared actual Boolean equals(Object that) {
        if (is NoTask x = that, x.start == start) {
            return true;
        }
        return false;
    }
    shared actual String string => "[@``startdt`` NoTask]";
}

class WorkOn(Instant start, activity)
        extends ScheduleItem(start) {

    shared actual Boolean equals(Object that) {
        if (is WorkOn x = that,
                x.start == start && x.activity === activity) {
            return true;
        }
        return false;
    }

    shared Node activity;
    shared actual String string => "[@``startdt`` WorkOn ``activity``]";
}

class DoTask(Instant start, activity)
        extends ScheduleItem(start) {

    shared actual Boolean equals(Object that) {
        if (is DoTask x = that,
                x.start == start && x.activity === activity) {
            return true;
        }
        return false;
    }

    shared Node activity;
    shared actual String string => "[@``startdt`` DoTask ``activity``]";
}


// tree is intended to be immutable; hence no need for linked list between nodes

class BaseNode(type, text, {Node*} children_={}) {
    shared [Node*] children = children_.sequence();
    variable value childrenSizes = 0;
    for (child in children) {
        childrenSizes += child.subtreesize;
    }
    shared Integer subtreesize = children.size + childrenSizes;
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

class Node(String type, String text, {Node*} children={})
        extends BaseNode(type, text, children) {
    shared late BaseNode parent;
}

class Project(String text, {Node*} children={})
        extends Node("project", text, children) {
}

class Task(String text, {Node*} children={})
        extends Node("task", text, children) {
}

class LifeTree({Node*} children_={})
        extends BaseNode("life", null, children_) {
    shared Node findNode(Integer index) {
        variable value currentIndex = 0;
        if (this.children.size == 0) {
            throw Exception("wat");
        }
        variable value parentIterator = this.children.iterator();
        assert(is Node initialNode = parentIterator.next());
        variable value currentNode = initialNode;

        while (currentIndex < index) {
            currentIndex++;
            if (currentIndex + currentNode.subtreesize > index) {
                parentIterator = currentNode.children.iterator();
                assert(is Node node = parentIterator.next());
                currentNode = node;
            } else {
                currentIndex += currentNode.subtreesize;
                assert(is Node node = parentIterator.next());
                currentNode = node;
            }
        }
        assert(currentIndex == index);
        return currentNode;
    }

    shared Node randomnode(Random random){
        return findNode(random.nextInt(this.subtreesize));
    }
}


class ScheduleParams(tree, start) {
    shared LifeTree tree;
    shared Instant start;
    shared Duration length = scheduleLength;
    shared Instant end => start.plus(length);
    shared Float getFitness(Genome schedule) {
        return fitness(this, schedule);
    }
    shared Instant randomTime(Random random) {
        return this.start.plus(Duration(random.nextInt(this.length.milliseconds)));
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

test void findNodeSanityCheck() {
    value target = Task("d");
    value target2 = Task("a");
    value fnTree = LifeTree {
        Task {
            text = "A";
            Task {
                text = "i";
                Task("a"),
                Task("b"),
                Task("c")
            },
            Task {
                text = "ii";
                target,
                Task("e")
            }
        },
        Task {
            text = "B";
            Task {
                text = "i";
                target2,
                Task("b")
            }
        }
    };
    
    assert(fnTree.findNode(6) == target);
    assert(fnTree.findNode(10) == target2);
}

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
