//! Corpus benchmarks over the real `test_logs/` files (bead log_viewer2-7no.1,
//! epic perf). Run from the workspace root: `cargo bench -p logviewer-core`.
//!
//! The fixtures are resolved against `<repo>/test_logs` (two files: a big
//! format-B style log ~175 MB and a small format-A style log ~5.4 MB); when a
//! fixture is absent the corresponding groups are skipped with a note, so the
//! run never panics on a machine without the corpus. Only counts, paths and
//! timings appear in the output — never file contents (repo rule 1).
//!
//! Measured stages mirror the shell's real call paths:
//! - `scan`: `Scanner::open` (mmap + line-offset index + format detection),
//!   split into `offsets_only` and `format_detect`.
//! - `parse`: `parser::parse` over a 100k-line window (`rows_slice`-driven),
//!   cold (different window each iteration) then warm (same window reused).
//! - `visibility`: full `visible_lines` recompute — the shell's per-mutation
//!   cost. Variants: empty whitelist (the fresh engine default), all
//!   categories enabled (the shell state after load), and with one plain
//!   filter active.
//! - `search`: one pass over the full visible list (the `search_visible_inner`
//!   cost) for plain / regex / simple matchers, replicating the shell's
//!   cache-driven loop (lossy raw text + matcher per row).
//! - `highlight`: `highlights::row_spans` over a 10k-line window per mode.
//! - `get_rows`: a 1000-row window at 50% of the visible list, replicating the
//!   shell's visible-cache slice path (`visible_lines` once, then row lookup
//!   + row-field clones as the DTO conversion does).

use std::hint::black_box;
use std::path::PathBuf;
use std::time::{Duration, Instant};

use criterion::{Criterion, Throughput};

use logviewer_core::highlights::{HighlightEngine, Rule, row_spans};
use logviewer_core::matching::Matcher;
use logviewer_core::parser::parse;
use logviewer_core::scanner::{Scanner, build_offsets, format_from_reader};
use logviewer_core::visibility::Visibility;
use logviewer_core::workspace::FileModel;

/// Patterns are deliberately generic ASCII so that no corpus content is ever
/// copied into this file (repo rule 1): digits occur in every log's timestamps.
const PLAIN_PAT: &str = "0";
const REGEX_PAT: &str = "[0-9]+";
const SIMPLE_PAT: &str = "\"0\"";

/// Window sizes mirroring the shell's chunked UI calls and the bead contract.
const PARSE_WINDOW: usize = 100_000;
const HIGHLIGHT_WINDOW: usize = 10_000;
const ROWS_WINDOW: usize = 1_000;

struct Fixture {
  label: &'static str,
  path: PathBuf,
}

/// Corpus fixtures that exist on this machine (skipped when `test_logs/` is
/// not present, so CI-less environments still compile and run the rest).
fn fixtures() -> Vec<Fixture> {
  let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../test_logs");
  [
    ("small", "TitleId-YBA91-Ksiva-6d865.txt"),
    ("big", "log.txt"),
  ]
  .into_iter()
  .filter_map(|(label, name)| {
    let path = dir.join(name);
    if path.is_file() {
      Some(Fixture { label, path })
    } else {
      eprintln!("[{label}] fixture not found, skipping: {}", path.display());
      None
    }
  })
  .collect()
}

/// All categories enabled — the shell's state right after load: every
/// category path AND its ancestor prefixes (mirrors the shell's
/// `repopulate_categories`; disabling a node hides its children, so the
/// whitelist must hold every prefix).
fn all_categories(model: &FileModel) -> Visibility {
  let mut vis = Visibility::new();
  for path in model.categories() {
    let mut prefix: &str = path;
    loop {
      vis.set_category_enabled(prefix, true);
      match prefix.rfind('/') {
        Some(i) => prefix = &prefix[..i],
        None => break,
      }
    }
  }
  vis
}

fn bench_scan(c: &mut Criterion, label: &str, path: &std::path::Path) {
  let mut g = c.benchmark_group(format!("scan_{label}"));
  g.sample_size(20);
  g.throughput(Throughput::Bytes(
    std::fs::metadata(path).map_or(0, |m| m.len()),
  ));
  g.bench_function("open", |b| b.iter(|| Scanner::open(black_box(path)).unwrap()));
  // The two components of `open`, over already-mapped data.
  let data = std::fs::read(path).expect("fixture bytes");
  g.throughput(Throughput::Bytes(data.len() as u64));
  g.bench_function("offsets_only", |b| b.iter(|| build_offsets(black_box(&data))));
  g.bench_function("format_detect", |b| {
    b.iter(|| format_from_reader(black_box(&data)))
  });
  g.finish();
}

fn bench_parse(c: &mut Criterion, label: &str, model: &FileModel) {
  let format = model.format();
  let n = model.line_count() as usize;
  let w = PARSE_WINDOW.min(n);
  let mut g = c.benchmark_group(format!("parse_{label}"));
  g.throughput(Throughput::Elements(w as u64));
  // Cold: a different window each iteration (caches must not hold its bytes).
  let mut offset = 0usize;
  g.bench_function("window_100k_cold", |b| {
    b.iter_batched(
      || (),
      |()| {
        let slice = model.rows_slice(offset, w);
        offset = if offset + w >= n { 0 } else { offset + w };
        for row in slice {
          black_box(parse(format, row.line_no, &row.raw));
        }
      },
      criterion::BatchSize::PerIteration,
    )
  });
  // Warm: the same window parsed over and over.
  let fixed = n.saturating_sub(w) / 2;
  g.bench_function("window_100k_warm", |b| {
    b.iter(|| {
      for row in model.rows_slice(fixed, w) {
        black_box(parse(format, row.line_no, &row.raw));
      }
    })
  });
  g.finish();
}

fn bench_visibility(c: &mut Criterion, label: &str, model: &FileModel) {
  let n = model.line_count();
  let mut g = c.benchmark_group(format!("visibility_{label}"));
  g.sample_size(10);
  g.measurement_time(Duration::from_secs(6));
  g.throughput(Throughput::Elements(n));

  // Fresh engine default (empty whitelist): the short-circuit floor.
  g.bench_function("recompute_empty_whitelist", |b| {
    let vis = Visibility::new();
    b.iter(|| black_box(vis.visible_lines(model)))
  });
  // The shell state after load: every category enabled, no filters.
  g.bench_function("recompute_all_categories", |b| {
    let vis = all_categories(model);
    b.iter(|| black_box(vis.visible_lines(model)))
  });
  // ..plus one enabled plain filter: the per-filter user cost.
  g.bench_function("recompute_all_categories_one_plain_filter", |b| {
    let mut vis = all_categories(model);
    vis.add_filter(Matcher::plain(PLAIN_PAT));
    b.iter(|| black_box(vis.visible_lines(model)))
  });
  g.finish();
}

/// One full pass over a visibility cached list, exactly as the shell's
/// `search_visible_inner` walks it (lossy raw text + matcher per row).
fn search_pass(model: &FileModel, lines: &[u32], matcher: &Matcher) -> usize {
  let mut hits = 0usize;
  for &line in lines {
    let row = model.row(line as usize - 1).expect("cached line exists");
    let text = String::from_utf8_lossy(&row.raw);
    if matcher.matches(&text, row.line_no) {
      hits += 1;
    }
  }
  black_box(hits)
}

fn bench_search(c: &mut Criterion, label: &str, model: &FileModel) {
  // The search input is the visible list with everything enabled (full set).
  let vis = all_categories(model);
  let lines = vis.visible_lines(model);
  let n = lines.len();
  eprintln!("[{label}] visible set for search: {n} lines");
  let mut g = c.benchmark_group(format!("search_{label}"));
  g.sample_size(10);
  g.measurement_time(Duration::from_secs(6));
  g.throughput(Throughput::Elements(n as u64));
  for (name, matcher) in [
    ("plain", Matcher::plain(PLAIN_PAT)),
    ("regex", Matcher::regex(REGEX_PAT)),
    ("simple", Matcher::simple(SIMPLE_PAT)),
  ] {
    let hits = search_pass(model, &lines, &matcher);
    eprintln!("[{label}] search {name}: {hits} matching lines of {n}");
    g.bench_function(name, |b| b.iter(|| search_pass(model, &lines, &matcher)));
  }
  g.finish();
}

fn bench_highlights(c: &mut Criterion, label: &str, model: &FileModel) {
  let n = model.line_count() as usize;
  let offset = n.saturating_sub(HIGHLIGHT_WINDOW) / 2;
  let window = model.rows_slice(offset, HIGHLIGHT_WINDOW.min(n)).to_vec();
  let mut g = c.benchmark_group(format!("highlight_{label}"));
  g.throughput(Throughput::Elements(window.len() as u64));
  for (name, rule) in [
    ("plain", Rule::Pattern { matcher: Matcher::plain(PLAIN_PAT) }),
    ("regex", Rule::Pattern { matcher: Matcher::regex(REGEX_PAT) }),
    ("simple", Rule::Pattern { matcher: Matcher::simple(SIMPLE_PAT) }),
  ] {
    let mut engine = HighlightEngine::new();
    engine.add(rule);
    g.bench_function(name, |b| {
      b.iter(|| {
        for row in &window {
          black_box(row_spans(&engine, row));
        }
      })
    });
  }
  g.finish();
}

fn bench_get_rows(c: &mut Criterion, label: &str, model: &FileModel) {
  // The shell serves get_rows from its cached visible list; replicate the
  // slice path: visible_lines once (setup), then a window at 50%, then the
  // row lookup + field clones the DTO conversion performs.
  let vis = all_categories(model);
  let lines = vis.visible_lines(model);
  let n = lines.len();
  let start = n / 2;
  let window: Vec<u32> = lines
    .get(start..(start + ROWS_WINDOW).min(n))
    .unwrap_or(&[])
    .to_vec();
  eprintln!("[{label}] visible list {n}; get_rows window {len} at offset {start}", len = window.len());
  let mut g = c.benchmark_group(format!("get_rows_{label}"));
  g.throughput(Throughput::Elements(window.len() as u64));
  g.bench_function("window_1000_mid", |b| {
    b.iter(|| {
      let rows: Vec<(&str, &str, String)> = window
        .iter()
        .map(|&line| {
          let row = model.row(line as usize - 1).expect("cached line exists");
          (row.time_display.as_str(), row.category.as_str(), row.message.clone())
        })
        .collect();
      black_box(rows)
    })
  });
  g.finish();
}

fn main() {
  let mut c = Criterion::default().warm_up_time(Duration::from_secs(1));

  for fixture in fixtures() {
    let meta = std::fs::metadata(&fixture.path).expect("fixture metadata");
    bench_scan(&mut c, fixture.label, &fixture.path);
    let t0 = Instant::now();
    let (model, _) = FileModel::load_path(&fixture.path).expect("fixture loads");
    eprintln!(
      "[{}] loaded: bytes={} lines={} load_ms={}",
      fixture.label,
      meta.len(),
      model.line_count(),
      t0.elapsed().as_millis()
    );

    bench_parse(&mut c, fixture.label, &model);
    bench_visibility(&mut c, fixture.label, &model);
    bench_search(&mut c, fixture.label, &model);
    bench_highlights(&mut c, fixture.label, &model);
    bench_get_rows(&mut c, fixture.label, &model);
  }

  c.final_summary();
}
