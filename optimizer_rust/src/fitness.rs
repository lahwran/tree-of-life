use std::rc::Rc;
use std::collections::HashMap;
use std::mem;

use chrono::Duration;

use ::model::genome::{Genome, Optimization, NodeRef, Node, NodeExt};
use ::model::genome::ActivityType::{Nothing, WorkOn, Finish};
use ::model::genome::NodeType::Project;
use ::model::log::LogEntry;
use ::model::log::LogKind::Activation;
use ::model::log::LogNode::{Exists, Gone};


// is f64 okay? do we want f32?
pub type Fitness = f64;

#[derive(Clone)]
struct NodeState {
    focus_so_far: Duration,
}

impl NodeState {
    fn new() -> NodeState {
        NodeState {
            focus_so_far: Duration::seconds(0)
        }
    }

    fn add_time(&mut self, delta: Duration) {
        self.focus_so_far = self.focus_so_far + delta;
    }
}

#[derive(Clone)]
pub struct TreeState {
    nodestates: HashMap<NodeRef,NodeState>,
    total_time_working: Duration
}

impl TreeState {
    pub fn new(opt: &Optimization) -> TreeState {
        let mut result = TreeState {
            nodestates: HashMap::with_capacity(opt.tree.subtreesize),
            total_time_working: Duration::seconds(0)
        };
        for project in &opt.projects {
            result.get(project);
        }

        result
    }

    fn get(&mut self, node: &Rc<Node>) -> &mut NodeState {
        let nref = node.id();
        self.nodestates.entry(nref).or_insert_with(|| NodeState::new())
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
        let average = times.iter().fold(0f64, |x, y| x + *y)
                        / times.len() as f64;
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
        let result = 1f64 / (cv + 1f64);

        //println!("t:{:?}, a:{:?}, d:{:?}, v:{:?}, s:{:?}, c:{:?}, r:{:?}",
        //         times, average, deltas, variance, stddev, cv, result);
        result
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

fn last_project(e: &LogEntry) -> Option<&Rc<Node>> {
    for lognode in e.nodes.iter().rev() {
        let node = match lognode {
            &Exists(ref node) => node,
            &Gone => { continue; }
        };
        match &node.nodetype {
            &Project => {
                return Some(node);
            },
            _ => { continue; }
        }
    }

    None
}

pub fn prepare_state(log: Vec<LogEntry>, opt: &Optimization) -> TreeState {
    let mut treestate = TreeState::new(opt);
    let iterator = log.iter().filter(|x| x.kind == Activation);
    for (first, second) in PairIter::new(iterator) {
        let node = match last_project(first) {
            None => { continue; },
            Some(node) => node
        };
        let delta = first.time.clone() - second.time.clone();
        treestate.total_time_working = treestate.total_time_working + delta;
        treestate.get(node).add_time(delta);
    }

    treestate
}

pub fn fitness(initial_state: &TreeState, opt: &Optimization, genome: &Genome)
        -> Fitness {
    let mut treestate = initial_state.clone();
    let mut fitness = 100f64;

    for (first, second) in PairIter::new(genome.pool.iter()) {
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
        if let Project = activity.nodetype {} else {
            fitness *= 0.95;
        }

        let delta = second.start.clone() - first.start.clone();
        treestate.total_time_working = treestate.total_time_working + delta;
        treestate.get(activity).add_time(delta);
    }
    //println!("fitness before total time scaling: {:?}", fitness);
    fitness *= treestate.total_time_working.num_seconds() as f64
                / opt.duration().num_seconds() as f64;
    //println!("fitness before balance quality: {:?}", fitness);
    fitness *= treestate.balance_quality(opt);
    //println!("final fitness: {:?}", fitness);

    fitness
}

#[cfg(test)]
mod tests {
    use super::{fitness,TreeState};
    use ::model::genome::{Genome, Optimization};
    use ::model::genome::testtree;
    use ::model::genome::ActivityType::{Nothing, WorkOn};

    use chrono::{TimeZone, UTC};

    use test::Bencher;

    #[test]
    fn balanced_gets_good_rating() {
        let tree = testtree();
        let genome1 = Genome::preinit(vec![
            (2015, 1, 1, 15, 20, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 30, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 40, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, 0, Nothing),
        ]);
        let opt1 = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 20, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );

        let treestate1 = TreeState::new(&opt1);
        let f1 = fitness(&treestate1, &opt1, &genome1);

        let genome2 = Genome::preinit(vec![
            (2015, 1, 1, 15,  0, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 30, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 40, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, 0, Nothing)
        ]);
        let opt2 = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(15, 0, 0),
            UTC.ymd(2015, 1, 1).and_hms(15, 50, 0),
            tree.clone()
        );
        let treestate2 = TreeState::new(&opt2);
        let f2 = fitness(&treestate1, &opt2, &genome2);
        assert!(f1 > f2);
    }

    #[test]
    fn test_perfect_genome() {
        let tree = testtree();
        let opt = Optimization::new(
            UTC.ymd(2015, 1, 1).and_hms(0, 0, 0),
            UTC.ymd(2015, 1, 4).and_hms(0, 0, 0),
            tree.clone()
        );
        let genome = Genome::preinit(vec![
            (2015, 1, 1,  0,  0, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 2,  0,  0, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 3,  0,  0, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 4,  0,  0, 0, Nothing)
        ]);
        let treestate = TreeState::new(&opt);
        let f = fitness(&treestate, &opt, &genome);
        assert!((99.99 < f) && (f < 100.001));
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
            (2015, 1, 1, 15, 20, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 50, 0, Nothing)
        ]);
        let treestate = TreeState::new(&opt);
        let f1 = fitness(&treestate, &opt, &genome1);

        let genome2 = Genome::preinit(vec![
            (2015, 1, 1, 15,  0, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 50, 0, Nothing)
        ]);
        let f2 = fitness(&treestate, &opt, &genome2);
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
            (2015, 1, 1, 15, 20, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 30, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 40, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, 0, Nothing),
        ]);

        let treestate = TreeState::new(&opt);
        bencher.iter(|| {
            fitness(&treestate, &opt, &genome);
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
            (2015, 1, 1, 15, 20, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 21, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 22, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 23, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 24, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 25, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 26, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 27, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 28, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 29, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 31, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 32, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 33, 0, WorkOn(tree.children[0].clone())),
            (2015, 1, 1, 15, 34, 0, WorkOn(tree.children[1].clone())),
            (2015, 1, 1, 15, 35, 0, WorkOn(tree.children[2].clone())),
            (2015, 1, 1, 15, 50, 0, Nothing),
        ]);

        let treestate = TreeState::new(&opt);
        bencher.iter(|| {
            fitness(&treestate, &opt, &genome);
        });
    }
}
