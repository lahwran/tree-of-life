use rand::Rng;
use ::genome::Genome;



pub fn demo_select<'a, R>(origin: &'a Vec<Genome>, count: usize, _: &mut R)
        -> Vec<&'a Genome>
        where R: Rng {
    origin.iter().take(count).collect()
}


/// Stochastic Universal Sampling selection
pub fn sus_select<'a, R>(pop: &'a Vec<Genome>, count: usize, rng: &mut R)
        -> Vec<&'a Genome>
        where R: Rng {

    // Calculate the sum of all fitness values.
    let total_fitness = pop.iter()
        .fold(0f64, |sum, g| sum + g.cached_fitness.unwrap());

    let mut selection = Vec::with_capacity(count);

    // Pick a random offset between 0 and 1 as the starting point for selection.
    let start_offset = rng.next_f64();
    let mut cumulative_expectation = 0f64;
    let mut index = 0;
    for genome in pop {
        // Calculate the number of times this candidate is expected to
        // be selected on average and add it to the cumulative total
        // of expected frequencies.
        cumulative_expectation += (genome.cached_fitness.unwrap()
                                   / total_fitness) * (count as f64);
        
        while cumulative_expectation > start_offset + (index as f64) {
            selection.push(genome);
            index += 1;
        }
    }

    selection
}

/// Ranked Stochastic Universal Sampling selection
pub fn rank_sus_select<'a, R>(pop: &'a Vec<Genome>, count: usize, rng: &mut R)
        -> Vec<&'a Genome>
        where R: Rng {

    // Calculate the sum of all fitness values.
    // sum of 1..len+1, ie sum of (0..len+1).map(|x| len - x)
    let len = pop.len();
    let total_fitness = ((len * (len + 1)) / 2) as f64;

    let mut selection = Vec::with_capacity(count);

    // Pick a random offset between 0 and 1 as the starting point for selection.
    let start_offset = rng.next_f64();
    let mut cumulative_expectation = 0f64;
    let mut index = 0;
    for (genome_index, genome) in pop.iter().enumerate() {
        // Calculate the number of times this candidate is expected to
        // be selected on average and add it to the cumulative total
        // of expected frequencies.
        cumulative_expectation += ((len - genome_index) as f64
                                   / total_fitness) * (count as f64);
        
        while cumulative_expectation > start_offset + (index as f64) {
            selection.push(genome);
            index += 1;
        }
    }

    selection
}


#[cfg(test)]
mod tests {
    use rand::XorShiftRng;

    use ::genome::Genome;
    use super::{rank_sus_select, sus_select};

    #[test]
    fn test_sus() {
        for _ in 0..60 {
            let pop = vec![
                Genome::new_empty().with_fitness(10.0),
                Genome::new_empty().with_fitness(4.5),
                Genome::new_empty().with_fitness(1.0),
                Genome::new_empty().with_fitness(0.5),
            ];

            let mut rng = XorShiftRng::new_unseeded();
            let selection = sus_select(&pop, 4, &mut rng);
            let count = |i: usize| {
                selection.iter().filter(|s| {
                    (&***s) as *const _ == &pop[i] as *const _
                }).count()
            };

            assert_eq!(selection.len(), 4);
            assert!(count(0) >= 2);
            assert!(count(0) <= 3);

            assert!(count(1) >= 1);
            assert!(count(1) <= 2);

            assert!(count(2) <= 1);
            assert!(count(3) <= 1);
        }
    }

    #[test]
    fn test_rank_sus() {
        for _ in 0..60 {
            let pop = vec![
                Genome::new_empty().with_fitness(10.0),
                Genome::new_empty().with_fitness(4.5),
                Genome::new_empty().with_fitness(1.0),
                Genome::new_empty().with_fitness(0.5),
            ];

            let mut rng = XorShiftRng::new_unseeded();
            let selection = rank_sus_select(&pop, 4, &mut rng);
            let count = |i: usize| {
                selection.iter().filter(|s| {
                    (&***s) as *const _ == &pop[i] as *const _
                }).count()
            };

            assert_eq!(selection.len(), 4);
            assert!(count(0) >= 1);
            assert!(count(0) <= 2);

            assert!(count(1) >= 1);
            assert!(count(1) <= 2);

            assert!(count(2) <= 1);
            assert!(count(3) <= 1);
        }
    }
}


