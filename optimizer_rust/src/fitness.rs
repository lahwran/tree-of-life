use std::rc::Rc;
use std::collections::HashMap;
use std::num::Float;
use std::mem;

use chrono::Duration;

use super::genome::{Genome, Optimization, NodeRef, Node, NodeExt};


// is f64 okay? do we want f32?
pub type Fitness = f64;

pub trait FitnessFunction {
    fn fitness(&self, opt: &Optimization, genome: &Genome) -> Fitness;
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
        let nref = node.id_key();
        if !self.nodestates.contains_key(&nref) {
            self.nodestates.insert(nref, NodeState::new());
        }
        self.nodestates.get_mut(&nref).unwrap()
    }

    fn balance_quality(&self, opt: &Optimization) -> Fitness {
        let times = opt.projects
                    .iter()
                    .map(|proj| self.nodestates.get(&proj.id_key()).unwrap())
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

struct PairIter<T, I>
        where I: Iterator<Item = T>, T: Copy {
    prev: T,
    iter: I
}

impl<T, I> PairIter<T, I>
        where I: Iterator<Item = T>, T: Copy {
    fn new(iterator: I) -> PairIter<T, I> {
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
    fn fitness(&self, opt: &Optimization, genome: &Genome) -> Fitness {
        let treestate = TreeState::new(opt);
        let mut fitness = 100f64;


        //genome.0.iter().scan(None, |state, b| {
        //    match state {
        //        None => {
        //            mem::replace(state, Some(b));
        //        },
        //        Some(prev) => {
        //        }
        //    }
        //    let a = mem::replace(prev, b);
        //    Some((mem::replace(prev, x), x))
        //})
        //for (index, ()) in {
        //}

        0f64
    }
}
