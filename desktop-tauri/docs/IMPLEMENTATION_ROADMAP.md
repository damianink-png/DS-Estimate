# DS Estimate — plan wdrożenia i stan prac

Projekt: `damianink-png/DS-Estimate`, gałąź `main`, Windows Tauri 2 / Svelte 5 + Python OCCT.
Ten plik jest trwałym rejestrem postępów dla godzinnych iteracji. Po każdej zmianie aktualizuj statusy i wpisuj SHA oraz link do CI.
Nie oznaczaj **DONE** bez odpowiedniego testu. **CODED** oznacza tylko wdrożenie oczekujące na CI.
Nie zmieniaj progów regresji tylko po to, aby uzyskać PASS.

## Etap I — przyspieszenie i obserwowalność CAD (P0)
- [ ] 1. Profilowanie importu STEP, B-Rep, sygnatur, sprawdzania członków, konturu cięcia, pamięci i czasu całości — PARTIAL: okresowe postępy na stderr, także w przypadku timeout; pamięć nadal do dodania
- [ ] 2. Ograniczenie porównań członków grupy przez bezpieczne ponowne użycie dowodów — PARTIAL: grupowanie członków po dokładnym IsPartner(TShape) i sprawdzanie tylko pierwszego członka każdej rodziny TShape; wymagane potwierdzenie CI i profilowania
- [x] 3. Lazy evaluation sygnatur powierzchni/ścian, bez osłabienia walidacji — CODED, CI oczekuje
- [ ] 4. Cache wyników par: klucz obejmuje geometrię, transformację i tolerancję, wynik może być UNKNOWN
- [x] 5. Korekta sygnatur geometrycznych opartych na objętości i powierzchni w `src/lib/geometry.mjs` — CODED, testy i CI oczekują
- [ ] 7. Jednoznaczne wyniki: EQUAL / DIFFERENT / UNVERIFIED

## Etap II — niezawodność geometrii
- [ ] 6. Dodatkowe niezmienniki przed drogimi wywołaniami OCCT
- [ ] 8. Audyt tolerancji objętości i wymiarów, testy rzeczywistych STEP
- [ ] 9. Cache transformacji i orientacji
- [ ] 10. Szybka masa i inwentarz niezależnie od pełnego grupowania
- [ ] 11. Zarządzanie pamięcią, timeouty etapów i anulowanie
- [ ] 12. Izolacja porównań problematycznych w procesach

## Etap III — import dokumentacji projektu
- [ ] 13. XCAF/STEPCAF: hierarchia złożenia, wystąpienia i nazwy
- [ ] 14. Materiały, części kupowane, beton i zakres produkcji; brak globalnego założenia o stali
- [ ] 15. Asynchroniczny, anulowalny silnik CAD i postęp przez Rust/Tauri
- [ ] 16. Cache projektu i przeliczenie ofert bez ponownego importu CAD
- [ ] 17. PDF wektorowy, OCR skanów, źródła i pewność odczytu
- [ ] 18. DXF/DWG, Excel, obrazy, archiwa, rewizje i kontrola duplikatów

## Etap IV — technologia i wycena
- [ ] 19. Detekcja spoin z dokumentacji i zweryfikowane powiązanie z modelem
- [ ] 20. Profile maszyn i materiałów, czasy technologiczne cięcia
- [ ] 21. Cechy CNC, półfabrykat i szacowanie operacji
- [ ] 22. Właściwy silnik Deepnest, sprawdzanie kolizji i wykorzystania arkusza
- [ ] 23. Spójny kosztorys z Kwantflow: czas, stawka, operacje, zakres i niepewność
- [ ] 24. Zapis projektów, rewizje i eksport ofert z pochodzeniem wyników

## Bramki jakości (bez zmian baseline bez niezależnego uzasadnienia)
- `portal-frame`: 15 brył, 3 grupy
- `stepgen-frame`: 1 bryła, 1 grupa
- `earthpress`: 251 brył, 97 grup
- `dockhub`: 541 brył, 111 grup, para 247/267 **nigdy nie może zostać automatycznie połączona bez dowodu**
- Masy STEP, częściowo znane czasy cięcia i zgodność dokumentacji z zamrożonymi próbkami
- Zakończenie DockHub w 240 s w benchmarku CI; niedokończona analiza nie jest PASS
- Kompilacja **pełnej** Windows Tauri/NSIS z dostarczanym silnikiem CAD; integrować i testować UI → import → kosztorys
- Nie przedstawiać automatycznie wyliczonych czasów spawania, CNC i montażu bez zweryfikowanych źródeł

## Dziennik iteracji
- 2026-11-03, start Etapu I: znaleziono błąd `geometrySignature`, dla której `x/(x*relTol)` nie odróżniało dodatnich wartości. Zmieniono ją na logarytmiczne przedziały względne, zachowano oddzielny dowód B-Rep, dodano testy i uruchomienia CI. Status: CODED, weryfikacja w toku.
- Ostatni znany stan przed tą zmianą: commit `c42bd87e`, Windows `41699158499` **PASS**, benchmark `41699158586` **FAIL**, DockHub `ENGINE_TIMEOUT`.

- 2026-11-03, iteracja 2: Windows run 41704191065 PASS, public run 41704193387 FAIL (DockHub timeout, brak inventory; niezależny audyt pary 247/267 nie może potwierdzić wyniku bez inventory). Dodano lazy face-area dla członków grup oraz diagnostykę kosztu właściwości brył i weryfikacji członków. Nie zmieniono kryterium dopasowania ani baseline; CODED, CI oczekuje.

- 2026-11-03, iteracja 3: Windows 41707301072 PASS; benchmark 41707301286 FAIL: DockHub timeout 240 s (czas całej próby ~552.5 s), brak inventory; audyt 247/267 nie może potwierdzić niełączenia w wyniku. Dodano cykliczne DS-CAD-PROGRESS co 25 brył (stderr zapisywany także przy timeout), dokładny czas odrzuconych kandydatów w matches_every_group_member, liczniki odrzuceń i test AST ścieżek wyjścia. Bez zmian kryteriów grupowania. CODED, CI oczekuje.

- 2026-11-03, iteracja 4: Windows 41716648076 PASS, benchmark 41716648217 FAIL (DockHub 419.44 s czasu zewnętrznego, timeout silnika 240 s; EarthPress 251/97, ~58.9 s, memberValidationSeconds 35.264 s / 389 par). Zastosowano bezpieczny skrót: członek grupy współdzielący OCCT TShape z reprezentantem nie wymaga ponownego Boolean po uprzednim dowodzie candidate-representative. Nie dotyczy przybliżonych sygnatur ani różnych TShape. Dodano licznik memberPartnerSkips i kontrolę źródła. CODED, CI oczekuje. Jeżeli brak oszczędności, kolejny krok: profilowanie kosztów per para i cache dowodów, bez transytywności tolerancji.

- 2026-11-03, iteracja 5: Windows 41725657025 PASS, benchmark 41725656899 FAIL; DockHub timeout 240 s (cała próba ~417.39 s), 3/4 ENGINE_OK, brak inventory DockHub. Dotychczasowe logi Actions nie eksponują DS-CAD-PROGRESS z przechwyconego stderr; wprowadzono drukowanie ostatnich 8 znaczników i końcówki stderr przy timeout oraz zapis do manifestu. To wyłącznie poprawka diagnostyczna benchmarku, NIE naprawa timeoutu; wymagane kolejne CI i analiza artefaktów. Nie zmieniono baseline ani kryteriów B-Rep.

- 2026-11-04, iteracja 6: benchmark 41734019573 FAIL: DockHub 534.72 s zewnętrznie, brak inventory. Znaczniki postępu: przy 375 bryłach / 77 grupach memberValidationSeconds=292.689 s, memberValidationPairs=2605, memberPartnerSkips=0, a główne translacje/obroty łącznie ok. 60 s. EarthPress 251/97, memberValidationSeconds=46.911 s. Rozszerzono bezpieczne pomijanie powtórnych B-Rep na wszystkie wcześniej niezależnie potwierdzone rodziny identycznych OCCT TShape (nie tylko TShape reprezentanta). Brak transytywności porównań tolerancyjnych; odrębny dowód dla każdej rodziny. CODED — CI do weryfikacji. Benchmark FAIL pozostaje otwarty; nie zmieniono limitu ani baseline.

- 2026-11-04, iteracja 7: Windows 41742833646 PASS, benchmark 41742833561 FAIL; DockHub ENGINE_TIMEOUT 240s, 3/4 ENGINE_OK, 247/267 independent non-merge not certifiable without inventory. EarthPress 251/97, memberValidationSeconds=47.321s, memberValidationPairs=389, memberPartnerSkips=0 — skrót IsPartner nie przyniósł mierzalnego efektu. Dodano ograniczone raportowanie kosztownych pojedynczych operacji B-Rep w walidacji członków (grupa, indeks, wystąpienie, czas, translacja/obrót), bez zmiany logiki akceptacji. CODED; następne CI wskaże konkretne wolne pary.

- 2026-11-04, iteracja 8: Windows 41750111292 PASS, benchmark 41750111309 FAIL; DockHub faktycznie przetworzył 541 brył, 110 grup, lecz 509.522 s (limit 240 s). memberValidationSeconds=408.462 s / 3442 par; memberPartnerSkips=0. Wynik 110 zamiast oczekiwanych 111 wymaga niezależnego audytu, nie wolno zmieniać baseline. Do profilowania dodano bezpieczny, opcjonalny pomiar working set Windows w komunikatach postępu i wynikach; bez zmian grupowania. CODED, oczekuje na CI. Następna iteracja: zweryfikować rzeczywiste porównania najdroższych grup i rozbieżność 110/111.
