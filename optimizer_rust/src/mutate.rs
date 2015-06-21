use std::mem;

use rand::Rng;

use ::model::genome::{Genome, Optimization, NodeExt, Activity};
use ::model::genome::ActivityType::WorkOn;
use ::tuneables::{ADD_MAX, ADD_CURVE_EXPONENT, DEL_TARGET, DEL_CURVE_EXPONENT};

pub fn add_gene<R: Rng>(opt: &Optimization, genome: &mut Genome, rng: &mut R) {
    let node = opt.tree.randomnode(rng);
    let insert_time = opt.random_time(rng);

    let gene = Activity {
        start: insert_time,
        activitytype: WorkOn(node)
    };

    genome.pool.push(gene);
}

pub fn mutate<R: Rng>(opt: &Optimization, genome: &mut Genome, rng: &mut R) {
    let add_count = (
                ADD_MAX * rng.next_f64().powi(ADD_CURVE_EXPONENT)) as usize;
    let del_thresh = DEL_TARGET * rng.next_f64().powi(DEL_CURVE_EXPONENT);

    let mut prev_genome = Genome::new_empty(genome.pool.len() * 2);
    mem::swap(&mut prev_genome, genome);
    let prev_genome_len = prev_genome.pool.len();

    for (index, gene) in prev_genome.pool.drain(..).enumerate() {
        if index == prev_genome_len - 1 {
            genome.pool.push(gene);
            break;
        }
        if rng.next_f64() * (prev_genome_len as f64) < del_thresh {
            continue;
        }
        genome.pool.push(gene);
    }

    for _ in 0..add_count {
        // TODO: need to try to match distributions between delete and add :(
        add_gene(opt, genome, rng);
    }

    genome.sort();
}


#[cfg(test)]
pub mod tests {
    use rand::XorShiftRng;
    use chrono::{UTC, Duration, TimeZone};

    use ::model::genome::{Genome,Optimization};
    use ::model::genome::ActivityType::{WorkOn,Nothing};
    use ::model::genome::testtree;

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
        genome.sort();

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
