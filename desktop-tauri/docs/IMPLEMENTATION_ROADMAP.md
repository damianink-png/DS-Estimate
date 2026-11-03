# DS Estimate — plan wdrożenia i stan prac

Projekt: `damianink-png/DS-Estimate`, gałąź `main`, Windows Tauri 2 / Svelte 5 + Python OCCT.
Ten plik jest trwałym rejestrem postępów dla godzinnych iteracji. Po każdej zmianie aktualizuj statusy i wpisuj SHA oraz link do CI.
Nie oznaczaj **DONE** bez odpowiedniego testu. **CODED** oznacza tylko wdrożenie oczekujące na CI.
Nie zmieniaj progów regresji tylko po to, aby uzyskać PASS.

## Etap I — przyspieszenie i obserwowalność CAD (P0)
- [ ] 1. Profilowanie importu STEP, B-Rep, sygnatur, sprawdzania członków, konturu cięcia, pamięci i czasu całości
- [ ] 2. Ograniczenie porównań członków grupy przez bezpieczne ponowne użycie dowodów
- [ ] 3. Lazy evaluation sygnatur powierzchni/ścian, bez osłabienia walidacji
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
