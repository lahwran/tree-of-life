#[allow(dead_code)]
#[allow(unused_variables)]

use std::rc::Rc;
use std::cmp;

use chrono::{UTC, DateTime};

use self::NodeType::{Root, Project, Task};
use self::ActivityType::{Nothing, WorkOn, Finish};

pub struct Activity {
    start: DateTime<UTC>,
    activitytype: ActivityType,
}

pub enum ActivityType {
    Nothing,
    WorkOn(Rc<Node>),
    Finish(Rc<Node>),
}

pub struct Node {
    nodetype: NodeType,
    name: String,
    children: Vec<Rc<Node>>,
}

pub enum NodeType {
    Root,
    Project,
    Task,
}

impl cmp::Ord for Activity {
    fn cmp(&self, other: &Self) -> cmp::Ordering {
        self.start.cmp(&other.start)
    }
}

impl cmp::PartialOrd for Activity {
    #[inline]
    fn partial_cmp(&self, other: &Self) -> Option<cmp::Ordering> {
        self.start.partial_cmp(&other.start)
    }
}

impl cmp::PartialEq for Activity {
    #[inline]
    fn eq(&self, other: &Self) -> bool {
        self.start.eq(&other.start) &&
        match (&self.activitytype, &other.activitytype) {
            (&Nothing, &Nothing) => true,

            (&WorkOn(ref a), &WorkOn(ref b))
            | (&Finish(ref a), &Finish(ref b)) => {
                &**a as *const _ == &**b as *const _
            }

            _ => false
        }
    }
}

impl cmp::Eq for Activity {}

impl Node {
    pub fn new_parent(nodetype: NodeType, name: &str, children: Vec<Rc<Node>>)
            -> Rc<Node> {
        Rc::new(Node {
            nodetype: nodetype,
            name: name.to_string(),
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
            children: vec![]
        })
    }
}

#[test]
fn derp() {
    let tree = Node::new_root(vec![
        Node::new_parent(Project, "Project Name", vec![
            Node::new(Task, "Task Name"),
        ]),
        Node::new(Project, "Another project name"),
        Node::new(Project, "Herp derp"),
    ]);

    let mut genome = BTreeSet::new();
}
