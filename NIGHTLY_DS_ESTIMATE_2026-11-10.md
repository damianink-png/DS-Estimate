# DS Estimate — nocny dziennik techniczny (2026-11-10/11)

## 2026-11-10, 22:55 Europe/Warsaw — iteracja 1

**Baza:** PR #7, branch `codex/cutting-audit-statuses-20261107`, commit `bfa6195eaa32e8e7a508c47d01b495c3f34daab0`.

**Stan przed zmianą:** GitHub Actions Windows run [42899382278](https://github.com/damianink-png/DS-Estimate/actions/runs/42899382278) **PASS**, w tym zainstalowana aplikacja, zbudowany przenośny OneEXE, test prawdziwego GUI i pliku STEP oraz upload zweryfikowanego artefaktu. Benchmark [42899381889](https://github.com/damianink-png/DS-Estimate/actions/runs/42899381889) **PASS**. Earthpress: 75 nierozpoznanych wystąpień (37 unikalnych geometrii), 62 wystąpienia / 25 geometrii z wykrytymi cechami B-Rep, 13 wystąpień / 9 geometrii z rodziną gotowego detalu, 0 nowych potwierdzonych półfabrykatów i 0 nowych potwierdzonych czasów. W audycie cięcia Earthpress 121/251 znanych, 130/251 oczekuje na wyjaśnienie. Brak podstaw, aby przedstawiać cechy geometryczne jako poprawę skuteczności certyfikacji półfabrykatów.

**Analiza kodu:** w `stock_recognition.py` funkcja `recognize_stock` próbuje trzech osi krótkiego profilu; `_short_profile` liczyła wszystkie ściany OCCT osobno dla każdej osi, gdy profil nie pasował do katalogu. W dużych złożeniach jest to zbędne powtarzanie tego samego kosztownego zapytania B-Rep. Limit 32 ścian pozostaje bez zmian.

**Poprawka:** commit `d39ce20a3b6ee60d40576af09f0bb047d387c4f4`: pamięć liczby ścian ograniczona do jednego wywołania `recognize_stock` dla pojedynczej bryły. Nie współdzieli danych pomiędzy detalami, nie zmienia logiki rozpoznawania, tolerancji, mas, grupowania ani wyceny. W najgorszym przypadku zmniejsza liczbę pełnych enumeracji ścian w próbach trzech osi z 3 do 1; rzeczywisty zysk wydajności nie jest jeszcze zmierzony.

**Walidacja:** nowe przebiegi CI uruchamiają się po commicie dziennika; do uzyskania wyników nie oznaczać zmiany jako PASS. Następna iteracja powinna porównać SHA, logi testów i metryki Earthpress; priorytetem pozostaje potwierdzanie półfabrykatów bez fałszywych trafień.
