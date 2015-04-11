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
use std::mem;
use std::cmp::max;

use chrono::{DateTime, UTC};

use ::model::genome::{Optimization, Genome};
use ::tuneables::CROSSOVER_COUNT;

fn random_times<T: Rng>(opt: &Optimization, randomizer: &mut T)
        -> Vec<DateTime<UTC>> {
    let mut vec = Vec::with_capacity(CROSSOVER_COUNT);

    for _ in 0..CROSSOVER_COUNT {
        vec.push(opt.random_time(randomizer));
    }

    vec.sort();
    vec

}

fn crossover<'a>(mut parent1: &'a Genome, mut parent2: &'a Genome,
             times: Vec<DateTime<UTC>>) ->  (Genome, Genome) {
    let probable_length = max(parent1.pool.len(), parent2.pool.len());

    // integer multiply by 1.5!
    let probable_length = probable_length + probable_length / 2;

    let mut result_a = Genome::new_empty(probable_length);
    let mut index_a = 0;
    let mut result_b = Genome::new_empty(probable_length);
    let mut index_b = 0;

    for time in times.iter() {

        while let Some(activity) = parent1.pool.get(index_a) {
            if activity.start > *time {
                break;
            }
            result_a.pool.push(activity.clone());
            index_a += 1;
        }

        while let Some(activity) = parent2.pool.get(index_b) {
            if activity.start > *time {
                break;
            }
            result_b.pool.push(activity.clone());
            index_b += 1;
        }


        mem::swap(&mut parent1, &mut parent2);
        mem::swap(&mut index_a, &mut index_b);
    }

    while let Some(activity) = parent1.pool.get(index_a) {
        result_a.pool.push(activity.clone());
        index_a += 1;
    }

    while let Some(activity) = parent2.pool.get(index_b) {
        result_b.pool.push(activity.clone());
        index_b += 1;
    }

    (result_a, result_b)
}

pub fn crossover_rand<T: Rng>(opt: &Optimization, parent1: &Genome,
                              parent2: &Genome, random: &mut T)
        ->  (Genome, Genome) {

    crossover(parent1, parent2, random_times(opt, random))
}

#[cfg(test)]
pub mod tests {
    use rand::XorShiftRng;
    use chrono::UTC;
    use chrono::offset::TimeZone;

    use super::random_times;
    use super::crossover;

    use ::model::genome::{Optimization,Genome};
    use ::model::genome::testtree;
    use ::model::genome::tests::testgenomes;
    use ::model::genome::ActivityType::{WorkOn, Finish};


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
            UTC.ymd(2015, 1, 1).and_hms(15, 24, 58),
            UTC.ymd(2015, 1, 1).and_hms(15, 29, 56),
            UTC.ymd(2015, 1, 1).and_hms(15, 36, 36),
        ];
        let vec = random_times(&op1, &mut ran_doom);
        assert_eq!(vec1, vec);
    }

    #[test]
    pub fn test_crossing() {
        let (opt, g1, g2, g3) = testgenomes();

        let vec = vec!(
            UTC.ymd(2015, 2, 1).and_hms(6,0,0),
            UTC.ymd(2015, 2, 1).and_hms(9,0,0),
            UTC.ymd(2015, 2, 1).and_hms(12,0,0),
        );
        let (g1, g2) = crossover(&g1, &g2, vec);

        let expected_g1 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1,  3, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1, 11, 0, 0, Finish(opt.tree.children[0].clone())),
            (2015, 2, 1, 23, 0, 0, Finish(opt.tree.children[1].clone()))
        ]);
        let expected_g2 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[1].clone())),
            (2015, 2, 1,  6, 0, 0, WorkOn(opt.tree.children[1].clone())),
            (2015, 2, 1,  8, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1, 10, 0, 0, WorkOn(opt.tree.children[1].clone())),
            (2015, 2, 1, 12, 0, 0, Finish(opt.tree.children[1].clone())),
            (2015, 2, 1, 19, 0, 0, Finish(opt.tree.children[0].clone()))
        ]);

        assert_eq!(g1, expected_g1);
        assert_eq!(g2, expected_g2);

        let vec = vec!(
            UTC.ymd(2015,02,1).and_hms(5,0,0),
            UTC.ymd(2015,02,1).and_hms(10,0,0),
            UTC.ymd(2015,02,1).and_hms(15,0,0),
        );
        let (g1, g2) = crossover(&g1, &g3, vec);

        let expected_g1 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1,  3, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1,  9, 0, 0, WorkOn(opt.tree.children[2].clone())),
            (2015, 2, 1, 11, 0, 0, Finish(opt.tree.children[0].clone())),
            (2015, 2, 1, 22, 0, 0, Finish(opt.tree.children[2].clone()))
        ]);
        let expected_g2 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[2].clone())),
            (2015, 2, 1,  4, 0, 0, WorkOn(opt.tree.children[2].clone())),
            (2015, 2, 1, 12, 0, 0, Finish(opt.tree.children[2].clone())),
            (2015, 2, 1, 23, 0, 0, Finish(opt.tree.children[1].clone()))
        ]);
        assert_eq!(g1, expected_g1);
        assert_eq!(g2, expected_g2);
    }


}
