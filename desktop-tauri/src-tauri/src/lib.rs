use std::path::PathBuf;
use std::process::Command;

#[tauri::command]
async fn analyze_step(app: tauri::AppHandle, path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || analyze_step_blocking(app, path))
        .await.map_err(|e| format!("Błąd zadania CAD: {e}"))?
}

fn analyze_step_blocking(app: tauri::AppHandle, path: String) -> Result<String, String> {
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![analyze_step, step_fingerprint, extract_pdf_text, scan_project])
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
