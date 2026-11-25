//! Line scanning: memory-mapped reading, line offset index, format detection
//! (FUNCTIONAL_SPEC §3: two formats auto-detected by the first non-empty line).

use std::fs;
use std::io;
use std::path::Path;

use memmap2::Mmap;

use crate::format::Format;

pub struct Scanner {
  data: Box<[u8]>,
  offsets: Vec<u64>,
  format: Format,
}

impl Scanner {
  pub fn open(path: &Path) -> io::Result<Scanner> {
    let file = fs::File::open(path)?;
    let data: Box<[u8]> = if file.metadata()?.len() == 0 {
      Box::new([])
    } else {
      Box::from(&*unsafe { Mmap::map(&file)? })
    };
    let offsets = build_offsets(&data);
    let format = format_from_reader(&data);
    Ok(Scanner { data, offsets, format })
  }

  pub fn line_count(&self) -> usize {
    self.offsets.len()
  }

  /// Byte length of the backing data (file size; travels in the load result
  /// so the UI file slot can show "name · size" without re-reading the path).
  pub fn size(&self) -> u64 {
    self.data.len() as u64
  }

  /// Raw bytes of 1-based line `i`, without the trailing `\n` / `\r\n`.
  pub fn raw_line(&self, i: usize) -> &[u8] {
    assert!(i >= 1 && i <= self.line_count(), "line index out of range");
    let start = self.offsets[i - 1] as usize;
    let end = if i < self.line_count() {
      let next = self.offsets[i] as usize;
      next - eol_len(&self.data[next.saturating_sub(2)..next])
    } else {
      // Last line may or may not end with a line terminator.
      let mut end = self.data.len();
      if end > start && self.data[end - 1] == b'\n' {
        end -= 1;
        if end > start && self.data[end - 1] == b'\r' {
          end -= 1;
        }
      } else if end > start && self.data[end - 1] == b'\r' {
        end -= 1;
      }
      end
    };
    &self.data[start..end]
  }

  pub fn format(&self) -> Format {
    self.format
  }
}

/// Length of the line terminator ending at byte `end`: `\r\n` = 2, `\n` = 1.
/// `tail` holds the last two bytes before `end` (fewer at buffer start).
fn eol_len(tail: &[u8]) -> usize {
  match tail {
    [b'\r', b'\n'] => 2,
    [_, b'\n'] | [_, b'\r'] => 1,
    [b'\n'] | [b'\r'] => 1,
    _ => 0,
  }
}

/// Byte offsets of every line start. The last line is counted even without a
/// trailing newline; a trailing newline does not produce a phantom line.
pub fn build_offsets(data: &[u8]) -> Vec<u64> {
  if data.is_empty() {
    return Vec::new();
  }
  let mut offsets: Vec<u64> = Vec::with_capacity(data.len() / 80 + 1);
  offsets.push(0);
  for p in memchr::memchr_iter(b'\n', data) {
    let next = p + 1;
    if next == data.len() {
      break; // trailing newline: no phantom line
    }
    offsets.push(next as u64);
  }
  offsets.shrink_to_fit();
  offsets
}

/// Detect the format from the first non-empty line (§3).
pub fn format_from_reader(data: &[u8]) -> Format {
  let mut rest = data;
  loop {
    let Some(p) = memchr::memchr(b'\n', rest) else {
      return classify(trim_eol(rest));
    };
    let line = trim_eol(&rest[..p]);
    if line.iter().all(|&b| b == b' ' || b == b'\t') {
      rest = &rest[p + 1..];
      continue;
    }
    return classify(line);
  }
}

fn classify(line: &[u8]) -> Format {
  let mut fields = 0;
  let mut first: Option<&[u8]> = None;
  for field in line
    .split(|&b| b == b' ' || b == b'\t')
    .filter(|f| !f.is_empty())
  {
    if first.is_none() {
      first = Some(field);
    }
    fields += 1;
  }
  match first {
    Some(ts) if fields >= 5 && looks_like_time(ts) => Format::Plain,
    _ => Format::Ksiva,
  }
}

/// `HH:MM:SS.mmm`, exactly 12 bytes (§3 format B first field).
fn looks_like_time(ts: &[u8]) -> bool {
  ts.len() == 12
    && ts[2] == b':'
    && ts[5] == b':'
    && ts[8] == b'.'
    && (0..12)
      .filter(|&i| !matches!(i, 2 | 5 | 8))
      .all(|i| ts[i].is_ascii_digit())
}

fn trim_eol(line: &[u8]) -> &[u8] {
  let mut end = line.len();
  while end > 0 && (line[end - 1] == b'\n' || line[end - 1] == b'\r') {
    end -= 1;
  }
  &line[..end]
}
