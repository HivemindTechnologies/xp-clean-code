use std::env;
use std::fs;
use std::time::{Instant, SystemTime};

// ruleid: rust-global-mutation
static mut COUNTER: u64 = 0;

// ok: rust-global-mutation
static LIMIT: u64 = 10;

fn stamp() -> SystemTime {
    // ruleid: rust-clock
    SystemTime::now()
}

fn started() -> Instant {
    // ruleid: rust-clock
    std::time::Instant::now()
}

fn roll() -> u8 {
    // ruleid: rust-random
    rand::random::<u8>()
}

fn home() -> Result<String, env::VarError> {
    // ruleid: rust-environment
    env::var("HOME")
}

fn read(path: &str) -> std::io::Result<String> {
    // ruleid: rust-io
    fs::read_to_string(path)
}

fn log(message: &str) {
    // ruleid: rust-io
    println!("{}", message);
}

fn parse(raw: &str) -> u32 {
    // ruleid: rust-panic
    raw.parse().unwrap()
}

// ok: rust-panic
fn parse_checked(raw: &str) -> Result<u32, std::num::ParseIntError> {
    raw.parse()
}

// ok: rust-clock
fn age(now: SystemTime, born: SystemTime) -> Option<std::time::Duration> {
    now.duration_since(born).ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses() {
        // ok: rust-panic
        let value: u32 = "1".parse().unwrap();
        // ok: rust-clock
        let _now = SystemTime::now();
        // ok: rust-io
        println!("{}", value);
    }
}

// ok: rust-panic
#[test]
fn top_level_test() { "4".parse::<u32>().unwrap(); }
