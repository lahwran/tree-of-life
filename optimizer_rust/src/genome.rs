use std::rc::Rc;
use std::collections::BTreeMap;
use std::collections::btree_map;
use std::collections::Bound;
use std::slice::SliceExt;
use std::cmp;
use std::fmt;

use rand::Rng;
use chrono::{UTC, DateTime, Duration};
use chrono::offset::TimeZone;

use self::NodeType::{Root, Project, Task};
use self::ActivityType::{Nothing, WorkOn, Finish};
use ::core::Fitness;

#[derive(Debug, Clone, PartialEq)]
pub struct Activity {
    pub start: DateTime<UTC>,
    pub activitytype: ActivityType,
}

#[derive(Debug, Clone)]
pub enum ActivityType {
    Nothing,
    WorkOn(Rc<Node>),
    Finish(Rc<Node>),
}

pub struct Node {
    pub nodetype: NodeType,
    pub name: String,
    pub children: Vec<Rc<Node>>,
    pub subtreesize: usize
}

#[derive(Debug)]
pub enum NodeType {
    Root,
    Project,
    Task,
}

impl cmp::PartialEq for ActivityType {
    fn eq(&self, other: &ActivityType) -> bool {
        match (self, other) {
            (&Nothing, &Nothing) => true,
            (&WorkOn(ref a), &WorkOn(ref b))
            | (&Finish(ref a), &Finish(ref b)) => {
                a.id() == b.id()
            },
            _ => false
        }
    }
}

impl Node {
    pub fn new_parent(nodetype: NodeType, name: &str, children: Vec<Rc<Node>>)
            -> Rc<Node> {
        Rc::new(Node {
            nodetype: nodetype,
            name: name.to_string(),
            subtreesize: children.len() + children.iter().fold(0, |v, x| {
                (&**x).subtreesize + v
            }),
            children: children
        })
    }

    pub fn new_root(children: Vec<Rc<Node>>) -> Rc<Node> {
        Node::new_parent(Root, "life", children)
    }

    pub fn new(nodetype: NodeType, name: &str) -> Rc<Node> {
        Rc::new(Node {
            nodetype: nodetype,
            name: name.to_string(),
            children: vec![],
            subtreesize: 0
        })
    }
}

#[allow(raw_pointer_derive)]
#[derive(Hash, PartialEq, Eq, Debug, Copy)]
pub struct NodeRef(*const Node);

pub trait NodeExt {
    fn id(&self) -> NodeRef;
    fn walk<F: FnMut(&Self)>(&self, callback: &mut F);
    fn find_node(&self, index: usize) -> Rc<Node>;
    fn randomnode<R: Rng>(&self, rng: &mut R) -> Rc<Node>;
}

impl NodeExt for Rc<Node> {
    #[inline]
    fn id(&self) -> NodeRef {
        NodeRef(&**self as *const Node)
    }

    fn walk<F: FnMut(&Self)>(&self, callback: &mut F) {
        callback(self);
        for child in &self.children {
            child.walk(callback);
        }
    }

    /// Find a node by index. *panics on out of bounds*
    fn find_node(&self, index: usize) -> Rc<Node> {
        let mut parent_iterator = self.children.iter();
        let mut current_index: usize = 0;
        let mut current_node = parent_iterator.next().unwrap();

        while current_index < index {

            current_index += 1;

            if current_index + current_node.subtreesize > index {
                parent_iterator = current_node.children.iter();
                current_node = parent_iterator.next().unwrap();
            } else {
                current_index += current_node.subtreesize;
                current_node = parent_iterator.next().unwrap();
            }
        }
        assert_eq!(current_index, index);
        return current_node.clone();
    }

    fn randomnode<R: Rng>(&self, rng: &mut R) -> Rc<Node> {
        self.find_node(rng.gen_range(0, self.subtreesize))
    }
}

#[derive(Clone)]
pub struct Genome {
    pub pool: Vec<Activity>,
    pub cached_fitness: Option<Fitness>
}

impl cmp::PartialEq for Genome {
    fn eq(&self, other: &Genome) -> bool {
        self.pool == other.pool
    }
}

impl fmt::Debug for Genome {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        try!(write!(f, "Genome {{ fitness: {:?},\n", self.cached_fitness));
        for node in &self.pool {
            try!(write!(f, "    {:?},\n", node));
        }
        write!(f, "}}")
    }
}

impl fmt::Debug for Node {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Node {{ nodetype: {:?}, name: {:?}, children: ..., subtreesize: {:?} }}",
               self.nodetype, self.name, self.subtreesize)
    }
}

impl Genome {
    pub fn new_empty(expected_size: usize) -> Genome {
        Genome {
            pool: Vec::with_capacity(expected_size),
            cached_fitness: None
        }
    }

    pub fn new(opt: &Optimization) -> Genome{
        let mut result = Genome::new_empty(2);
        result.pool.push(Activity {
            start: opt.start.clone(),
            activitytype: Nothing
        });
        result.pool.push(Activity {
            start: opt.end.clone(),
            activitytype: Nothing
        });

        result
    }

    pub fn preinit(entries: Vec<(i32, u32, u32, u32, u32, u32, ActivityType)>)
            -> Genome {
        let mut result = Genome::new_empty(15);

        for (year, month, day, hour, minute, second, activity)
                in entries.into_iter() {
            result.pool.push(Activity {
                start: UTC.ymd(year, month, day).and_hms(hour, minute, second),
                activitytype: activity
            });
        }
        result
    }

    /// this is only for testing, to make initializing with fitness easier.
    pub fn with_fitness(mut self, fitness: Fitness) -> Genome {
        self.cached_fitness = Some(fitness);

        self
    }

    pub fn sort(&mut self) {
        self.pool.sort_by(|a, b| a.start.cmp(&b.start));
    }
}

#[derive(Debug, Clone)]
pub struct Optimization {
    pub start: DateTime<UTC>,
    pub end: DateTime<UTC>,
    pub tree: Rc<Node>,
    pub projects: Vec<Rc<Node>>
}

impl Optimization {
    pub fn new(start: DateTime<UTC>,
               end: DateTime<UTC>,
               tree: Rc<Node>) -> Optimization {
        let mut projects = vec![];
        tree.walk(&mut |node: &Rc<Node>| {
            match &(**node).nodetype {
                &Project => projects.push(node.clone()),
                _ => ()
            };
        });
        Optimization {
            start: start,
            end: end,
            tree: tree,
            projects: projects
        }
    }

    pub fn duration(&self) -> Duration {
        self.end.clone() - self.start.clone()
    }

    pub fn random_time<T: Rng>(&self, randomizer: &mut T)
            -> DateTime<UTC> {
        self.start.clone() + Duration::seconds(
            randomizer.gen_range(0, self.duration().num_seconds()))
    }
}

pub fn testtree() -> Rc<Node> {
    Node::new_root(vec![
        Node::new_parent(Project, "Project Name", vec![
            Node::new(Task, "Task Name"),
        ]),
        Node::new(Project, "Another project name"),
        Node::new(Project, "Herp derp"),
    ])
}

#[cfg(test)]
pub mod tests {
    use super::{Optimization, Genome, Node, NodeExt};
    use super::NodeType::Project;
    use super::ActivityType::{WorkOn, Finish};
    use super::testtree;

    use test::Bencher;

    use rand::{Rng, XorShiftRng};
    use chrono::{TimeZone, UTC};

    #[test]
    fn test_noderef_eq() {
        let node = Node::new(Project, "derp");
        let node2 = Node::new(Project, "derp");

        let nref = node.id();
        let nref2 = node.id();

        let nref3 = node2.id();

        assert_eq!(nref, nref2);
        assert!(nref != nref3);
    }

    pub fn testgenome() -> (Optimization, Genome) {
        let tree = testtree();

        let opt = Optimization::new(
            UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
            UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
            tree
        );

        let genome = Genome::preinit(vec![
            (2015, 2, 12, 0, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 14, 0, 0, 0, Finish(opt.tree.children[1].clone())),
            (2015, 2, 15, 0, 0, 0, Finish(opt.tree.children[2].clone())),
        ]);

        (opt, genome)
    }

    pub fn testgenomes() -> (Optimization, Genome, Genome, Genome) {
        let tree = testtree();
        let mut rand = XorShiftRng::new_unseeded();
        rand.next_u32();

        let opt = Optimization::new(
            UTC.ymd(2015, 2, 1).and_hms(0, 0, 0),
            UTC.ymd(2015, 2, 2).and_hms(0, 0, 0),
            tree
        );
        let g1 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1,  3, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1,  8, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 1, 11, 0, 0, Finish(opt.tree.children[0].clone())),
            (2015, 2, 1, 19, 0, 0, Finish(opt.tree.children[0].clone()))
        ]);
        let g2 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[1].clone())),
            (2015, 2, 1,  6, 0, 0, WorkOn(opt.tree.children[1].clone())),
            (2015, 2, 1, 10, 0, 0, WorkOn(opt.tree.children[1].clone())),
            (2015, 2, 1, 12, 0, 0, Finish(opt.tree.children[1].clone())),
            (2015, 2, 1, 23, 0, 0, Finish(opt.tree.children[1].clone()))
        ]);
        let g3 = Genome::preinit(vec![
            (2015, 2, 1,  0, 0, 0, WorkOn(opt.tree.children[2].clone())),
            (2015, 2, 1,  4, 0, 0, WorkOn(opt.tree.children[2].clone())),
            (2015, 2, 1,  9, 0, 0, WorkOn(opt.tree.children[2].clone())),
            (2015, 2, 1, 12, 0, 0, Finish(opt.tree.children[2].clone())),
            (2015, 2, 1, 22, 0, 0, Finish(opt.tree.children[2].clone()))
        ]);
        (opt, g1, g2, g3)

    }

    #[bench]
    pub fn benchmark_genome_create(b: &mut Bencher) {
        let tree = testtree();

        let opt = Optimization::new(
            UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
            UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
            tree
        );

        b.iter(|| {
            Genome::preinit(vec![
                (2015, 2, 12, 0, 0, 0, WorkOn(opt.tree.children[0].clone())),
                (2015, 2, 14, 0, 0, 0, Finish(opt.tree.children[1].clone())),
                (2015, 2, 15, 0, 0, 0, Finish(opt.tree.children[2].clone())),
            ]);
        });
    }

    #[test]
    fn subtree_counts() {
        let tree = testtree();
        assert_eq!(&tree.subtreesize, &4);
        assert_eq!(&tree.children[0].subtreesize, &1);
        assert_eq!(&tree.children[1].subtreesize, &0);
        assert_eq!(&tree.children[2].subtreesize, &0);
    }

    pub fn genomerun() {
        let (_, genome) = testgenome();

        println!("{:?}", genome);
    }
}
