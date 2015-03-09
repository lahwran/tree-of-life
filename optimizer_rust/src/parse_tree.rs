use std::error::FromError;
use std::rc::Rc;
use std::result::Result;
use std::str::Pattern;

use ::genome::Node;

#[derive(Copy, PartialEq, Eq)]
enum Parsing {
    Indent,
    Type,
    Id,
    Sep,
    Text
}

pub struct ParsedLine {
    indent: i32,
    is_metadata: bool,
    id: Option<String>,
    node_type: String,
    text: Option<String>
}

// note: this does not include spaces.
static NODEIDCHARS: &'static str = 
      "abcdefghijklmnopqrstuvwxyz\
       ABCDEFGHIJKLMNOPQRSTUVWXYZ\
       0123456789";

pub fn parse_line(line: &str) -> Result<ParsedLine, &'static str> {
    let mut parsing = Parsing::Indent;
    let mut result = ParsedLine {
        indent: 0i32,
        is_metadata: false,
        id: None,

        node_type: String::new(),
        text: None
    };

    if line.trim() == "" {
        return Ok(result);
    }

    for chr in line.chars() {
        let last_parsing = parsing;
        if parsing == Parsing::Indent {
            if chr == ' ' {
                result.indent += 1;
                continue;
            } else {
                if result.indent % 4 != 0 {
                    return Err("Indentation not multiple of four");
                }
                result.indent /= 4;
                parsing = Parsing::Type;
            }
        }

        if chr == '\n' {
            continue;
        }

        if parsing == Parsing::Type {
            if last_parsing == Parsing::Indent {
                if chr == '@' {
                    result.is_metadata = true;
                    continue;
                } else if chr == '-' {
                    result.node_type = String::from_str("-");
                    parsing = Parsing::Sep;
                    continue;
                }
                // otherwise, do nothing here
            }
            if chr == ':' {
                parsing = Parsing::Sep;
                continue;
            }
            if chr == '#' {
                parsing = Parsing::Id;
                continue;
            }

            result.node_type.push(chr);
            continue;
        }

        if parsing == Parsing::Id {
            if result.id.is_none() {
                result.id = Some(String::with_capacity(5));
            }
            if chr == ':' {
                parsing = Parsing::Sep;
                continue;
            }
            if !(chr).is_contained_in(NODEIDCHARS) {
                return Err("Node id contains invalid characters");
            }
            result.id.as_mut().unwrap().push(chr);
            continue;
        }

        if parsing == Parsing::Sep {
            if chr != ' ' {
                return Err("Space required after colon");
            }
            parsing = Parsing::Text;
            continue;
        }

        // at this point, parsing == Parsing::Text
        if result.text.is_none() {
            result.text = Some(String::new());
        }

        result.text.as_mut().unwrap().push(chr);
    }

    match result.id {
        Some(ref x) if x.chars().count() != 5 => {
            return Err("Node id is not exactly 5 chars long");
        }
        Some(_) if result.is_metadata => {
            return Err("Cannot have IDs on metadata lines");
        }
        _ => ()
    }

    Ok(result)
}

macro_rules! tryline {
    ($index:expr, $expr:expr) => (match $expr {
        Ok(val) => val,
        Err(err) => {
            return Err(format!("Line {}: {}", $index + 1, err));
        }
    })
}

// #1: derp >0
// #2:     derp >1
// #3:         derp >2
// #4:         derp >2
// #5:     derp >1
// #6:     derp >1
// #7:         derp >2
// #8:             derp >3
// #9:                 derp >4
// #a:         derp >2
// #b:             derp >3
// #c:                 derp >4
// #d: derp >0
//
// reverse: 
//      stack: [[#d], [], [#a: [#b: [#c]], #7: [#3: [#9]]]]
//      insert #d >0;
//      insert #c >4;
//      insert #b >3 popping #c;
//      insert #a >2 popping #b;
//      insert #9 >4;
//      insert #8 >3 popping #9;
//      insert #7 >2 popping #8;
//      ...
//
// forward:
//      queue: [#1, #5]
//      committed: [
//          [],
//          [#2: [#3: [], #4: []]],
//          []
//      ]
//      start #1;                                                         queue #1 >0;
//      start #2;                                                         queue #2 >1;
//      start #3;                                                         queue #3 >2;
//      start #4; commit #3 >2;                                           queue #4 >2;
//      start #5; commit #4 >2; commit #2 >1;                             queue #5 >1;
//      start #6; commit #5 >1;                                           queue #6 >1;
//      start #7;                                                         queue #7 >2;
//      start #8;                                                         queue #8 >3;
//      start #9;                                                         queue #9 >4;
//      start #a; commit #9 >4; commit #8 >3; commit #7 >2;               queue #a >2;
//      start #b;                                                         queue #b >3;
//      start #c;                                                         queue #c >4;
//      start #d; commit #c >4; commit #b >3; commit #a >2; commit #1 >0; queue #d >0;

pub fn parse(lines: &str) -> Result<Rc<Node>, String> {
    let mut parent_stack: Vec<ParsedLine> = Vec::new();
    let mut peers_stack: Vec<Vec<Rc<Node>>> = vec![Vec::new()];

    let mut last_indent = -1;

    for (lineidx, line) in lines.lines().enumerate() {
        if line.trim() == "" {
            continue;
        }

        let parsed = tryline!(lineidx, parse_line(line));
        assert!(!parsed.is_metadata);
        assert!(parsed.id.is_some());
        if parsed.indent > last_indent + 1 {
            return tryline!(lineidx, Err("Indentation too great"));
        } else {
            while parsed.indent <= last_indent {
                last_indent -= 1;
                let children = peers_stack.pop().unwrap();
                let parsedline = parent_stack.pop().unwrap();
                let node = Node::new_parent(
                    tryline!(lineidx, parsedline.node_type.parse()),
                    parsedline.id.unwrap(),
                    parsedline.text,
                    children
                );
                peers_stack.last_mut().unwrap().push(node);
            }
        }

        last_indent = parsed.indent;
        parent_stack.push(parsed);
        peers_stack.push(vec![]);
    }

    // Finally, create the root node.
    let children = peers_stack.pop().unwrap();
    
    Ok(Node::new_root(children))
}

#[cfg(test)]
mod tests {
    use super::{parse_line, parse};

    use ::genome::Node;
    use ::genome::NodeType::Task;

    #[test]
    fn test_basic() {
        let line = "\u{fc}category: \u{fc}personal \u{fc}projects";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 0);
        assert!(!result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "\u{fc}category");
        assert_eq!(result.text, Some(
                "\u{fc}personal \u{fc}projects".to_string()));
    }

    #[test]
    fn test_basic_nodeid() {
        let line = "\u{fc}category#asdfg: \u{fc}personal \u{fc}projects";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 0);
        assert!(!result.is_metadata);
        assert_eq!(result.id, Some("asdfg".to_string()));
        assert_eq!(result.node_type, "\u{fc}category");
        assert_eq!(result.text, Some("\u{fc}personal \u{fc}projects".to_string()));
    }

    #[test]
    fn test_indent() {
        let line = "    \u{fc}project: \u{fc}todo \u{fc}tracker";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 1);
        assert!(!result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "\u{fc}project");
        assert_eq!(result.text, Some("\u{fc}todo \u{fc}tracker".to_string()));
    }

    #[test]
    fn test_indent_id() {
        let line = "    \u{fc}project#hjklo: \u{fc}todo \u{fc}tracker";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 1);
        assert!(!result.is_metadata);
        assert_eq!(result.id, Some("hjklo".to_string()));
        assert_eq!(result.node_type, "\u{fc}project");
        assert_eq!(result.text, Some("\u{fc}todo \u{fc}tracker".to_string()));
    }

    #[test]
    fn test_empty_line() {
        let line = "";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 0);
        assert!(!result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "");
        assert!(result.text.is_none());
    }

    #[test]
    fn test_empty_line_indent() {
        let line = "      ";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 0);
        assert!(!result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "");
        assert!(result.text.is_none());
    }

    #[test]
    fn test_notext() {
        let line = "        minor\u{fc} tasks";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 2);
        assert!(!result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "minor\u{fc} tasks");
        assert!(result.text.is_none());
    }

    #[test]
    fn test_notext_id() {
        let line = "        minor\u{fc} tasks#abcde";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 2);
        assert!(!result.is_metadata);
        assert_eq!(result.id, Some("abcde".to_string()));
        assert_eq!(result.node_type, "minor\u{fc} tasks");
        assert!(result.text.is_none());
    }

    #[test]
    fn test_metadata() {
        let line = "    @option\u{fc}: \u{fc}value";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 1);
        assert!(result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "option\u{fc}");
        assert_eq!(result.text, Some("\u{fc}value".to_string()));
    }

    #[test]
    fn test_metadata_notext() {
        let line = "    @option\u{fc}";
        let result = parse_line(line).unwrap();
        assert_eq!(result.indent, 1);
        assert!(result.is_metadata);
        assert!(result.id.is_none());
        assert_eq!(result.node_type, "option\u{fc}");
        assert!(result.text.is_none());
    }

    fn assert_iserror<T: Sized, B: Sized>(x: Result<T,B>) {
        match x {
            Err(_) => (),
            Ok(_) => unreachable!()
        }
    }

    #[test]
    fn test_bad_node_id() {
        assert_iserror(parse_line("    option#longid: derp"));
        assert_iserror(parse_line("    option#shrt: derp"));
        assert_iserror(parse_line("    option#-----: derp"));
    }

    #[test]
    fn test_metadata_node_id() {
        assert_iserror(parse_line("    @option#badid: derp"));
    }

    #[test]
    fn test_bad_indentation() {
        assert_iserror(parse_line("  @option"));
    }

    #[test]
    fn test_no_space() {
        assert_iserror(parse_line("herp:derp"));
    }

    #[test]
    fn test_full_parse() {
        let input = concat!(
            "task#11111: 1\n",
            "    task#22222: 2\n",
            "        task#33333: 3\n",
            "        task#44444: 4\n",
            "    task#55555: 5\n",
            "    task#66666: 6\n",
            "        task#77777: 7\n",
            "            task#88888: 8\n",
            "                task#99999: 9\n",
            "        task#aaaaa: 10\n",
            "            task#bbbbb: 11\n",
            "                task#ccccc\n",
            "task#ddddd: 13\n"
        );

        let parsed = parse(input).unwrap();


        let expected = Node::new_root(vec![
            Node::new_parent(Task, "11111", Some("1"), vec![
                Node::new_parent(Task, "22222", Some("2"), vec![
                    Node::new(Task, "33333", Some("3")),
                    Node::new(Task, "44444", Some("4")),
                ]),
                Node::new(Task, "55555", Some("5")),
                Node::new_parent(Task, "66666", Some("6"), vec![
                    Node::new_parent(Task, "77777", Some("7"), vec![
                        Node::new_parent(Task, "88888", Some("8"), vec![
                            Node::new(Task, "99999", Some("9")),
                        ]),
                    ]),
                    Node::new_parent(Task, "aaaaa", Some("10"), vec![
                        Node::new_parent(Task, "bbbbb", Some("11"), vec![
                            Node::new(Task, "ccccc", None),
                        ]),
                    ]),
                ]),
            ]),
            Node::new(Task, "ddddd", Some("13")),
        ]);

        assert_eq!(parsed, expected);
    }
}
