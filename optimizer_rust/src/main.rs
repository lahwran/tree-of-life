#![feature(core)]
#![feature(std_misc)]
#![feature(test)]
#![feature(io)]
#![feature(collections)]

extern crate test;
extern crate chrono;
extern crate rand;

use std::old_io as io;

pub mod tuneables;
pub mod core;
pub mod mutate;
pub mod fitness;
pub mod crossover;
pub mod selection;
pub mod model;

#[cfg(not(test))]
fn main() {
    //genome::genomerun();
    //fitness::vec_pairs();
    //crossover::tests::test_random_times();

    print!("Tree File: ");
    let mut filename = io::stdin().read_line().unwrap();
    filename.pop();
    let mut file = io::File::open(&Path::new(filename)).unwrap();
    core::run_parse(&mut file);
}


