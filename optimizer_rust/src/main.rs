#![feature(test)]
#![feature(convert)]
#![feature(drain)]
#![feature(pattern)]

macro_rules! trylabel {
    ($label:expr, $expr:expr) => (match $expr {
        Ok(val) => val,
        Err(err) => {
            return Err(format!("{}: {}", $label, err));
        }
    })
}

extern crate test;
extern crate chrono;
extern crate rand;
extern crate argparse;
extern crate rustc_serialize;

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
use std::io::ErrorKind;

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

fn pathjoin(arg1: &str, arg2: &'static str) -> String {
    format!("{}/{}", arg1, arg2)
}

fn run() -> Result<(), String> {
    let mut treedir = String::new();
    let mut pop_filename = String::new();
    {
        let mut parser = ArgumentParser::new();
        parser.set_description("Optimize a schedule");
        parser.refer(&mut treedir)
            .add_argument("treedir", Store,
                          "Directory containing tree and log")
            .required();
        parser.refer(&mut pop_filename)
            .add_argument("population_cache", Store, "File to put pop in")
            .required();
        parser.parse_args_or_exit();
    }

    let mut file = trylabel!("Opening .../life",
                             File::open(pathjoin(&treedir, "life")));
    let mut text = String::new();
    trylabel!("Reading .../life", file.read_to_string(&mut text));


    file = trylabel!("Opening .../log", File::open(pathjoin(&treedir, "log")));
    let mut log = String::new();
    trylabel!("Reading .../log", file.read_to_string(&mut log));

    let popstring = match File::open(pop_filename.clone()) {
        Ok(mut popfile) => {
            let mut genome_text = String::new();
            trylabel!("Reading population",
                      popfile.read_to_string(&mut genome_text));
            Some(genome_text)
        },
        Err(ref error) if error.kind() == ErrorKind::NotFound => None,
        Err(error) => { return Err(format!("Reading population: {}", error)); }
    };

    let resultstring = trylabel!("Core",
                            core::run(text.as_ref(), log.as_ref(), popstring));

    let mut writer = trylabel!("Creating population",
                               File::create(pop_filename));
    let result_bytes = resultstring.into_bytes();
    trylabel!("Writing population",
              writer.write(result_bytes.as_ref()));
    trylabel!("Flushing population", writer.flush());

    Ok(())
}


