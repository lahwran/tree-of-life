use std::rc::Rc;

use rustc_serialize::json;

use chrono::{UTC, DateTime, TimeZone};

use ::fitness::{TreeState, prepare_state};
use ::model::genome::{Node,Optimization};
use ::model::parse_tree;

use self::LogKind::{Activation, Unknown};
use self::LogNode::{Exists, Gone};

#[derive(Eq, PartialEq)]
pub enum LogKind {
    Activation,
    Unknown
}

pub enum LogNode {
    // Currently equivalent to Option. It's fine if that never changes, but
    // this is intended to elegantly allow adding a "what disappeared"
    // parameter to Gone, should that be desired (it is greatly expected).
    Exists(Rc<Node>),
    Gone
}

pub struct LogEntry {
    pub time: DateTime<UTC>,
    pub kind: LogKind,
    pub nodes: Vec<LogNode>

}

impl LogEntry {
    fn from_line(opt: &Optimization, line: &str)
                -> Result<LogEntry,String> {
        // 2014-12-17 14:55:21 Wednesday - activation - ["life#00000", "category#Uew2Y: spacemonkey", "task#5Frk3: add setting to restrict uploaded files"]
        // YYYY-MM-DD HH:MM:SS WEEKDAY - LOGTYPE - JSONNODEPATH
        // DATE - LOGTYPE - REST
        let segment_split: Vec<&str> = line.splitn(3, " - ").collect();
        if segment_split.len() != 3 {
            return Err("Wrong number of segments".to_string());
        }
        let date_split: Vec<&str> = segment_split[0].rsplitn(2, " ").collect();
        let logkind_data = segment_split[1];
        let nodes_data = segment_split[2];

        let date = match UTC.datetime_from_str(date_split[1],
                                               "%Y-%m-%d %H:%M:%S") {
            Ok(x) => x,
            Err(error) => return Err(format!("Date parse: {} - {:?}", error, date_split))
        };

        let logkind = match logkind_data {
            "activation" => Activation,
            _ => Unknown
        };

        let nodestrings: Vec<String> = json::decode(nodes_data).unwrap();
        let mut nodes = Vec::new();

        for nodestring in nodestrings {
            let parsed = trylabel!("Parsing node",
                                   parse_tree::parse_line(&nodestring));
            if parsed.indent != 0 {
                return Err("A node had nonzero indent in the json".to_string());
            }
            if parsed.is_metadata {
                return Err("Contained metadata in nodes".to_string());
            }
            let id = match parsed.id {
                Some(ref x) => x,
                None => {
                    return Err("A node is missing an id".to_string());
                }
            };

            nodes.push(match opt.id_map.get(id) {
                Some(node) => Exists(node.clone()),
                None => Gone
            });
        }

        Ok(LogEntry {
            time: date,
            kind: logkind,
            nodes: nodes
        })
    }
}

pub fn parse_log(opt: &Optimization, log: &str)
        -> Result<Vec<LogEntry>,String> {
    let mut result = Vec::new();
    for (lineidx, line) in log.lines().enumerate() {
        result.push(tryline!(lineidx, LogEntry::from_line(opt, line)));
    }

    Ok(result)
}

pub fn process_log(opt: &Optimization, log: &str) -> Result<TreeState, String> {
    let parsed = try!(parse_log(opt, log));

    Ok(prepare_state(parsed, opt))
}
