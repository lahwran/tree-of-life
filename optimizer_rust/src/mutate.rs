use std::num::Float;

use rand::Rng;

use ::genome::{Genome,Optimization,NodeExt,Activity};
use ::genome::ActivityType::WorkOn;
use ::tuneables::{ADD_MAX, ADD_CURVE_EXPONENT, DEL_TARGET, DEL_CURVE_EXPONENT};

pub fn add_gene<R: Rng>(opt: &Optimization, genome: &mut Genome, rng: &mut R) {
    let node = opt.tree.randomnode(rng);
    let insert_time = opt.random_time(rng);

    let gene = Activity {
        start: insert_time,
        activitytype: WorkOn(node)
    };

    genome.insert(gene);
}

pub fn mutate<R: Rng>(opt: &Optimization, genome: &mut Genome, rng: &mut R) {
    let add_count = (
                ADD_MAX * rng.next_f64().powi(ADD_CURVE_EXPONENT)) as usize;
    let del_thresh = DEL_TARGET * rng.next_f64().powi(DEL_CURVE_EXPONENT);
    let mut del_keys = Vec::with_capacity(del_thresh as usize * 2);

    for value in genome.values().take(genome.len()-1) {
        if rng.next_f64() * (genome.len() as f64) < del_thresh {
            del_keys.push(value.start.clone());
        }
    }

    for key in del_keys {
        genome.remove(&key);
    }

    for _ in 0..add_count {
        // TODO: need to try to match distributions between delete and add :(
        add_gene(opt, genome, rng);
    }
}


pub mod tests {
    use rand::XorShiftRng;
    use chrono::{UTC, Duration, TimeZone};

    use ::genome::{Genome,Optimization};
    use ::genome::ActivityType::{WorkOn,Nothing};
    use ::genome::tests::testtree;

    use super::add_gene;


    #[test]
    fn test_add_gene() {
        let tree = testtree();
        let mut genome = Genome::preinit(vec![
            (2015, 1, 1, 11, 00,  0, WorkOn(tree.children[0].clone())),
            (2015, 1, 7, 12, 15,  0, WorkOn(tree.children[1].clone())),
            (2015, 1, 15, 12, 50, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 25, 14, 15, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 29, 16, 00, 0, Nothing)
        ]);
        let opt = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(11, 0, 0),
            UTC.ymd(2015, 1, 1).and_hms(11, 0, 0) + Duration::days(30),
            tree.clone()
        );

        let mut rng = XorShiftRng::new_unseeded();
        add_gene(&opt, &mut genome, &mut rng);

        assert_eq!(genome, Genome::preinit(vec![
            (2015, 1, 1, 11, 00,  0,  WorkOn(tree.children[0].clone())),
            (2015, 1, 7, 12, 15,  0,  WorkOn(tree.children[1].clone())),
            (2015, 1, 15, 12, 50, 0,  WorkOn(tree.children[2].clone())),
            (2015, 1, 19, 05, 46, 36, WorkOn(tree.children[0].clone())),
            (2015, 1, 25, 14, 15, 0,  WorkOn(tree.children[0].clone())),
            (2015, 1, 29, 16, 00, 0,  Nothing)
        ]));
    }
}
