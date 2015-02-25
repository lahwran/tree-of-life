use rand::Rng;

use ::genome::{Genome,Optimization,NodeExt,Activity};
use ::genome::ActivityType::WorkOn;

pub fn add_gene<R: Rng>(opt: &Optimization, genome: &mut Genome, rng: &mut R) {
    let node = opt.tree.randomnode(rng);
    let insert_time = opt.random_time(rng);

    let gene = Activity {
        start: insert_time,
        activitytype: WorkOn(node)
    };

    genome.insert(gene);
}

pub fn mutate(genome: &mut Genome) {
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
