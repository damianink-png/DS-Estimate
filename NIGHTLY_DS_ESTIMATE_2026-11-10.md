# DS Estimate — nocny dziennik techniczny (2026-11-10/11)

## 2026-11-10, 22:55 Europe/Warsaw — iteracja 1

**Baza:** PR #7, branch `codex/cutting-audit-statuses-20261107`, commit `bfa6195eaa32e8e7a508c47d01b495c3f34daab0`.

**Stan przed zmianą:** GitHub Actions Windows run [42899382278](https://github.com/damianink-png/DS-Estimate/actions/runs/42899382278) **PASS**, w tym zainstalowana aplikacja, zbudowany przenośny OneEXE, test prawdziwego GUI i pliku STEP oraz upload zweryfikowanego artefaktu. Benchmark [42899381889](https://github.com/damianink-png/DS-Estimate/actions/runs/42899381889) **PASS**. Earthpress: 75 nierozpoznanych wystąpień (37 unikalnych geometrii), 62 wystąpienia / 25 geometrii z wykrytymi cechami B-Rep, 13 wystąpień / 9 geometrii z rodziną gotowego detalu, 0 nowych potwierdzonych półfabrykatów i 0 nowych potwierdzonych czasów. W audycie cięcia Earthpress 121/251 znanych, 130/251 oczekuje na wyjaśnienie. Brak podstaw, aby przedstawiać cechy geometryczne jako poprawę skuteczności certyfikacji półfabrykatów.

**Analiza kodu:** w `stock_recognition.py` funkcja `recognize_stock` próbuje trzech osi krótkiego profilu; `_short_profile` liczyła wszystkie ściany OCCT osobno dla każdej osi, gdy profil nie pasował do katalogu. W dużych złożeniach jest to zbędne powtarzanie tego samego kosztownego zapytania B-Rep. Limit 32 ścian pozostaje bez zmian.

**Poprawka:** commit `d39ce20a3b6ee60d40576af09f0bb047d387c4f4`: pamięć liczby ścian ograniczona do jednego wywołania `recognize_stock` dla pojedynczej bryły. Nie współdzieli danych pomiędzy detalami, nie zmienia logiki rozpoznawania, tolerancji, mas, grupowania ani wyceny. W najgorszym przypadku zmniejsza liczbę pełnych enumeracji ścian w próbach trzech osi z 3 do 1; rzeczywisty zysk wydajności nie jest jeszcze zmierzony.

**Walidacja:** nowe przebiegi CI uruchamiają się po commicie dziennika; do uzyskania wyników nie oznaczać zmiany jako PASS. Następna iteracja powinna porównać SHA, logi testów i metryki Earthpress; priorytetem pozostaje potwierdzanie półfabrykatów bez fałszywych trafień.


## 2026-11-10, 23:55 Europe/Warsaw — iteracja 2

**Baza przed zmianą:** `a0b86422fa18bba69d2762d8fde96caa80d6305a`; benchmark [42909844084](https://github.com/damianink-png/DS-Estimate/actions/runs/42909844084) **PASS**, Windows/OneEXE [42909843819](https://github.com/damianink-png/DS-Estimate/actions/runs/42909843819) **PASS**. Poprzedni niezależny run `d39ce20...` anulowany przez następujący po nim commit dziennika, dlatego za punkt odniesienia przyjęto ukończony run `a0b86422...`. Nie ma podstaw do twierdzenia, że poprawiła się liczba certyfikowanych półfabrykatów: Earthpress nadal 75/37 nieznanych, 62/25 cech B-Rep, 13/9 rodzin, 0 dodatkowych potwierdzonych blanków.

**Problem wydajności:** `recognize_stock` na nieznanych bryłach zbiera diagnostykę oryginalnych ścian B-Rep. Dla każdej ściany planarnej wykonuje kosztowne `GProp_GProps` + `surface_props`, chociaż do wyniku `finishedBrepSurfaceEvidence.planes` trafia najwyżej 64 pierwszych rekordów. Przy wielu ścianach płaskich jest to zbędna integracja geometryczna.

**Poprawka:** `dd11c102056f79fecbfab7ae7ac7945e2e350f3f`: po zgromadzeniu 64 poprawnych rekordów planarnej diagnostyki pomijane jest dalsze wyliczanie pól powierzchni, lecz zachowana jest pełna liczba `planeFaceCount`. Nie zmienia to logiki rozpoznawania stock, masy, grupowania ani wyceny; dane 64 pierwszych płaszczyzn i pełne liczby ścian pozostają dostępne. Oszczędność CPU zależy od liczby płaskich ścian na bryłę; brak pomiaru czasu na oryginalnym STEP.

**Walidacja:** commity z poprawką i niniejszym dziennikiem uruchamiają CI; wyniku dla nowego SHA jeszcze nie potwierdzono. Kolejna iteracja: sprawdzić PASS/FAIL i porównać pełny benchmark oraz wydajność, nie przedstawiać optymalizacji diagnostyki jako poprawy certyfikacji półfabrykatów.
