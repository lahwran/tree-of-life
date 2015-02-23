#![feature(hash)]
#![feature(core)]
#![feature(std_misc)]
#![feature(test)]
#![feature(rand)]
#![feature(collections)]

extern crate test;
extern crate chrono;

pub mod core;
pub mod mutate;
pub mod genome;
pub mod fitness;
pub mod crossover;

#[cfg(not(test))]
fn main() {
    //genome::genomerun();
    //fitness::vec_pairs();
    //crossover::tests::test_random_times();
    core::run();
}


