# DS Estimate — aplikacja desktopowa

Aktualny program znajduje się w **`desktop-tauri/`**. Wersja 0.4 ma jeden interfejs
w stylu DS Compare 0.6.4: dodawanie plików i folderów, przeciąganie do okna,
wybór modelu głównego, moduły kosztorysu i raport ich gotowości. Bez podglądu 3D.

## Gotowy program Windows

Użytkownik nie musi kompilować źródeł ani instalować Pythona. Gotowy instalator
powstaje w [GitHub Actions — DS Estimate Tauri Windows](https://github.com/damianink-png/DS-Estimate/actions/workflows/tauri-desktop-windows.yml).
W zakończonym pomyślnie przebiegu pobierz artefakt
**DS-Estimate-0.4-Parts-Automation-Windows-Installer**, rozpakuj ZIP i uruchom instalator EXE.
Brak artefaktu oznacza, że pakiet nie został jeszcze pomyślnie zbudowany.

Pliki ZIP `DS_Estimate_1.2_FIX81_...` oraz `FIX85_DO_POBRANIA.zip` w katalogu
głównym są zachowanymi starszymi pakietami źródłowymi. Nie są instalatorem 0.4.

## Stan modułów

[Szczegółowy raport funkcji i ograniczeń](desktop-tauri/docs/WORKSPACE_0_4_STATUS.md).

W aplikacji ten sam zakres jest dostępny w zakładce **Stan modułów** oraz
w eksporcie JSON/CSV. Masa pochodzi z B-Rep OCCT, koszty sumuje adapter Kwantflow.
Czasy wymagające technologii pozostają do uzupełnienia; nie są traktowane jako zera.

## Źródła i testy

W `desktop-tauri/`: `npm ci`, `npm test`, `npm run build`.
Testy interfejsu: `python tests/workspace_browser.py` (Playwright; atrapy mostka natywnego).
Rzeczywisty silnik CAD i instalator są kompilowane i testowane osobno w Windows CI.
Licencje oraz pochodzenie adaptowanych fragmentów: `desktop-tauri/COPYING`
i `desktop-tauri/THIRD_PARTY_NOTICES.md`.

