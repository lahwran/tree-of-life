#![feature(std_misc)]
#![feature(test)]

#![feature(collections)]

extern crate test;
extern crate chrono;
extern crate rand;

pub mod core;
pub mod mutate;
pub mod genome;
pub mod fitness;
pub mod crossover;
pub mod selection;

#[cfg(not(test))]
fn main() {
    //genome::genomerun();
    //fitness::vec_pairs();
    //crossover::tests::test_random_times();
    core::run();
}


