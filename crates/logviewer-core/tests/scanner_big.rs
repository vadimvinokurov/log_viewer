//! Timing check against the real log file (rule 1: test_logs is not committed
//! and must never be copied into docs or code - this test only measures it).

use std::path::Path;
use std::time::Instant;

use logviewer_core::Scanner;

#[test]
#[ignore = "needs ../../test_logs/log.txt (real logs, not committed)"]
fn big_file_scan_speed() {
  let path = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/../../test_logs/log.txt"));
  if !path.exists() {
    eprintln!("test_logs/log.txt not present, skipping");
    return;
  }
  let t0 = Instant::now();
  let s = Scanner::open(path).unwrap();
  let scan = t0.elapsed();
  println!("format={:?} lines={} scan={scan:?}", s.format(), s.line_count());
  assert!(scan.as_secs_f64() < 2.0, "scan took {scan:?}, budget 2 s");
}
