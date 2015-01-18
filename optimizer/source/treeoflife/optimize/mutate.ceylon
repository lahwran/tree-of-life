import ceylon.interop.java { createJavaByteArray }
import java.lang { ByteArray }
import java.util { Random }
import org.uncommons.maths.random { MersenneTwisterRNG }
import ceylon.time { dateTime, Duration, Instant }
import ceylon.test { test }


// TODO: is it faster to ignore sorting until the end, and then sort it?

Genome mutate(ScheduleParams params, Genome original, Random random){
    value genome = Genome(original);
    value node = params.tree.randomnode(random);
    value inserttime = params.randomTime(random);

    // TODO: randomly choose task type
    value gene = DoTask(inserttime, node);

    //value insertpoint = random.nextInt(genome.size + 1);
    genome.insert(genome.size, gene);
    return genome;
}

ByteArray seed {
    return createJavaByteArray {
        0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte,
        0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte
    };
}

test void testMutate() {
    value genome = Genome {
        WorkOn(dateTime(2015, 1, 1, 11, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 1, 12, 15).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 1, 12, 50).instant(), nn(testtree.children[2])),
        WorkOn(dateTime(2015, 1, 1, 14, 15).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 1, 16, 00).instant())
        };
    value params = ScheduleParams(testtree, dateTime(2015, 1, 1, 11, 00).instant());

    value random = MersenneTwisterRNG(seed);
    print(mutate(params, genome, random));
}

