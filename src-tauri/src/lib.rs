mod ipc;

/// Smoke command used by the scaffold; real commands live in ipc.rs.
#[tauri::command]
#[specta::specta]
fn ping_core() -> String {
  logviewer_core::version()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  let bindings = tauri_specta::Builder::<tauri::Wry>::new().commands(
    tauri_specta::collect_commands![ping_core, ipc::load_file, ipc::get_rows],
  );
  #[cfg(debug_assertions)]
  bindings
    .export(specta_typescript::Typescript::default(), "../ui/src/bindings.ts")
    .expect("failed to export typescript bindings");

  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_clipboard_manager::init())
    .manage(ipc::new_file_state())
    .invoke_handler(bindings.invoke_handler())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while building tauri application");
}
