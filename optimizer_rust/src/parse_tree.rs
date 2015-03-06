use std::result::Result;
use std::str::Pattern;

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

#[cfg(test)]
mod tests {
    use super::parse_line;

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
}
