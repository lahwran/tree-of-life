// 1. Randomly choose n times along the genome
// 2. Create a new list (array, avg length * 1.3?)
// 3. Iterate through the lists, appending to the new list,
//     switching between them at the crossover points
// 
// later:
// 4. Keep track of duplicate single-instance items as it goes,
//     deleting a randomly chosen side of the duplicate

import java.util { Random }
import ceylon.time { dateTime, Duration, Instant }
import ceylon.test { test }

[Instant*] randomTimes(ScheduleParams params, Random randomizer) {
    return sort([
        for (x in 0..crossoverCount)
        params.start.plus(Duration(randomizer.nextInt(params.length.milliseconds)))
    ]);
}

Genome crossover(ScheduleParams params, Genome parent1, Genome parent2, [Instant*] times) {
    value newgenome = Genome();
    variable value current_index = 0;
    variable value last_index = 0;
    variable value current_parent = parent1;
    variable value last_parent = parent2;
    for (time in times) {

        while (exists item = current_parent[current_index], item.start < time) {
            newgenome.add(item);
            current_index += 1;
        }
        while (exists item = last_parent[last_index], item.start < time) {
            last_index += 1;
        }

        value temp_parent = current_parent;
        current_parent = last_parent;
        last_parent = temp_parent;

        value temp_index = current_index;
        current_index = last_index;
        last_index = temp_index;
    }

    while (exists item = current_parent[current_index]) {
        newgenome.add(item);
        current_index += 1;
    }
    return newgenome;
}

test void blah() {
    value genome1 = Genome {
        WorkOn(dateTime(2015, 1, 1, 11, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 12, 15).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 1, 12, 50).instant(), nn(testtree.children[2])),
        WorkOn(dateTime(2015, 1, 1, 14, 15).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 1, 16, 00).instant())
        };

    value genome2 = Genome {
        WorkOn(dateTime(2015, 1, 1, 11, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 11, 30).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 1, 12, 40).instant(), nn(testtree.children[2])),
        WorkOn(dateTime(2015, 1, 1, 13, 40).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 15, 00).instant(), nn(testtree.children[1])),
        NoTask(dateTime(2015, 1, 1, 16, 00).instant())
        };
    value times = [
        dateTime(2015, 1, 1, 12, 00).instant(),
        dateTime(2015, 1, 1, 13, 00).instant(),
        dateTime(2015, 1, 1, 14, 00).instant()
        ];
    value params = ScheduleParams(testtree, dateTime(2015, 1, 1, 11, 00).instant());
    value result = crossover(params, genome1, genome2, times);
    value expectedgenome = Genome {
        WorkOn(dateTime(2015, 1, 1, 11, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 12, 40).instant(), nn(testtree.children[2])),
        WorkOn(dateTime(2015, 1, 1, 15, 00).instant(), nn(testtree.children[1])),
        NoTask(dateTime(2015, 1, 1, 16, 00).instant())
        };
    print("result: ``result``");
    print("expected genome: ``expectedgenome``");
    assert (result == expectedgenome);
}

