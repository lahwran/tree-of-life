#[allow(dead_code)]
#[allow(unused_variables)]

use std::rc::Rc;
use std::collections::BTreeMap;
use std::collections::btree_map;
use std::collections::Bound;
use std::slice::SliceExt;

use chrono::{UTC, DateTime, Offset, Duration};

use self::NodeType::{Root, Project, Task};
use self::ActivityType::{Nothing, WorkOn, Finish};
use ::core::Fitness;

#[derive(Debug, Clone)]
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

#[derive(Debug)]
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
}

#[derive(Debug, Clone)]
pub struct Genome {
    genome: BTreeMap<DateTime<UTC>,Activity>,
    pub cached_fitness: Option<Fitness>
}

impl Genome {
    pub fn new_empty() -> Genome {
        Genome {
            genome: BTreeMap::new(),
            cached_fitness: None
        }
    }

    pub fn new(opt: &Optimization) -> Genome{
        let mut result = Genome::new_empty();
        result.insert(Activity {
            start: opt.start.clone(),
            activitytype: Nothing
        });
        result.insert(Activity {
            start: opt.end.clone(),
            activitytype: Nothing
        });

        result
    }

    pub fn preinit(entries: Vec<(i32, u32, u32, u32, u32, ActivityType)>)
            -> Genome {
        let mut result = Genome::new_empty();

        for (year, month, day, hour, minute, activity)
                in entries.into_iter() {
            result.insert(Activity {
                start: UTC.ymd(year, month, day).and_hms(hour, minute, 0),
                activitytype: activity
            });
        }
        result
    }

    pub fn insert(&mut self, activity: Activity) {
        self.genome.insert(activity.start.clone(), activity);
        self.cached_fitness = None;
    }
    pub fn get(&self, time: &DateTime<UTC>) -> Option<&Activity>{
        self.genome.get(time)
    }

    pub fn values<'a>(&'a self) ->
            btree_map::Values<'a, DateTime<UTC>, Activity> {
        self.genome.values()
    }

    pub fn range<'a>(&'a self, min: Bound<&DateTime<UTC>>, max: Bound<&DateTime<UTC>>) ->
            btree_map::Range<'a, DateTime<UTC>, Activity> {
        self.genome.range(min, max)
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
}

pub mod tests {
    use super::{Optimization, Genome, Node, NodeExt};
    use super::NodeType::{Project, Task};
    use super::ActivityType::{WorkOn, Finish};

    use test::Bencher;

    use std::rc::Rc;
    use std::rand::{Rng, XorShiftRng};
    use chrono::{UTC, Offset};

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

    pub fn testtree() -> Rc<Node> {
        Node::new_root(vec![
            Node::new_parent(Project, "Project Name", vec![
                Node::new(Task, "Task Name"),
            ]),
            Node::new(Project, "Another project name"),
            Node::new(Project, "Herp derp"),
        ])
    }

    pub fn testgenome() -> (Optimization, Genome) { 
        let tree = testtree();

        let opt = Optimization::new(
            UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
            UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
            tree
        );

        let genome = Genome::preinit(vec![
            (2015, 2, 12, 0, 0, WorkOn(opt.tree.children[0].clone())),
            (2015, 2, 14, 0, 0, Finish(opt.tree.children[1].clone())),
            (2015, 2, 15, 0, 0, Finish(opt.tree.children[2].clone())),
        ]);

        (opt, genome)
    }
    
    pub fn testgenomes() -> (Optimization, Genome, Genome, Genome) { 
        let tree = testtree();
        let mut genomes = Vec::<Genome>::new();
        let mut rand = XorShiftRng::new_unseeded();
        rand.next_u32();

        let opt = Optimization::new(
            UTC.ymd(2015, 2, 1).and_hms(0, 0, 0),
            UTC.ymd(2015, 2, 2).and_hms(0, 0, 0),
            tree
        );
        let g1 = Genome::preinit(vec![
                (2015, 2, 1, 0, 0, WorkOn(opt.tree.children[1].clone())),
                (2015, 2, 1, 3, 0, WorkOn(opt.tree.children[1].clone())),
                (2015, 2, 1, 8, 0, WorkOn(opt.tree.children[1].clone())),
                (2015, 2, 1, 11, 0, Finish(opt.tree.children[1].clone())),
                (2015, 2, 1, 19, 0, Finish(opt.tree.children[1].clone()))
            ]);
        let g2 = Genome::preinit(vec![
                (2015, 2, 1, 0, 0, WorkOn(opt.tree.children[2].clone())),
                (2015, 2, 1, 6, 0, WorkOn(opt.tree.children[2].clone())),
                (2015, 2, 1, 10, 0, WorkOn(opt.tree.children[2].clone())),
                (2015, 2, 1, 12, 0, Finish(opt.tree.children[2].clone())),
                (2015, 2, 1, 23, 0, Finish(opt.tree.children[2].clone()))
            ]);
        let g3 = Genome::preinit(vec![
                (2015, 2, 1, 0, 0, WorkOn(opt.tree.children[0].clone())),
                (2015, 2, 1, 4, 0, WorkOn(opt.tree.children[0].clone())),
                (2015, 2, 1, 9, 0, WorkOn(opt.tree.children[0].clone())),
                (2015, 2, 1, 12, 0, Finish(opt.tree.children[0].clone())),
                (2015, 2, 1, 22, 0, Finish(opt.tree.children[0].clone()))
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
                (2015, 2, 12, 0, 0, WorkOn(opt.tree.children[0].clone())),
                (2015, 2, 14, 0, 0, Finish(opt.tree.children[1].clone())),
                (2015, 2, 15, 0, 0, Finish(opt.tree.children[2].clone())),
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
