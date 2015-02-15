use std::rc::Rc;
use std::collections::HashMap;
use std::num::Float;

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

impl FitnessFunction for Optimization {
    fn fitness(&self, opt: &Optimization, genome: &Genome) -> Fitness {
        let treestate = TreeState::new(opt);

        0f64
    }
}
