#![feature(core)]
#![feature(std_misc)]
#![feature(test)]
#![feature(convert)]

#![feature(collections)]

extern crate test;
extern crate chrono;
extern crate rand;

pub mod tuneables;
pub mod core;
pub mod mutate;
pub mod fitness;
pub mod crossover;
pub mod selection;
pub mod model;

use std::fs::File;
use std::io;
use std::io::{Read, Write};

#[cfg(not(test))]
fn main() {
    //genome::genomerun();
    //fitness::vec_pairs();
    //crossover::tests::test_random_times();

    match run() {
        Ok(()) => (),
        Err(e) => println!("Error: {}", e)
    };
}

fn run() -> io::Result<()> {
    print!("Tree File: ");
    try!(io::stdout().flush());

    let mut filename = String::new();
    try!(io::stdin().read_line(&mut filename));
    filename.pop(); // remove newline

    let mut file = try!(File::open(filename));
    let mut text = String::new();
    try!(file.read_to_string(&mut text));

    core::run_parse(text.as_ref());

    Ok(())
}


