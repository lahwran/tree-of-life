// 1. Randomly choose n times along the genome
// 2. Create a new list (array, avg length * 1.3?)
// 3. Iterate through the lists, appending to the new list,
//     switching between them at the crossover points
//
// later:
// 4. Keep track of duplicate single-instance items as it goes,
//     deleting a randomly chosen side of the duplicate

// http://doc.rust-lang.org/rand/rand/index.html

use rand::{Rng};
use std::collections::Bound::{Included, Excluded};
use std::mem;

use chrono::{DateTime, UTC, Duration};

use ::fitness::PairIter;
use ::genome::{Optimization, Genome};

fn random_time<T: Rng>(opt: &Optimization, randomizer: &mut T)
        -> DateTime<UTC> {
    opt.start.clone() + Duration::seconds(
        randomizer.gen_range(0, opt.duration().num_seconds()))
}

fn random_times<T: Rng>(opt: &Optimization, randomizer: &mut T)
        -> Vec<DateTime<UTC>> {
    let mut vec = Vec::with_capacity(3);
    vec.push(opt.start.clone());
    vec.push(opt.end.clone() + Duration::seconds(1));

    for _ in 0..3 {
        vec.push(random_time(opt, randomizer));
    }

    vec.sort();
    vec

}

fn crossover(parent1: &Genome, parent2: &Genome,
             times: Vec<DateTime<UTC>>) ->  (Genome, Genome) {
    let mut newg1 = Genome::new_empty();
    let mut newg2 = Genome::new_empty();

    for (start, end) in PairIter::new(times.iter()) {
        for (_, activity) in parent1.range(Included(start), Excluded(end)) {
            newg1.insert(activity.clone());
        }

        for (_, activity) in parent2.range(Included(start), Excluded(end)) {
            newg2.insert(activity.clone());
        }
        mem::swap(&mut newg1, &mut newg2)
    }

    (newg1, newg2)
}

pub fn crossover_rand<T: Rng>(opt: &Optimization, parent1: &Genome, parent2: &Genome,
                       random: &mut T) ->  (Genome, Genome) {
    crossover(parent1, parent2, random_times(opt, random))

}

pub mod tests {
    use rand::XorShiftRng;
    use chrono::UTC;
    use chrono::offset::TimeZone;

    use super::random_times;
    use super::crossover;

    use ::genome::Optimization;
    use ::genome::tests::testtree;
    use ::genome::tests::testgenomes;


    #[test]
    pub fn test_random_times(){
        let mut ran_doom = XorShiftRng::new_unseeded();
        let tree = testtree();
        let op1 = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 20, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );
        let vec1 = vec![
            UTC.ymd(2015, 1, 1).and_hms(15,20,0),
            UTC.ymd(2015,01,01).and_hms(15,24,58),
            UTC.ymd(2015,01,01).and_hms(15,29,56),
            UTC.ymd(2015,01,01).and_hms(15,36,36),
            UTC.ymd(2015, 1, 1).and_hms(15,50,1),
        ];
        let vec = random_times(&op1, &mut ran_doom);
        assert_eq!(vec1, vec);
    }

    //#[test]
    pub fn test_crossing(){
        println!("");
        let (_, g1, g2, g3) = testgenomes();

        // for activity in g1.values() {
        //     println!("{:?}", activity);
        // }
        // println!("");
        // for activity in g2.values() {
        //     println!("{:?}", activity);
        // }

        let vec = vec!(
            UTC.ymd(2015,02,1).and_hms(6,0,0),
            UTC.ymd(2015,02,1).and_hms(9,0,0),
            UTC.ymd(2015,02,1).and_hms(12,0,0),
        );
        let (g1, g2) = crossover(&g1, &g2, vec);

        assert!(g1.contains_key(&UTC.ymd(2015,02,1).and_hms(12,0,0)));
        assert!(g1.contains_key(&UTC.ymd(2015,02,1).and_hms(6,0,0)));
        assert!(g2.contains_key(&UTC.ymd(2015,02,1).and_hms(8,0,0)));
        assert!(g2.contains_key(&UTC.ymd(2015,02,1).and_hms(19,0,0)));

        let vec = vec!(
            UTC.ymd(2015,02,1).and_hms(5,0,0),
            UTC.ymd(2015,02,1).and_hms(10,0,0),
            UTC.ymd(2015,02,1).and_hms(15,0,0),
        );
        let (g1, g2) = crossover(&g1, &g3, vec);

        assert!(g1.contains_key(&UTC.ymd(2015,02,1).and_hms(9,0,0)));
        assert!(g1.contains_key(&UTC.ymd(2015,02,1).and_hms(22,0,0)));
        assert!(g2.contains_key(&UTC.ymd(2015,02,1).and_hms(6,0,0)));
        assert!(g2.contains_key(&UTC.ymd(2015,02,1).and_hms(4,0,0)));
    }


}
