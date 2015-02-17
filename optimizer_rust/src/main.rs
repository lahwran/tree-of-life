#![feature(hash)]
#![feature(core)]
#![feature(std_misc)]
#![feature(test)]

extern crate test;
extern crate chrono;

pub mod genome;
pub mod fitness;

#[cfg(not(test))]
fn main() {
    //genome::genomerun();
    fitness::vec_pairs();
}


