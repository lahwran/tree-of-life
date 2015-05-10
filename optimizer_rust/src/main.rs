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
use std::io::{Read,Write};
use std::io::ErrorKind::NotFound;

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
    let mut pop_filename = String::new();
    {
        let mut parser = ArgumentParser::new();
        parser.set_description("Optimize a schedule");
        parser.refer(&mut filename)
            .add_argument("treefile", Store, "File containing tree")
            .required();
        parser.refer(&mut pop_filename)
            .add_argument("population_cache", Store, "File to put pop in")
            .required();
        parser.parse_args_or_exit();
    }

    let mut file = try!(File::open(filename));
    let mut text = String::new();
    try!(file.read_to_string(&mut text));

    let popstring = match File::open(pop_filename.clone()) {
        Ok(popfile) => {
            let mut genome_text = String::new();
            try!(file.read_to_string(&mut genome_text));
            Some(genome_text)
        },
        Err(ref error) if error.kind() == NotFound => None,
        Err(error) => { return Err(error); }
    };

    let resultstring = core::run(text.as_ref(), popstring);

    let mut writer = try!(File::create(pop_filename));
    let result_bytes = resultstring.into_bytes();
    try!(writer.write(result_bytes.as_ref()));
    try!(writer.flush());

    Ok(())
}


