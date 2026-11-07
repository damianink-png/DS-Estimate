use std::path::PathBuf;
use std::process::Command;

#[tauri::command]
async fn analyze_step(app: tauri::AppHandle, path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || analyze_step_blocking(app, path, None))
        .await.map_err(|e| format!("Błąd zadania CAD: {e}"))?
}

#[tauri::command]
async fn analyze_joints(app: tauri::AppHandle, path: String, max_seconds: Option<f64>) -> Result<String, String> {
    let budget = max_seconds.unwrap_or(180.0);
    if !budget.is_finite() || !(1.0..=600.0).contains(&budget) { return Err("Limit analizy musi wynosić 1–600 sekund".into()); }
    tauri::async_runtime::spawn_blocking(move || analyze_step_blocking(app, path, Some(format!("--joints --joint-seconds {budget}"))))
        .await.map_err(|e| format!("Błąd analizy styków: {e}"))?
}

#[tauri::command]
async fn preview_part(app: tauri::AppHandle, path: String, index: u32) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || analyze_step_blocking(app, path, Some(format!("--preview {index}"))))
        .await.map_err(|e| format!("Podgląd CAD: {e}"))?
}

fn analyze_step_blocking(app: tauri::AppHandle, path: String, mode: Option<String>) -> Result<String, String> {
    use tauri::Manager;
    let input = PathBuf::from(&path);
    if !input.is_file() { return Err("Nie znaleziono pliku STEP".into()); }
    let backend = app.path().resource_dir()
        .map_err(|e| e.to_string())?
        .join("cad-backend").join("ds-cad-engine.exe");
    if !backend.is_file() {
        return Err(format!("Silnik CAD nie jest zainstalowany: {}", backend.display()));
    }
    let mut command = Command::new(&backend);
    command.arg(&input);
    if let Some(mode) = mode { for arg in mode.split_whitespace() { command.arg(arg); } }
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW: CAD never opens a second console/UI.
    }
    let result = command.output()
        .map_err(|e| format!("Nie można uruchomić silnika CAD: {e}"))?;
    if !result.status.success() {
        return Err(format!("Błąd analizy STEP: {}", String::from_utf8_lossy(&result.stderr)));
    }
    String::from_utf8(result.stdout).map_err(|e| e.to_string())
}

/// A cache key bound to actual file metadata; changing the STEP invalidates
/// only its geometry snapshot, not operator-confirmed settings.
#[tauri::command]
fn step_fingerprint(path: String) -> Result<String, String> {
    let meta = std::fs::metadata(&path).map_err(|e| format!("Plik STEP: {e}"))?;
    if !meta.is_file() { return Err("Wymagany plik STEP".into()); }
    let modified = meta.modified().map_err(|e| e.to_string())?
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| e.to_string())?;
    Ok(format!("{}:{}:{}", meta.len(), modified.as_secs(), modified.subsec_nanos()))
}

#[tauri::command]
fn extract_pdf_text(path: String) -> Result<String, String> {
    let input = PathBuf::from(&path);
    if !input.is_file() { return Err("Nie znaleziono pliku PDF".into()); }
    if input.extension().and_then(|x| x.to_str()).map(|x| !x.eq_ignore_ascii_case("pdf")).unwrap_or(true) {
        return Err("Wymagany plik PDF".into());
    }
    pdf_extract::extract_text(&input).map_err(|e| format!("Błąd odczytu tekstu PDF: {e}"))
}


const MAX_SCAN_FILES: usize = 2000;
const MAX_SCAN_DEPTH: usize = 12;

/// Only enumerate files; never upload files or follow symlinks outside the dropped folder.
/// A STEP is analyzed by the existing offline CAD engine after an explicit user action.
fn accepted_document(path: &std::path::Path) -> bool {
    let Some(ext) = path.extension().and_then(|x| x.to_str()) else { return false; };
    matches!(ext.to_ascii_lowercase().as_str(),
        "step" | "stp" | "pdf" | "dxf" | "dwg" | "png" | "jpg" | "jpeg" | "csv" | "xlsx" | "xls")
}

fn collect_documents(path: &std::path::Path, depth: usize, out: &mut Vec<String>) -> Result<(), String> {
    if depth > MAX_SCAN_DEPTH { return Err("Przekroczono bezpieczny limit zagnieżdżenia folderów.".into()); }
    let meta = std::fs::symlink_metadata(path)
        .map_err(|e| format!("Nie można odczytać ścieżki {}: {e}", path.display()))?;
    if meta.file_type().is_symlink() { return Ok(()); }
    if meta.is_file() {
        if accepted_document(path) {
            if out.len() >= MAX_SCAN_FILES {
                return Err(format!("Folder zawiera więcej niż {MAX_SCAN_FILES} dokumentów. Wybierz mniejszy zestaw."));
            }
            out.push(path.to_string_lossy().into_owned());
        }
    } else if meta.is_dir() {
        let mut children = std::fs::read_dir(path)
            .map_err(|e| format!("Nie można otworzyć folderu {}: {e}", path.display()))?
            .collect::<Result<Vec<_>, _>>().map_err(|e| e.to_string())?;
        children.sort_by_key(|x| x.file_name().to_string_lossy().to_ascii_lowercase());
        for child in children {
            let name = child.file_name();
            if name.to_string_lossy().starts_with('.') { continue; }
            collect_documents(&child.path(), depth+1, out)?;
        }
    }
    Ok(())
}

#[tauri::command]
fn scan_project(path: String) -> Result<Vec<String>, String> {
    let target = PathBuf::from(path.trim());
    if !target.exists() { return Err("Nie znaleziono wskazanego folderu lub pliku".into()); }
    let mut files = Vec::new();
    collect_documents(&target, 0, &mut files)?;
    if files.is_empty() { return Err("Nie znaleziono obsługiwanych plików projektu".into()); }
    Ok(files)
}

/// Save only text reports after the native save dialog has selected a path.
#[tauri::command]
fn write_report(path: String, content: String) -> Result<(), String> {
    let target = PathBuf::from(&path);
    let ext = target.extension().and_then(|s| s.to_str()).unwrap_or("").to_ascii_lowercase();
    if !matches!(ext.as_str(), "json" | "csv") { return Err("Wybierz format JSON lub CSV".into()); }
    if content.len() > 32 * 1024 * 1024 { return Err("Raport jest za duży".into()); }
    std::fs::write(target, content).map_err(|e| format!("Nie można zapisać raportu: {e}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![analyze_step, analyze_joints, preview_part, step_fingerprint, extract_pdf_text, scan_project, write_report])
                .setup(|app| {
            use tauri::Manager;
            if let Some(window) = app.get_webview_window("main") {
                if let Some(monitor) = window.current_monitor()? {
                    let scale = monitor.scale_factor();
                    let area = monitor.work_area();
                    let width = (area.size.width as f64 / scale * 0.92).min(1440.0);
                    let height = (area.size.height as f64 / scale * 0.92).min(960.0);
                    window.set_min_size(Some(tauri::LogicalSize::new(480.0_f64.min(width), 360.0_f64.min(height))))?;
                    window.set_size(tauri::LogicalSize::new(width, height))?;
                    window.center()?;
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Błąd uruchamiania DS Estimate");
}

#[cfg(test)]
mod scan_tests {
    use super::*;

    #[test]
    fn accepts_exact_limit_and_rejects_only_next_supported_document() {
        let dir = std::env::temp_dir().join(format!("ds-estimate-scan-{}-{:?}", std::process::id(), std::thread::current().id()));
        std::fs::create_dir_all(&dir).unwrap();
        let supported = dir.join("part.step");
        let ignored = dir.join("readme.txt");
        std::fs::write(&supported, b"").unwrap();
        std::fs::write(&ignored, b"").unwrap();
        let mut items = vec!["existing".to_owned(); MAX_SCAN_FILES - 1];
        assert!(collect_documents(&supported, 0, &mut items).is_ok());
        assert_eq!(items.len(), MAX_SCAN_FILES);
        assert!(collect_documents(&ignored, 0, &mut items).is_ok());
        assert!(collect_documents(&supported, 0, &mut items).is_err());
        assert_eq!(items.len(), MAX_SCAN_FILES);
        std::fs::remove_dir_all(dir).unwrap();
    }
}
