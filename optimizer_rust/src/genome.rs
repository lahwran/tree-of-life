#[allow(dead_code)]
#[allow(unused_variables)]

use std::rc::Rc;
use std::cmp;
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

#[derive(Debug)]
struct Genome(BTreeMap<DateTime<UTC>,Activity>);

impl Genome {
    fn new() -> Genome {
        Genome(BTreeMap::new())
    }

    fn insert(&mut self, activity: Activity) {
        let &mut Genome(ref mut map) = self;
        map.insert(activity.start.clone(), activity);
    }

}

pub fn derp() {
    let tree = Node::new_root(vec![
        Node::new_parent(Project, "Project Name", vec![
            Node::new(Task, "Task Name"),
        ]),
        Node::new(Project, "Another project name"),
        Node::new(Project, "Herp derp"),
    ]);

    let mut genome = Genome::new();
    genome.insert(Activity {
        start: UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
        activitytype: WorkOn(tree.children[0].clone())
    });
    genome.insert(Activity {
        start: UTC.ymd(2015, 2, 14).and_hms(0, 0, 0),
        activitytype: Finish(tree.children[1].clone())
    });
    genome.insert(Activity {
        start: UTC.ymd(2015, 2, 15).and_hms(0, 0, 0),
        activitytype: Finish(tree.children[2].clone())
    });
    println!("{:?}", genome);
}
