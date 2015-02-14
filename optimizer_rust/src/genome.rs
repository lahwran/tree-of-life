#[allow(dead_code)]
#[allow(unused_variables)]

use std::rc::Rc;
use std::collections::BTreeMap;

use chrono::{UTC, DateTime, Offset};

use self::NodeType::{Root, Project, Task};
use self::ActivityType::{Nothing, WorkOn, Finish};

#[derive(Debug)]
pub struct Activity {
    start: DateTime<UTC>,
    activitytype: ActivityType,
}

#[derive(Debug)]
pub enum ActivityType {
    Nothing,
    WorkOn(Rc<Node>),
    Finish(Rc<Node>),
}

#[derive(Debug)]
pub struct Node {
    nodetype: NodeType,
    name: String,
    children: Vec<Rc<Node>>,
    subtreesize: usize
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

#[derive(Hash, PartialEq, Eq, Debug)]
pub struct NodeRef(usize);

pub trait ConvertToInt {
    fn toint(&self) -> NodeRef;
}

impl ConvertToInt for Rc<Node> {
    #[inline]
    fn toint(&self) -> NodeRef {
        NodeRef(&**self as *const _ as usize)
    }
}

#[test]
fn test_noderef_eq() {
    let node = Node::new(Project, "derp");
    let node2 = Node::new(Project, "derp");

    let nref = node.toint();
    let nref2 = node.toint();

    let nref3 = node2.toint();

    assert_eq!(nref, nref2);
    assert!(nref != nref3);
}

#[derive(Debug)]
pub struct Genome(BTreeMap<DateTime<UTC>,Activity>);

impl Genome {
    fn new() -> Genome {
        Genome(BTreeMap::new())
    }

    fn insert(&mut self, activity: Activity) {
        let &mut Genome(ref mut map) = self;
        map.insert(activity.start.clone(), activity);
    }

}

#[derive(Debug)]
pub struct Optimization {
    start: DateTime<UTC>,
    end: DateTime<UTC>,
    tree: Rc<Node>
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

    let opt = Optimization {
        start: UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
        end: UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
        tree: tree
    };

    let mut genome = Genome::new();
    genome.insert(Activity {
        start: UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
        activitytype: WorkOn(opt.tree.children[0].clone())
    });
    genome.insert(Activity {
        start: UTC.ymd(2015, 2, 14).and_hms(0, 0, 0),
        activitytype: Finish(opt.tree.children[1].clone())
    });
    genome.insert(Activity {
        start: UTC.ymd(2015, 2, 15).and_hms(0, 0, 0),
        activitytype: Finish(opt.tree.children[2].clone())
    });

    (opt, genome)
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
