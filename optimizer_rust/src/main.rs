#![feature(hash)]
#![feature(core)]

extern crate chrono;

pub mod genome;
pub mod fitness;

#[cfg(not(test))]
fn main() {
    genome::genomerun();
}


