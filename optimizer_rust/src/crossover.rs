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
use ::genome::{Optimization};
use chrono::{DateTime, UTC, Duration};

fn random_time<T: Rng>(opt: &Optimization, randomizer: &mut T)
        -> DateTime<UTC> {
    opt.start.clone() + Duration::seconds(
        randomizer.gen_range(0, opt.duration().num_seconds()))
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

pub mod tests {
    use std::rand::XorShiftRng;
    use chrono::UTC;
    use chrono::Offset;

    use super::random_times;

    use ::genome::{Genome, Optimization};
    use ::genome::tests::testtree;


    #[test]
    pub fn test_random_times(){
        let mut ranDOOM = XorShiftRng::new_unseeded();
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
        let vec = random_times(&op1, &mut ranDOOM);
        assert_eq!(vec1, vec);
        println!("{:?}", vec);
    }
}
