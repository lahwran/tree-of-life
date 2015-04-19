#![feature(core)]
#![feature(std_misc)]
#![feature(test)]
#![feature(convert)]

#![feature(collections)]

extern crate test;
extern crate chrono;
extern crate rand;
extern crate argparse;

pub mod tuneables;
pub mod core;
pub mod mutate;
pub mod fitness;
pub mod crossover;
pub mod selection;
pub mod model;

use std::fs::File;
use std::io;
use std::io::Read;

use argparse::{ArgumentParser, Store};

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
    let mut filename = String::new();
    {
        let mut parser = ArgumentParser::new();
        parser.set_description("Optimize a schedule");
        parser.refer(&mut filename)
            .add_argument("treefile", Store, "File containing tree")
            .required();
        parser.parse_args_or_exit();
    }

    let mut file = try!(File::open(filename));
    let mut text = String::new();
    try!(file.read_to_string(&mut text));

    core::run_parse(text.as_ref());

    Ok(())
}


