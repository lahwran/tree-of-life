#![feature(hash)]
#![feature(core)]
#![feature(std_misc)]

extern crate chrono;

pub mod genome;
pub mod fitness;

#[cfg(not(test))]
fn main() {
    genome::genomerun();
}


