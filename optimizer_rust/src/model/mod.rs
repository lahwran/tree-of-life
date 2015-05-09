macro_rules! tryline {
    ($index:expr, $expr:expr) => (match $expr {
        Ok(val) => val,
        Err(err) => {
            return Err(format!("Line {}: {}", $index + 1, err));
        }
    })
}

pub mod genome;
mod parse_tree;
