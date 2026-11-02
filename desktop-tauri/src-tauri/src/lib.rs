use std::path::PathBuf;
use std::process::Command;

#[tauri::command]
fn analyze_step(app: tauri::AppHandle, path: String) -> Result<String, String> {
    use tauri::Manager;
    let input = PathBuf::from(&path);
    if !input.is_file() { return Err("Nie znaleziono pliku STEP".into()); }
    let backend = app.path().resource_dir()
        .map_err(|e| e.to_string())?
        .join("cad-backend").join("ds-cad-engine.exe");
    if !backend.is_file() {
        return Err(format!("Silnik CAD nie jest zainstalowany: {}", backend.display()));
    }
    let result = Command::new(&backend).arg(&input).output()
        .map_err(|e| format!("Nie można uruchomić silnika CAD: {e}"))?;
    if !result.status.success() {
        return Err(format!("Błąd analizy STEP: {}", String::from_utf8_lossy(&result.stderr)));
    }
    String::from_utf8(result.stdout).map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![analyze_step])
        .run(tauri::generate_context!())
        .expect("Błąd uruchamiania DS Estimate");
}
