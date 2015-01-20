import ceylon.interop.java { createJavaByteArray }
import java.lang { ByteArray }
import java.util { Random }
import org.uncommons.maths.random { MersenneTwisterRNG }
import ceylon.time { dateTime, Duration, Instant }
import ceylon.test { test }


// TODO: is it faster to ignore sorting until the end, and then sort it?

void addGene(ScheduleParams params, Genome genome, Random random){
    value node = params.tree.randomnode(random);
    value insertTime = params.randomTime(random);

    // TODO: randomly choose task type
    value gene = DoTask(insertTime, node);

    //value insertpoint = random.nextInt(genome.size + 1);
    genome.insert(genome.findIndex(insertTime), gene);
}


Genome mutateGene(ScheduleParams params, Genome original, Random random){
    value genome = Genome(original);
    value addCount = (10 * random.nextFloat() ^ 3).integer;
    value deleteCount = (10 * random.nextFloat() ^ 3).integer;
    for (i in 0:deleteCount){
        genome.delete(random.nextInt(genome.size));
    }
    for (i in 0:addCount){
        addGene(params, genome, random);
    }
    return genome;

}
ByteArray seed {
    return createJavaByteArray {
        0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte,
        0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte, 0.byte
    };
}

test void testAddGene() {
    value genome = Genome {
        WorkOn(dateTime(2015, 1, 1, 11, 00).instant(), nn(testtree.children[0])),
        WorkOn(dateTime(2015, 1, 7, 12, 15).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 15, 12, 50).instant(), nn(testtree.children[2])),
        WorkOn(dateTime(2015, 1, 25, 14, 15).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 29, 16, 00).instant())
    };
    value params = ScheduleParams(testtree, dateTime(2015, 1, 1, 11, 00).instant());

    value random = MersenneTwisterRNG(seed);
    value result = Genome(genome);
    addGene(params, result, random);

    value expectedGenome = Genome {
        WorkOn(dateTime(2015, 1,  1, 11, 00).instant(), nn(testtree.children[0])),

        // copied from pseudorandom output
        // http://xkcd.com/221/
        DoTask(dateTime(2015, 1,  5,  4, 34, 34, 520).instant(),
                nn(nn(testtree.children[0]).children[0])),

        WorkOn(dateTime(2015, 1,  7, 12, 15).instant(), nn(testtree.children[1])),
        WorkOn(dateTime(2015, 1, 15, 12, 50).instant(), nn(testtree.children[2])),
        WorkOn(dateTime(2015, 1, 25, 14, 15).instant(), nn(testtree.children[0])),
        NoTask(dateTime(2015, 1, 29, 16, 00).instant())
    };
    assert(result == expectedGenome);
}

