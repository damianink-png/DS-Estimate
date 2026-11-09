; DS Estimate portable OneEXE wrapper (Windows, no installer/registry/admin).
; The single downloaded EXE extracts the actual Tauri executable and the
; packaged OCCT backend into a temporary directory, runs the application,
; then cleans the temporary files when the application exits.
; This is intentionally NOT an installer and must never claim to be a
; single native process. Windows WebView2 Runtime is still required.
!ifndef TAURI_EXE
  !error "Define TAURI_EXE with the compiled Tauri desktop path"
!endif
!ifndef CAD_EXE
  !error "Define CAD_EXE with the compiled PyInstaller CAD engine"
!endif
!ifndef OUTPUT_EXE
  !error "Define OUTPUT_EXE for the portable launcher"
!endif

Unicode true
Name "DS Estimate 0.7.1 Portable"
OutFile "${OUTPUT_EXE}"
RequestExecutionLevel user
SilentInstall silent
AutoCloseWindow true
ShowInstDetails nevershow
SetCompressor /SOLID lzma
SetCompressorDictSize 64
Icon "src-tauri\icons\icon.ico"
VIProductVersion "0.7.1.0"
VIAddVersionKey "ProductName" "DS Estimate"
VIAddVersionKey "FileDescription" "DS Estimate portable OneEXE (self-extracting)"
VIAddVersionKey "FileVersion" "0.7.1.0"

Section "Launch DS Estimate"
  InitPluginsDir
  SetOutPath "$PLUGINSDIR\DS-Estimate"
  File /oname=ds-estimate.exe "${TAURI_EXE}"
  SetOutPath "$PLUGINSDIR\DS-Estimate\cad-backend"
  File /oname=ds-cad-engine.exe "${CAD_EXE}"
  SetOutPath "$PLUGINSDIR\DS-Estimate\licenses"
  File "licenses\steel-section-database-MIT.txt"
  File "COPYING"
  File "THIRD_PARTY_NOTICES.md"
  SetOutPath "$PLUGINSDIR\DS-Estimate"
  ; ExecWait keeps the temporary resource folder alive while the Tauri app
  ; runs. NSIS cleans it after normal shutdown (no application installation).
  ExecWait '"$PLUGINSDIR\DS-Estimate\ds-estimate.exe"' $0
  SetErrorLevel $0
SectionEnd
