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

## 2026-11-11, 01:01 Europe/Warsaw — iteracja 3

**Punkt odniesienia:** PR #7, SHA `fa67e14ce88d5b14b69bd028863dee0a1cc0e9e5`. Windows/OneEXE run [42919026269](https://github.com/damianink-png/DS-Estimate/actions/runs/42919026269) **PASS** (zainstalowany interfejs + portable OneEXE z rzeczywistym STEP); benchmark [42919026307](https://github.com/damianink-png/DS-Estimate/actions/runs/42919026307) **PASS**. Ostatni artefakt OneEXE ID `13812383632`, rozmiar binarki 292260441 B. Earthpress: 251 brył, 96 grup, 333.7932759 kg ekwiwalentu stali przy 7850 kg/m³, 121/251 znanych wystąpień w audycie cięcia, 130 wymagających weryfikacji. Nierozpoznane półfabrykaty: 75 wystąpień / 37 geometrii, 62/25 z cechami B-Rep, 13/9 z rodziną gotowego detalu; certyfikowanych nowych półfabrykatów i czasów nadal **0**. Benchmark nadal nie zapewnia pełnej automatycznej wyceny.

**Analiza wydajności:** w `stock_recognition.recognize_stock` zbierano **wszystkie** unikalne osie z krawędzi i płaszczyzn, mimo że następny etap rozpatrywał tylko `axes[:8]`. Przy dużych detalach powodowało to zbędne porównania kierunków OCCT. Dodatkowo sortowano pełną listę krawędzi ponownie dla każdej próbowanej osi.

**Zmiana:** commit `ea4e0133175705a9392f73908501441bf87e34eb`: przerwij deduplikację po 8 osiach i użyj wcześniej posortowanych krawędzi dla wyboru wektora poprzecznego. Kolejność pierwszych 8 osi, limity, geometria, warunki klasyfikacji, mass/grouping/cost i zasady niecertyfikowania nieznanych brył są niezmienione. Oszczędność CPU zależy od liczby kierunków; nie deklarować liczbowego przyspieszenia bez pomiaru.

**Walidacja po zmianie:** commit dziennika uruchomi ponownie workflow dla finalnego SHA. **Nie oznaczać nowego SHA jako PASS**, dopóki oba runy Windows/OneEXE i benchmark STEP nie zakończą się pomyślnie. Następna iteracja powinna sprawdzić finalne run ID, wyniki rozpoznawania i czasy, szczególnie Earthpress.
