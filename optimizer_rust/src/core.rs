#![allow(non_upper_case_globals)]

use rand::{Rng, XorShiftRng};
use std::mem;

use chrono::{UTC, Duration};

use ::model::genome::{Genome, Optimization, node_from_str};
use ::model::log::process_log;
use ::fitness::{fitness,TreeState};
use ::mutate::{mutate, add_gene};
use ::crossover::crossover_rand;
use ::selection::rank_sus_select;

const pop_size: usize = 300;
const elite_count: usize = 50;
const generation_count: usize = 90;

// is f64 okay? do we want f32?
pub type Fitness = f64;

#[inline]
fn fill_fitnesses(fitness_state: &TreeState, pop: &mut Vec<Genome>,
                  opt: &Optimization) {
    for genome in pop.iter_mut() {
        match &genome.cached_fitness {
            &None => {
                genome.cached_fitness = Some(
                    fitness(fitness_state, opt, genome))
            },
            &Some(_) => ()
        }
    }
    pop.sort_by(|g1, g2| {
        let f1 = g1.cached_fitness.unwrap();
        let f2 = g2.cached_fitness.unwrap();

        f2.partial_cmp(&f1).unwrap()
    });
}

#[inline]
fn mutate_all<R: Rng>(opt: &Optimization, pop: &mut Vec<Genome>, rng: &mut R) {
    for genome in pop.iter_mut() {
        // TODO: mutation probability? is that our job here?
        if rng.next_f64() > 0.01 {
            mutate(opt, genome, rng);
        }
    }
}

fn crossover_all<R: Rng>(opt: &Optimization, rng: &mut R,
                         selections: Vec<&Genome>, pop: &mut Vec<Genome>) {
    let mut iter = selections.iter();
    loop {
        let a = match iter.next() {
            None => { break; },
            Some(x) => x
        };
        let b = match iter.next() {
            None => {
                pop.push((*a).clone());
                break;
            },
            Some(x) => x
        };
        // TODO: crossover probability?

        let (u, v) = crossover_rand(opt, a, b, rng);
        pop.push(u);
        pop.push(v);
    }
}

fn evolve<R: Rng>(fitness_state: TreeState, mut prev_pop: Vec<Genome>,
                  opt: &Optimization, rng: &mut R)
        -> Vec<Genome> {

    let mut pop = Vec::with_capacity(pop_size);

    if prev_pop.len() != pop_size {
        panic!("Wrong population size: {}", prev_pop.len());
    }

    assert!(elite_count < pop_size);

    for _ in 0..generation_count {
        // fill in fitness into prev
        fill_fitnesses(&fitness_state, &mut prev_pop, opt);
        //println!("iter: {:?}, best: {:?}, worst: {:?}",
        //         iter, prev_pop.first().unwrap().cached_fitness,
        //         prev_pop.last().unwrap().cached_fitness);

        {
            let mut selections = rank_sus_select(&prev_pop,
                        pop_size - elite_count, rng);

            rng.shuffle(selections.as_mut_slice());
            // clone from prev_pop into pop
            crossover_all(opt, rng, selections, &mut pop);
        }
        mutate_all(opt, &mut pop, rng);

        for elite in prev_pop.drain(..).take(elite_count) {
            pop.push(elite);
        }
        mem::swap(&mut prev_pop, &mut pop);
    }
    fill_fitnesses(&fitness_state, &mut prev_pop, opt);

    prev_pop
}

static GENOME_SEPARATOR: &'static str = "genome_separator\n";

fn pop_to_str(pop: &Vec<Genome>) -> String {
    let mut result = String::new();
    for (index, genome) in pop.iter().enumerate() {
        if index != 0 {
            result.push_str(GENOME_SEPARATOR);
        }
        let genome_string = genome.to_string();
        result.push_str(genome_string.as_ref());
    }
    
    result
}

fn generate_pop<R: Rng>(opt: &Optimization, rng: &mut R) -> Vec<Genome> {
    (0..pop_size)
        .map(|_| {
            let mut genome = Genome::new(opt);
            for _ in 0..25 {
                add_gene(opt, &mut genome, rng);
            }
            genome.sort();
            genome
        })
        .collect::<Vec<Genome>>()
}

pub fn run(tree: &str, log: &str, pop_str: Option<String>)
        -> Result<String,String> {
    let tree = node_from_str(tree).unwrap();

    let now = UTC::now();
    let opt = Optimization::new(
        // TODO IMPORTANT FIXME XXX: how does the optimizer deal with dates
        // outside its range?
        // ANSWER: badly
        now.clone(),
        now.clone() + Duration::weeks(2),
        tree
    );
    let mut rng = XorShiftRng::new_unseeded();
    let fitness_state = trylabel!("Parsing log", process_log(&opt, log));
    let empty_genome = Genome::new(&opt);
    println!("Fitness of empty genome: {}", fitness(&fitness_state, &opt,
                                                    &empty_genome));
    let initial_pop = match pop_str {
        None => {
            generate_pop(&opt, &mut rng)
        },
        Some(s) => {
            let mut pop = Vec::new();
            for genome_string in s.trim().split(GENOME_SEPARATOR) {
                if genome_string.trim().len() == 0 {
                    continue;
                }
                let b = Genome::from_string(&opt, genome_string.trim());
                let a = trylabel!("Parsing genome", b);
                pop.push(a);
            }
            pop
        }
    };

    let result_pop = evolve(fitness_state, initial_pop, &opt, &mut rng);

    Ok(pop_to_str(&result_pop))
}
