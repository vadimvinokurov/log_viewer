//! Live-verification driver (debug builds only; docs/PIPELINE.md §5, beads
//! n4y.3). A localhost HTTP server evaluates headless-console actions inside
//! the real webview and reports the result back over the Tauri IPC:
//!
//! ```text
//! driver -> POST /load {"path": ...} -> eval(__headless.load)
//! page   -> driver_report(id, value) -> HTTP response {"result": ...}
//! ```
//! This is the app's own text RPC running in the real window: the load goes
//! through the real IPC (load_file), the real core and the real table, with
//! zero manual steps. The native Open dialog itself is not drivable; the
//! dialog step stays an owner-level live check (CLAUDE.md rule 5 last resort).

use std::collections::HashMap;

use tauri::Manager;
use std::io::{Read, Write};
use std::fmt::Write as _;
use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Condvar, Mutex};
use std::time::Duration;

/// One pending report slot: the page fills it, the server takes it.
#[derive(Default)]
pub struct ReportShared {
  pub reports: Mutex<HashMap<String, String>>,
  signal: Condvar,
}

pub type SharedState = Arc<ReportShared>;

/// Tauri command the page invokes with the evaluation result.
#[tauri::command]
#[specta::specta]
pub fn driver_report(
  id: String,
  value: String,
  state: tauri::State<'_, SharedState>,
) {
  state
    .reports
    .lock()
    .expect("driver reports poisoned")
    .insert(id, value);
  state.signal.notify_all();
}

/// Start the debug driver server; returns when the listener is bound.
pub fn start(app: tauri::AppHandle, port_file: std::path::PathBuf) -> std::io::Result<()> {
  let listener = TcpListener::bind(("127.0.0.1", 0))?;
  let port = listener.local_addr()?.port();
  let _ = std::fs::write(&port_file, format!("{port}\n"));
  log::info!("driver server on 127.0.0.1:{port} (port file {port_file:?})");
  let shared: SharedState = Arc::new(ReportShared::default());
  app.manage(shared.clone());
  std::thread::spawn(move || {
    for stream in listener.incoming() {
      match stream {
        Ok(stream) => handle(stream, shared.clone(), app.clone()),
        Err(e) => log::warn!("driver accept failed: {e}"),
      }
    }
  });
  Ok(())
}

fn handle(mut stream: TcpStream, shared: SharedState, app: tauri::AppHandle) {
  let request = read_request(&mut stream);
  let Some(request) = request else {
    let _ = write_response(&mut stream, 400, "{\"error\":\"bad request\"}");
    return;
  };
  let result: Option<String> = (|| {
    let path = json_field(&request.body, "path")?;
    let id = format!("r{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.subsec_nanos()).unwrap_or(0));
    // Escape the path as a JS string literal, then drive the real console.
    let js = format!(
      "(async () => {{ try {{ const r = await window.__headless.load({path_js}); \
       await window.__TAURI_INTERNALS__.invoke('driver_report', {{ id: '{id}', value: JSON.stringify(r) }}); }} \
       catch (e) {{ await window.__TAURI_INTERNALS__.invoke('driver_report', {{ id: '{id}', value: JSON.stringify({{ driverError: String(e) }}) }}); }} }})()",
      path_js = json_string(&path)
    );
    let Some(webview) = app.get_webview_window("main") else {
      return Some("{\"error\":\"no webview\"}".to_owned());
    };
    let _ = webview.eval(&js);
    let deadline = std::time::Instant::now() + Duration::from_secs(60);
    let mut reports = shared.reports.lock().expect("driver reports poisoned");
    loop {
      if let Some(value) = reports.remove(&id) {
        return Some(format!("{{\"result\":{value}}}"));
      }
      let Some(timeout) = deadline.checked_duration_since(std::time::Instant::now()) else {
        return Some("{\"error\":\"driver timeout\"}".to_owned());
      };
      let (guard, _elapsed) = shared
        .signal
        .wait_timeout(reports, timeout)
        .expect("driver signal poisoned");
      reports = guard;
    }
  })();
  let body = result.unwrap_or_else(|| "{\"error\":\"bad request\"}".to_owned());
  let _ = write_response(&mut stream, if body.contains("\"error\"") { 400 } else { 200 }, &body);
}

/// Minimal HTTP: read headers then the declared content-length body.
fn read_request(stream: &mut TcpStream) -> Option<Request> {
  let mut buf = Vec::new();
  let mut chunk = [0_u8; 4096];
  let headers_end = loop {
    if let Some(p) = find_headers_end(&buf) {
      break p;
    }
    let n = stream.read(&mut chunk).ok()?;
    if n == 0 {
      return None;
    }
    buf.extend_from_slice(&chunk[..n]);
  };
  let header_text = String::from_utf8_lossy(&buf[..headers_end.saturating_sub(4)]).to_lowercase();
  let content_length: usize = find_header(&header_text, "content-length")
    .and_then(|v| v.parse().ok())
    .unwrap_or(0);
  while buf.len() < headers_end + content_length {
    let n = stream.read(&mut chunk).ok()?;
    if n == 0 {
      break;
    }
    buf.extend_from_slice(&chunk[..n]);
  }
  if buf.len() < headers_end {
    return None;
  }
  Some(Request {
    body: String::from_utf8_lossy(&buf[headers_end..]).into_owned(),
  })
}

struct Request {
  body: String,
}

fn find_headers_end(buf: &[u8]) -> Option<usize> {
  buf.windows(4).position(|w| w == b"\r\n\r\n").map(|p| p + 4)
}

fn find_header<'a>(header_text: &'a str, name: &str) -> Option<&'a str> {
  let needle = format!("{name}:");
  header_text
    .match_indices(&needle)
    .next()
    .and_then(|(pos, _)| {
      let line_end = header_text[pos..].find('\n').map(|p| p + pos)?;
      header_text[pos + needle.len()..line_end]
        .split_whitespace()
        .next()
    })
}

/// Serialize a Rust string as a JS/JSON string literal.
fn json_string(s: &str) -> String {
  let mut out = String::with_capacity(s.len() + 2);
  out.push('"');
  for c in s.chars() {
    match c {
      '"' => out.push_str("\\\""),
      '\\' => out.push_str("\\\\"),
      c => out.push(c),
    }
  }
  out.push('"');
  out
}

/// Consume a JSON string literal starting at `s` (expects leading quote).
fn json_string_value(s: &str) -> Option<String> {
  let bytes: Vec<char> = s.chars().collect();
  let mut i = 0;
  while i < bytes.len() && bytes[i].is_whitespace() {
    i += 1;
  }
  if bytes.get(i) != Some(&'"') {
    return None;
  }
  i += 1;
  let mut out = String::new();
  while i < bytes.len() {
    match bytes[i] {
      '"' => return Some(out),
      '\\' => {
        let next = *bytes.get(i + 1)?;
        match next {
          'n' => out.push('\n'),
          't' => out.push('\t'),
          'r' => out.push('\r'),
          _ => out.push(next),
        }
        i += 2;
      }
      c => {
        out.push(c);
        i += 1;
      }
    }
  }
  None
}




fn write_response(stream: &mut TcpStream, code: u16, body: &str) -> std::io::Result<()> {
  let mut head = String::new();
  let _ = write!(
    &mut head,
    "HTTP/1.1 {code} {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n",
    if code == 200 { "OK" } else { "Bad Request" },
    body.len()
  );
  stream.write_all(head.as_bytes())?;
  stream.write_all(body.as_bytes())
}

/// Extract a JSON string field from a flat object ("path": "...").
fn json_field(body: &str, field: &str) -> Option<String> {
  let needle = concat_escaped(field);
  let pos = body.find(&needle)? + needle.len();
  let pos = body[pos..].find(':')? + pos + 1;
  let value = json_string_value(&body[pos..])?;
  Some(value)
}

// No runtime string-building needed: field names are literals like "path".
fn concat_escaped(field: &str) -> String {
  format!("\"{field}\"")
}

#[cfg(test)]
mod tests {
  use super::*;

  #[test]
  fn extracts_path_field() {
    assert_eq!(
      json_field(r#"{"path": "/tmp/log.txt"}"#, "path"),
      Some("/tmp/log.txt".to_owned())
    );
    assert_eq!(
      json_field(r#"{"path":"/a b/c d.log"}"#, "path"),
      Some("/a b/c d.log".to_owned())
    );
    assert_eq!(json_field("{}", "path"), None);
  }

  #[test]
  fn escapes_js_string() {
    assert_eq!(json_string("/tmp/ok"), "\"/tmp/ok\"");
    assert_eq!(json_string("with \" quote"), "\"with \\\" quote\"");
  }

  #[test]
  fn reads_partial_http_bodies() {
    // The parser only runs on live sockets; smoke-check the header slicing.
    let header_text = "content-length: 5\r\nhost: 127.0.0.1\r\n";
    assert_eq!(find_header(header_text, "content-length"), Some("5"));
  }
}

