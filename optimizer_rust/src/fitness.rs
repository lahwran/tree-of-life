use std::rc::Rc;
use std::collections::HashMap;
use std::num::Float;
use std::mem;

use chrono::Duration;

use ::genome::{Genome, Optimization, NodeRef, Node, NodeExt};
use ::genome::ActivityType::{Nothing, WorkOn, Finish};


// is f64 okay? do we want f32?
pub type Fitness = f64;

pub trait FitnessFunction {
    fn fitness(&self, genome: &Genome) -> Fitness;
}

struct NodeState {
    focus_so_far: Duration,
}

impl NodeState {
    fn new() -> NodeState {
        NodeState {
            focus_so_far: Duration::seconds(0)
        }
    }
}

struct TreeState {
    nodestates: HashMap<NodeRef,NodeState>,
}

impl TreeState {
    fn new(opt: &Optimization) -> TreeState {
        let mut result = TreeState {
            nodestates: HashMap::with_capacity(opt.tree.subtreesize)
        };
        for project in &opt.projects {
            result.get(project);
        }
        return result;
    }

    fn get(&mut self, node: &Rc<Node>) -> &mut NodeState {
        let nref = node.id();
        if !self.nodestates.contains_key(&nref) {
            self.nodestates.insert(nref, NodeState::new());
        }
        self.nodestates.get_mut(&nref).unwrap()
    }

    fn balance_quality(&self, opt: &Optimization) -> Fitness {
        let times = opt.projects
                    .iter()
                    .map(|proj| self.nodestates.get(&proj.id()).unwrap())
                    .map(|nodestate| nodestate.focus_so_far.num_seconds() as f64)
                    .collect::<Vec<f64>>();
        if times.len() == 0 {
            return 1.0f64;
        }
        let average = times.iter().fold(0f64, |x, y| x + *y);
        if average == 0f64 {
            return 0f64;
        }
        let deltas = times.iter().map(|time| (time - average).powi(2));
        let variance = deltas.fold(0f64, |x, y| x + y);
        let stddev = variance.sqrt();
        assert!(!stddev.is_nan());
        // had to look this one up:
        // http://en.wikipedia.org/wiki/Coefficient_of_variation
        let cv = stddev / average;

        // cv is typically 0.1-ish, but ranges to infinity.
        // to get the result to be returned as a quality percentage,
        // 1 / (1.1)  which is 0.9 or so is preferable.
        1f64 / (cv + 1f64)
    }
}

pub struct PairIter<T, I>
        where I: Iterator<Item = T>, T: Copy {
    prev: T,
    iter: I
}

impl<T, I> PairIter<T, I>
        where I: Iterator<Item = T>, T: Copy {
    pub fn new(iterator: I) -> PairIter<T, I> {
        let mut iterator = iterator;
        PairIter {
            prev: iterator.next().unwrap(),
            iter: iterator
        }
    }
}

impl<T, I> Iterator for PairIter<T, I>
        where I: Iterator<Item = T>, T: Copy {
    type Item = (T, T);

    fn next(&mut self) -> Option<(T, T)> {
        match self.iter.next() {
            None => None,
            Some(value) =>
                Some((mem::replace(&mut self.prev, value),
                value))
        }

    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.iter.size_hint()
    }
}

#[derive(Debug)]
struct A(i32);

pub fn vec_pairs() {
    let x = vec![A(1), A(2), A(3), A(4), A(5)];
    let y = PairIter::new(x.iter()).collect::<Vec<(&A, &A)>>();
    println!("{:?}", y);
}


impl FitnessFunction for Optimization {
    fn fitness(&self, genome: &Genome) -> Fitness {
        let mut treestate = TreeState::new(self);
        let mut fitness = 100f64;
        let mut total_time_working = Duration::seconds(0);

        for (first, second) in PairIter::new(genome.values()) {
            let activity = match first.activitytype {
                Nothing => { continue; },
                Finish(_) => {
                    fitness *= 0.95;
                    continue;
                },
                WorkOn(ref a) => a
            };
            match second.activitytype {
                WorkOn(ref second_a) if activity.id() == second_a.id() => {
                    fitness *= 0.95;
                },
                _ => ()
            };

            let state = treestate.get(activity);
            let delta = second.start.clone() - first.start.clone();
            state.focus_so_far = state.focus_so_far + delta;
            total_time_working = total_time_working + delta;
        }
        fitness *= total_time_working.num_seconds() as f64
                    / self.duration().num_seconds() as f64;
        fitness *= treestate.balance_quality(self);

        fitness
    }
}

mod tests {
    use super::FitnessFunction;

    use ::genome::{Genome, Optimization};
    use ::genome::tests::testtree;
    use ::genome::ActivityType::{Nothing, WorkOn};

    use chrono::{TimeZone, UTC};

    use test::Bencher;

    #[test]
    fn balanced_gets_good_rating() {
        let tree = testtree();
        let genome1 = Genome::preinit(vec![
            (2015, 1, 1, 15, 20, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 30, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 40, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, Nothing),
        ]);
        let opt1 = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 20, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );

        let f1 = opt1.fitness(&genome1);

        let genome2 = Genome::preinit(vec![
            (2015, 1, 1, 15, 0 , WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 30, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 40, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, Nothing)
        ]);
        let opt2 = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 0, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );
        let f2 = opt2.fitness(&genome2);
        assert!(f1 > f2);
    }

    #[test]
    fn more_time_rating() {
        let tree = testtree();
        let opt = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 0, 0),
            UTC.ymd(2015, 1, 1).and_hms(16, 0, 0),
            tree.clone()
        );

        let genome1 = Genome::preinit(vec![
            (2015, 1, 1, 15, 20, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 50, Nothing)
        ]);
        let f1 = opt.fitness(&genome1);

        let genome2 = Genome::preinit(vec![
            (2015, 1, 1, 15, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 50, Nothing)
        ]);
        let f2 = opt.fitness(&genome2);
        assert!(f1 < f2);
    }

    #[bench]
    fn benchmark_fitness_run_small(bencher: &mut Bencher) {
        let tree = testtree();
        let opt = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 20, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );
        let genome = Genome::preinit(vec![
            (2015, 1, 1, 15, 20, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 30, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 40, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, Nothing),
        ]);

        bencher.iter(|| {
            opt.fitness(&genome);
        });
    }

    #[bench]
    fn benchmark_fitness_run_big(bencher: &mut Bencher) {
        let tree = testtree();
        let opt = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 20, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );
        let genome = Genome::preinit(vec![
            (2015, 1, 1, 15, 20, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 21, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 22, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 23, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 24, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 25, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 26, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 27, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 28, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 29, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 31, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 32, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 33, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 34, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 35, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, Nothing),
        ]);

        bencher.iter(|| {
            opt.fitness(&genome);
        });
    }
}
