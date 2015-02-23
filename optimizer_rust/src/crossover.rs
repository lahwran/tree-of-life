// 1. Randomly choose n times along the genome
// 2. Create a new list (array, avg length * 1.3?)
// 3. Iterate through the lists, appending to the new list,
//     switching between them at the crossover points
// 
// later:
// 4. Keep track of duplicate single-instance items as it goes,
//     deleting a randomly chosen side of the duplicate

// http://doc.rust-lang.org/rand/rand/index.html

use std::rand::{Rng};
use std::collections::Bound::{Included, Excluded};
use std::mem;

use chrono::{DateTime, UTC, Duration};

use ::fitness::PairIter;
use ::genome::{Optimization, Genome, Activity, ActivityType};

fn random_time<T: Rng>(opt: &Optimization, randomizer: &mut T)
        -> DateTime<UTC> {
    opt.start.clone() + Duration::minutes(
        randomizer.gen_range(0, opt.duration().num_minutes()))
}

fn random_times<T: Rng>(opt: &Optimization, randomizer: &mut T)
        -> Vec<DateTime<UTC>> {
    let mut vec = Vec::with_capacity(3);
    for x in 0..3 {
        vec.push(random_time(opt, randomizer));

    }

    vec.sort();
    vec

}

fn crossover(opt: &Optimization, parent1: Genome, parent2: Genome,
             times: &mut Vec<DateTime<UTC>>) ->  (Genome, Genome) {
    let mut newg1 = Genome::new();
    let mut newg2 = Genome::new();
    times.insert(0,opt.start.clone());
    times.push(opt.end.clone());

    for (start, end) in PairIter::new(times.iter()) {
        println!("{:?}", times);
            for (datetime, activity) in parent1.range(Included(start), Excluded(end)) {
                newg1.insert(activity.clone());
            }

            for (datetime, activity) in parent2.range(Included(start), Excluded(end)) {
                newg2.insert(activity.clone());
            }
            mem::swap(&mut newg1, &mut newg2)
            
    }
    
    // newg1.insert(Activity{start: opt.end.clone(), activitytype: ActivityType::Nothing});
    // newg2.insert(Activity{start: opt.end.clone(), activitytype: ActivityType::Nothing});
    
    (newg1, newg2)
}

pub mod tests {
    use std::rand::XorShiftRng;
    use chrono::UTC;
    use chrono::Offset;

    use super::random_times;
    use super::crossover;

    use ::genome::{Genome, Optimization};
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
                UTC.ymd(2015,01,01).and_hms(15,24,58),
                UTC.ymd(2015,01,01).and_hms(15,29,56),
                UTC.ymd(2015,01,01).and_hms(15,36,36),
        ];
        let vec = random_times(&op1, &mut ran_doom);
        assert_eq!(vec1, vec);
    }

    #[test]
    pub fn test_crossing(){
        println!("");
        let mut ran_doom = XorShiftRng::new_unseeded();
        let (opt, mut g1, mut g2, g3) = testgenomes();
        
        // for activity in g1.values() {
        //     println!("{:?}", activity);
        // }
        // println!("");
        // for activity in g2.values() {
        //     println!("{:?}", activity);
        // }

        let mut vec = vec!( 
                UTC.ymd(2015,02,1).and_hms(6,0,0),
                UTC.ymd(2015,02,1).and_hms(9,0,0),
                UTC.ymd(2015,02,1).and_hms(12,0,0),
        );
        let (g1, g2) = crossover(&opt, g1, g2, &mut vec);
        // let (g1, g2) = crossover(&opt, g1, g2, &mut vec);

        println!("");
        println!("");
        for activity in g1.values() {
            println!("{:?}", activity);
        }
        println!("");
        for activity in g2.values() {
            println!("{:?}", activity);
        }
         

        g1.get(&UTC.ymd(2015,02,1).and_hms(12,0,0)).unwrap();
        g2.get(&UTC.ymd(2015,02,1).and_hms(8,0,0)).unwrap();
    }

}
