#![allow(non_upper_case_globals)]
#![allow(deprecated)]

use rand::{Rng, XorShiftRng};
use std::mem;

use chrono::{UTC, TimeZone};

use ::genome::{Genome, Optimization};
use ::genome::tests::testtree;
use ::fitness::FitnessFunction;
use ::mutate::mutate;

const pop_size: usize = 300;
const elite_count: usize = 50;
const generation_count: usize = 90;

// is f64 okay? do we want f32?
pub type Fitness = f64;

#[inline]
fn fill_fitnesses(pop: &mut Vec<Genome>, opt: &Optimization) {
    for genome in pop.iter_mut() {
        match &genome.cached_fitness {
            &None => {
                genome.cached_fitness = Some(opt.fitness(genome))
            },
            &Some(_) => ()
        }
    }
    pop.sort_by(|g1, g2| {
        let f1 = g1.cached_fitness.unwrap();
        let f2 = g2.cached_fitness.unwrap();

        f1.partial_cmp(&f2).unwrap()
    });
}

fn demo_select<'a, R>(origin: &'a Vec<Genome>, count: usize, rng: &mut R)
        -> Vec<&'a Genome>
        where R: Rng {
    origin.iter().take(count).collect()
}

#[inline]
fn mutate_all(pop: &mut Vec<Genome>) {
    for genome in pop.iter_mut() {
        mutate(genome);
    }
}

fn crossover(a: &Genome, b: &Genome) -> (Genome, Genome) {
    (a.clone(), b.clone())
}

fn crossover_all<R>(rng: &mut R, mut selections: Vec<&Genome>,
                    pop: &mut Vec<Genome>)
        where R: Rng {
    rng.shuffle(selections.as_mut_slice());
    let mut iter = selections.iter();
    loop {
        let a = match iter.next() {
            None => { break; },
            Some(x) => x
        };
        let b = match iter.next() {
            None => { break; },
            Some(x) => x
        };

        let (u, v) = crossover(a, b);
        pop.push(u);
        pop.push(v);
    }
}

fn evolve(mut prev_pop: Vec<Genome>, opt: &Optimization) {
    let mut rng = XorShiftRng::new_unseeded();

    let mut pop = Vec::with_capacity(pop_size);

    assert!(prev_pop.len() == pop_size);

    assert!(elite_count < pop_size);

    for generation in 0..generation_count {
        // fill in fitness into prev
        fill_fitnesses(&mut prev_pop, opt);

        {
            let selections = demo_select(&prev_pop,
                        pop_size - elite_count, &mut rng);

            // clone from prev_pop into pop
            crossover_all(&mut rng, selections, &mut pop);
        }
        mutate_all(&mut pop);

        for elite in prev_pop.drain().take(elite_count) {
            pop.push(elite);
        }
        mem::swap(&mut prev_pop, &mut pop);
    }
}

fn evolve_schedule(opt: &Optimization) {
    // todo: translate - generate initial pop
    let generated_pop = (0..pop_size)
            .map(|_| Genome::new(opt))
            .collect::<Vec<Genome>>();

    evolve(generated_pop, opt);
}

pub fn run() {
    let tree = testtree();
    let opt = Optimization::new(
        UTC.ymd(2015, 2, 12).and_hms(0, 0, 0),
        UTC.ymd(2015, 3, 12).and_hms(0, 0, 0),
        tree
    );
    evolve_schedule(&opt);
}
