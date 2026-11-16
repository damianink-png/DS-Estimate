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


## 2026-11-11, 02:00 Europe/Warsaw — iteracja 4

**Punkt odniesienia:** PR #7, SHA `decfee8ac12e4d7fb1ba918373831274993e55ee`. Benchmark oryginalnych STEP [42928179352](https://github.com/damianink-png/DS-Estimate/actions/runs/42928179352) **PASS**; Windows/OneEXE [42928179996](https://github.com/damianink-png/DS-Estimate/actions/runs/42928179996) **PASS**. Log Windows potwierdza test prawdziwego zainstalowanego GUI i ponowny test przenośnego EXE z CAD; wynik joba jest success. Benchmark `PUBLIC_PINNED_REGRESSION_PASS` potwierdza niezmienione masy, grupy i częściowe pokrycie cięcia. Wcześniej odnotowane liczby Earthpress pozostają punktem odniesienia: 75/37 nieznanych półfabrykatów, 62/25 cech B-Rep, 13/9 rodzin gotowego detalu, 0 nowych certyfikowanych półfabrykatów i 0 nowych potwierdzonych czasów; 121/251 wystąpień znanych w audycie cięcia. **Nie ma jeszcze wzrostu skuteczności certyfikacji.**

**Problem wydajności:** `_short_profile` sprawdza, czy bryła ma więcej niż 32 ściany, lecz `sum(1 for _ in api.shapes(...))` enumerowało wszystkie ściany, nawet gdy 33. już wykluczała dalszą próbę przekroju. Duże nieregularne detale Earthpress mogły niepotrzebnie wymuszać pełne przejście po B-Rep.

**Poprawka:** `fd9a2f590e7d4183d01cbd721e413d1b53ddb3c7`: zatrzymaj enumerację najpóźniej na 33. ścianie, zachowując identyczny warunek `face_count>32` i ten sam wynik dla wszystkich brył. Cache nadal lokalny dla jednej bryły. Bez zmian tolerancji, sposobu klasyfikacji, masy, grupowania i kosztu. Zysk CPU jest zależny od złożoności ścian; nie deklarować liczbowego przyspieszenia bez pomiaru.

**Walidacja:** końcowy commit dziennika uruchomi benchmark i Windows/OneEXE. Wynik dla nowego SHA **niezweryfikowany** na moment zapisu. Kolejna iteracja powinna odczytać finalne run ID, potwierdzić brak regresji i skupić się na wiarygodnej certyfikacji stock zamiast podnoszenia wskaźników samych cech geometrycznych.


## 2026-11-11, 03:00 Europe/Warsaw — iteracja 5

**Zweryfikowany punkt odniesienia:** SHA `a5484f3f1afce83b6a7b347d3d716c0a3d44a7d7`; benchmark STEP [42935825245](https://github.com/damianink-png/DS-Estimate/actions/runs/42935825245) **PASS**, Windows/OneEXE [42935825082](https://github.com/damianink-png/DS-Estimate/actions/runs/42935825082) **PASS**. Test Windows uruchomił zainstalowane GUI i przenośny samorozpakowujący EXE na oryginalnym STEP. OneEXE z tego SHA: 292268358 B, SHA256 `0360A8F5928ED0352F9AC0948F5C5DBE6D4214D496D14812576BBB657D21C0C4`.

**Rozpoznanie na baseline:** Earthpress 75 nierozpoznanych wystąpień / 37 geometrii; cechy B-Rep na 62 / 25; 13 wystąpień / 9 geometrii z rodziną gotowego detalu; 48 kandydatów normaliów (42 śruby/nakrętki + 6 smarowniczek), **0** nowych certyfikowanych półfabrykatów i **0** nowych certyfikowanych czasów. Audyt cięcia Earthpress: 121/251 znanych, 130 oczekujących. Nie ma podstaw do deklarowania wzrostu automatycznej wyceny.

**Wykryty błąd poprawności:** `convex_polygon_section_kind` sprawdzało wyłącznie zgodność znaku kolejnych iloczynów wektorowych. Samoprzecinający się pięciokątny gwiazdowy obrys (pentagram) również ma skręty o tym samym znaku, przez co mógł zostać fałszywie rozpoznany jako wypukły `polygon-bar` i zasugerować nieprawidłowy półfabrykat. To błąd niezawodności klasyfikacji, nie problem wydajności.

**Poprawka:** `832c0cf3f1cd5f2f1ff9d04dc085d5bd840505ca` dodaje tani test przecięcia nieprzyległych krawędzi dla sekcji mających maksymalnie 12 krawędzi; niepewne niemal styczne/kolinearne przypadki pozostają nieznane. `3a732f382d31c12f9b418ae34f1350d1126693bc` dodaje regresję gwiazdy w obu orientacjach oraz kontrolę, że prosty wypukły wielokąt nadal jest rozpoznawany. Bez zmian w masie, grupowaniu, stawkach, interfejsie, progach tolerancji i certyfikacji czasu.

**Walidacja po zmianach:** nowe workflow benchmark/Windows uruchomione na commitach powyżej; w chwili wpisu ich końcowe wyniki nie są jeszcze potwierdzone. Nie deklarować PASS dla poprawki do czasu ukończenia obu workflow na finalnym SHA. Kolejna iteracja ma sprawdzić logi, szczególnie test `test_self_intersecting_star_is_not_polygon_stock`, liczniki Earthpress i pełne uruchomienie OneEXE.


## 2026-11-11, 04:00 Europe/Warsaw — iteracja 6

**Punkt odniesienia zweryfikowany:** SHA `68a64b394cb4d52594284e0f565bdb1e05b41ab1`; Windows/OneEXE run [42942723413](https://github.com/damianink-png/DS-Estimate/actions/runs/42942723413) **PASS**, benchmark rzeczywistych STEP [42942723486](https://github.com/damianink-png/DS-Estimate/actions/runs/42942723486) **PASS**. Earthpress: 75 nierozpoznanych wystąpień / 37 unikalnych geometrii, 62/25 z cechami B-Rep, 13/9 z rodziną gotowego detalu, 48 geometrycznych kandydatów normaliów, 0 nowych certyfikowanych półfabrykatów i 0 nowych czasów. Audyt cięcia: 121/251 znanych, 130/251 do weryfikacji. Masy, grupy i czasy częściowe stabilne, pełna wycena nadal niedostępna.

**Błąd bezpieczeństwa klasyfikacji:** dotychczasowy test samoprzecięć w `convex_polygon_section_kind` wykrywał właściwe przecięcia odcinków, ale nie odrzucał nieprzyległych wierzchołków o identycznych (lub bliższych niż tolerancja) współrzędnych. Taki samodotykający się obrys nie jest jednoznacznym wypukłym przekrojem i nie powinien dawać automatycznie `polygon-bar`.

**Zmiana:** `9093136a165eafb71614203e48f195effe2e67b4` odrzuca powtórzone wierzchołki przed analizą wypukłości; `2e6214c3ec0324b8fc54e75b6993325a28643882` dodaje regresję dokładnego i tolerancyjnego powtórzenia oraz dodatni przypadek prawdziwego wypukłego przekroju. Maksymalnie 12 wierzchołków, więc kontrola O(n²) jest tania. Nie zmienia progów tolerancji, mas, grupowania, wyceny ani UI. To poprawa ochrony przed fałszywymi trafieniami, **nie wzrost liczby potwierdzonych półfabrykatów**.

**Walidacja:** przed zmianą oba workflow były PASS na `68a64b...`. Po zmianie testów należy odczytać finalne run ID dla najnowszego SHA, a nie przenosić PASS z poprzedniego SHA. Dziennik jest celowo oddzielnym commitem; może anulować pośrednie uruchomienia przez politykę concurrency. Kolejna iteracja ma sprawdzić oba finalne CI i regresję `test_repeated_vertex_is_not_convex_stock`, szczególnie prawdziwe STEP.


## 2026-11-11, 05:00 Europe/Warsaw — iteracja 7

**Punkt odniesienia:** SHA `49e3a80ebf5514712696ee2299a9367f5d67db36`, Windows/OneEXE [42949622120](https://github.com/damianink-png/DS-Estimate/actions/runs/42949622120) **PASS** oraz publiczny benchmark STEP [42949622013](https://github.com/damianink-png/DS-Estimate/actions/runs/42949622013) **PASS**. Potwierdzono stabilność Earthpress: 75 nierozpoznanych wystąpień / 37 unikalnych geometrii, 62 wystąpienia / 25 geometrii z cechami B-Rep, 13 wystąpień / 9 geometrii z rodziną gotowego detalu, 48 kandydatów normaliów, 0 dodatkowo certyfikowanych półfabrykatów i czasów. Cięcie 121/251 znanych, 130/251 niepotwierdzonych; pełna wycena nadal niedostępna.

**Wykryta luka w walidacji:** `beveled_rectangle_section_kind` sprawdzał długości i położenia odcinków fazki, ale nie odrzucał powtórzonego nieprzyległego wierzchołka. Samodotykający się obrys nie stanowi poprawnego prostego przekroju i nie powinien tworzyć nawet sugestii półfabrykatu `square-bar` / `rectangular-bar` z fazką.

**Zmiany:** `e02fe5b58223a564ce63263fd3bae088c9da9dce` dodaje kontrolę identycznych i tolerancyjnie bliskich nieprzyległych wierzchołków, bez zwiększenia limitu 11 wierzchołków (koszt O(n²), maksymalnie 55 porównań). `5d7f88aa36598dcdbb189161c8b948027bfbbd54` dodaje negatywne przypadki testowe dokładnego i bliskiego powtórzenia oraz pozytywny test prawidłowej fazki. Nie zmieniono progów tolerancji, mas, grupowania, czasu cięcia ani UI.

**Walidacja po zmianach:** uruchomienia GitHub Actions dla najnowszego SHA należy sprawdzić po ukończeniu. PASS na poprzednim `49e3a80...` nie jest dowodem dla nowej poprawki. Cel: brak fałszywego rozpoznania półfabrykatu; nie deklarować wzrostu skuteczności na Earthpress bez nowych liczników. Testy realnego Windows/OneEXE i STEP są obowiązkowe przed wydaniem.


## 2026-11-11, 06:05 Europe/Warsaw — iteracja 8

**Zweryfikowany punkt odniesienia:** SHA `c04989fe77fe2fd445325b1f31e7625f175ec29d`; Windows/OneEXE [42956647775](https://github.com/damianink-png/DS-Estimate/actions/runs/42956647775) **PASS**, benchmark rzeczywistych STEP [42956647636](https://github.com/damianink-png/DS-Estimate/actions/runs/42956647636) **PASS**. Test Windows obejmował rzeczywistą zainstalowaną aplikację, OneEXE i silnik CAD. OneEXE: 292268413 B, SHA256 `0F5D918186B8F87322BF06F907ED3016FC8491D2ED76DECA748DB47B5525135D`.

**Rozpoznawanie przed zmianą:** Earthpress: 75 nierozpoznanych wystąpień / 37 geometrii, 62 wystąpienia / 25 geometrii z cechami B-Rep, 13 wystąpień / 9 geometrii z rodziną gotowego detalu, 48 geometrycznych kandydatów normaliów, 0 dodatkowych potwierdzonych półfabrykatów i 0 potwierdzonych czasów. Cięcie: 121/251 znanych, 130/251 oczekujących; pełna wycena niedostępna. Zgodność mas, grupowania i godzin częściowych potwierdzona `PUBLIC_PINNED_REGRESSION_PASS`.

**Luka w klasyfikatorze:** `orthogonal_section_kind` rozpoznaje standardowe przekroje L/U/T/I oraz Z/omega z siatki pól, lecz nie sprawdzał, czy nieprzyległy wierzchołek został ponownie odwiedzony. Samodotykający się obrys może zafałszować topologię mimo pozornie poprawnych osi i pola. To analogiczna ochrona do poprzednio dodanej dla `convex_polygon_section_kind` i `beveled_rectangle_section_kind`.

**Poprawka:** `b671202b76353789b5080306ee1f0cb30bf33fd3` odrzuca nieprzyległe wierzchołki odległe o <= tolerancję przed rozpoznaniem siatki ortogonalnej; sąsiadujące powtórzenia od podziału krawędzi STEP pozostają dozwolone. `65949bd4006a972e411699bbbab1de1342fef52a` dodaje negatywne testy dokładnego i tolerancyjnie bliskiego powtórzenia oraz pozytywny test dopuszczalnego sąsiedniego duplikatu. Brak zmiany progów, cen, masy, grupowania, UI i logiki czasu.

**Walidacja:** oba workflow mają być zweryfikowane dla końcowego SHA z dziennikiem; wcześniejsze PASS nie stanowią dowodu dla nowych zmian. Nie deklarować wzrostu certyfikacji półfabrykatów bez potwierdzonych liczników na oryginalnych STEP. O 07:00 sprawdzić końcowe CI i przedstawić jeden raport bez kolejnych dużych zmian.
