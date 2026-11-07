# DS Estimate — rejestr wdrożeń planu cięcia (7 listopada 2026)

Dokument roboczy dla kolejnych godzinnych iteracji. Źródło wymagań:
`DS-Estimate-szczegolowy-plan-poprawy-ciecia.txt` (21 etapów, pakiety A–F).
Zmiany w PR [#7](https://github.com/damianink-png/DS-Estimate/pull/7).
**Żadna nieukończona pozycja nie staje się pełną wyceną, a brak czasu nie jest zerem.**

## Zasada produktu — minimalizm i pełna automatyzacja

**Wymaganie użytkownika (nadrzędne dla wszystkich pakietów A–F):**
**wrzucam STEP → program sam analizuje i pokazuje gotowe wyniki**.
Program ma pozostać maksymalnie minimalistyczny.

- **ZAKAZ** dodawania kolejnych opcji, obowiązkowych pól formularzy, nowych dialogów,
  dodatkowych zakładek, przycisków, ręcznych kroków i ekranów ustawień.
- Poprawiać **istniejące silniki**: wykrywanie półfabrykatów i operacji, pomiar
  geometrii, czasy, grupowanie i wyceny PLN — automatycznie na podstawie STEP.
- Import STEP uruchamia analizę automatycznie; domyślny ekran pokazuje tylko
  podstawowe **wyniki**: masa, półfabrykat, operacje/czasy, cena, jasny status
  brakujących danych. Szczegóły techniczne w testach/CSV/JSON/logach, nie w UI.
- Nie wymuszać uzupełniania parametrów, wybierania technologii ani potwierdzania
  każdego detalu. Istniejące korekty ręczne pozostają **opcjonalne** i nie
  blokują automatycznej analizy.
- Wynik niepotwierdzony nie może być podawany jako pełna, wiarygodna wycena
  ani zastępowany zerem; pokazać krótki komunikat „nieustalone”.
- W każdej godzinnej iteracji oceniaj poprawę **jakości automatu** i regresje
  UX; nie przedstawiaj dodanego formularza jako „rozwiązania” problemu CAD.

Stan: w PR #7 usunięto z widoku głównego nowo dodane, rozbudowane kody
przyczyn CAD, pozostawiając je w danych raportowych.

## Iteracja 7.11.2026 — optymalizacja silnika bez zmian UI

- **B, etap 3 (częściowo):** w `cad_backend/stock_recognition.py` usunięto drugie
  wywołanie kosztownego `_measured_solid_volume()` dla tej samej osi i bryły.
  Przy zgodnych 5 przekrojach pomiar objętości jest teraz wykonywany **raz**
  zamiast **dwukrotnie**. Nie zmienia to tolerancji 2% ani kryteriów dopasowania.
- Awaria pomiaru objętości jest jawnie zwracana jako `unknown`; nie wolno
  na tej podstawie wyliczyć czasu ani kosztu. Dotyczy także przekrojów zmiennych.
- Dodano 3 niezależne testy: liczba wywołań B-Rep, wyjątek przy przekroju stałym,
  wyjątek przy przekroju zmiennym.
- Poprzedni HEAD `7a85ed380a60951faf07f6455c10ddd02811f3d8`:
  Windows [42391172079](https://github.com/damianink-png/DS-Estimate/actions/runs/42391172079)
  PASS; benchmark [42391172162](https://github.com/damianink-png/DS-Estimate/actions/runs/42391172162)
  PASS. To nie jest jeszcze wynik testów nowego kodu.
- Weryfikacja nowych commitów: **oczekuje na GitHub Actions**; porównać
  liczbę rozpoznanych wystąpień oraz czas analizy Earthpress, Portal frame, StepGen
  po ukończeniu, bez przypisywania hipotetycznego przyspieszenia całej aplikacji.
- Następny krok: analiza nierozpoznanych osi i przekrojów z rzeczywistych
  STEP; zachować kryteria B-Rep i bez dodatkowych formularzy.

## Zamknięta bramka z poprzedniego kroku

- [x] Etapy 0–2 — częściowy model audytu każdej bryły / wystąpienia STEP, kody braków i eksport CSV/JSON.
- [x] Naprawa `cuttingPlan.error` → brak pozycji do wyceny **bez** fikcyjnego 0 min.
- [x] Korekta naddatków poprzecznych rur i RHS/SHS; zachowano pustą przestrzeń w przekroju.
- [x] Pierwsze testy **PR HEAD `f4b1fc28e5042a853032f73f726a765aba1aea9d`**:
  - Windows installer/UI: [42387811260](https://github.com/damianink-png/DS-Estimate/actions/runs/42387811260) PASS.
  - Prawdziwe STEP/PDF/BOM: [42387811224](https://github.com/damianink-png/DS-Estimate/actions/runs/42387811224) PASS.
- [x] Diagnoza CAD przeszła pełne testy HEAD `7a85ed3` (Windows i publiczny benchmark PASS); kolejny HEAD wymaga osobnych testów.

## Nowe odkrycie podczas audytu rzeczywistych modeli

Artefakt [13580851329](https://github.com/damianink-png/DS-Estimate/actions/runs/42387811224/artifacts/13580851329),
ścieżka `public_fabrication_output/cutting_occurrence_audit.json`.
Poniższe liczby należą do **aktualnej ścieżki desktop**, a nie do starego kalkulatora QuickEstimate:

| Model | Wystąpienia STEP | Znane czasy desktop | Nieustalone desktop | Pokrycie desktop |
|---|---:|---:|---:|---:|
| Earthpress | 251 | 121 | 130 | 48,2% |
| Portal frame | 15 | 6 | 9 | 40,0% |
| StepGen frame | 1 | 0 | 1 | 0,0% |

Historyczny, osobny kalkulator QuickEstimate zachowuje referencję Earthpress **89/251, 35,5%, 4,57144 h**. Różnice nie są dowodem poprawności metod i nie wolno bez weryfikacji przepisywać referencji.

**Uwaga diagnostyczna:** wcześniejszy audyt oznaczył wszystkie 130 braków Earthpress jako
`MATERIAL_TECHNOLOGY_UNKNOWN`, mimo że CAD zwrócił **131** brył o typie `stockHint.kind = unknown`.
Przyczyną był komunikat `Przyjęto stal...`, który maskował podstawowy problem z geometrią.
Naprawa powinna nadawać priorytet `UNKNOWN_STOCK` i przenosić oryginalny `stockHint.reason` z CAD.

Przyczyny nierozpoznanych półfabrykatów w **całym** Earthpress (nie tylko 130 braków):
- 67: brak jednoznacznego wydłużonego, osiowo zorientowanego przekroju;
- 59: otwarty, złożony lub nieobsługiwany przekrój;
- 4: objętość bryły niezgodna z postulowanym stałym przekrojem;
- 1: przekrój zmienia się wzdłuż części.

To są *powody odrzucenia przez obecny algorytm*, a nie dowód rzeczywistego typu półfabrykatu. Zwłaszcza pozycje `COMPOUND` i `portal-frame` wymagają jawnej weryfikacji podziału technologicznego.

## Kolejność następnych iteracji

1. **A, dokończenie Etapu 1:** uruchomić na pełnym publicznym benchmarku nowe kody `UNKNOWN_STOCK` i przyczyny szczegółowe; zweryfikować zgodność 251/15/1 oraz sumy statusów, porównać raport przed/po, usunąć ewentualny FAIL.
2. **B, Etap 3:** rozpoznanie lokalnych osi i przekrojów niezależnie od obrotu. Najpierw testy obróconych detali, w tym nieregularnych; nie rozluźniać dopasowania identyczności.
3. **B, Etap 4:** blachy płaskie — pomiar grubości, konturów, liczby przebić, rozróżnienie otworów i kieszeni; brak pomiaru = czas nieustalony.
4. **B, Etap 5:** RHS/SHS, CHS, ceowniki, kątowniki, I/T, pręty; pomiary w kilku przekrojach, końce ukośne, otwory, promienie. Porównanie z katalogiem bez wymuszania błędnego dopasowania.
5. **B, Etap 7:** półfabrykat, naddatki, masa netto/przygotówki, odpady i sposób zakupu; brak podwójnego materiału.
6. **C, Etap 8:** wspólny model operacji i odwzorowanie cech. Dzisiaj historyczny benchmark i GUI liczą innymi kalkulatorami; scalić dopiero po niezależnych testach zgodności.
7. **C, Etapy 10–13:** technologiczny wybór maszyny, czasy piły/lasera/plazmy/palnika, grupowanie partii, bez ukrytego nestingu.
8. **D, Etapy 14–15:** poprawa automatycznej korekty i weryfikacji, kompletność i brak zera za brak — bez nowych kolumn/formularzy w domyślnym widoku, bez wymagania ręcznej interwencji.
9. **E, Etapy 6 i 9:** blachy gięte i scalone bryły. W pierwszym wydaniu scalone konstrukcje przynajmniej wykrywać i jawnie oznaczać, nie dopisywać fikcyjnych cięć.
10. **F, Etapy 16–21:** integracje, wydajność, niezależne przypadki analityczne, prawdziwe STEP+PDF+BOM, instalator Windows/EXE i test użytkowy.

## Warunki przejścia do następnego kroku

- Zakończony PR HEAD Windows CI i test trzech prawdziwych projektów, bez znanych regresji.
- Żadna zmiana nie gubi brył, nazw, grup, cen zakupu, ręcznych korekt ani ograniczeń.
- Każda nowa wartość czasu ma podstawę: zmierzona geometria + wybrana maszyna + jawne normy.
- Brak rozpoznania zawsze otrzymuje kod, nie pozorne 0.
- Po każdym etapie zapisać commit, testy PASS/FAIL i różnice względem poprzedniego raportu.
- Nie scalać automatycznie do `main`; wydanie Windows dopiero po pełnym smoke teście.

Automatyczna kolejna iteracja powinna najpierw sprawdzić najnowszy HEAD i udokumentowane
PASS/FAIL, dopiero potem wprowadzić następny mały pakiet.

## Weryfikacja ORYGINALNEGO STEP — przekroje i osie (7.11.2026)

Przeprowadzono niezależny od klasyfikatora przegląd brył OCP bezpośrednio z
`earthpress/A-assembly.step` i `portal-frame/portal_frame.stp`.
Nie wystarcza interpretacja samego `stockHint.reason`.

- **Earthpress bryły 10–11:** model ma współosiowe powierzchnie walcowe
  Ø40/Ø34, oś walca `(0.9997303, 0, -0.0232220)`, odchylenie **1,33°** od X.
  Przekrój prostopadły do globalnej X to **2 elipsy**, a prostopadły do
  faktycznej osi walca to **2 okręgi** (R20/R17) w 2/10/25/50/75/90%
  długości. Zatem **rzeczywisty błąd wyboru płaszczyzny**. Cała bryła ma jednak
  191581.48 mm³ wobec 128805.90 mm³ dla odcinka prostego przewodu 369,37 mm:
  końce zawierają dodatkową geometrię; nie wolno z automatu traktować
  całości jako surowej rury i zaniżać masy/kosztu.
- **Earthpress bryły 182–185 i 193:** rzeczywiste czworokątne, nieprostokątne,
  stałe przekroje: 5×5×50 ma 750 mm³ (A=15 mm²), 6×6×45 ma 972 mm³
  (A=21,6 mm²). W tych konkretnych przypadkach płaszczyzna jest prawidłowa.
  Jest to **rozpoznanie geometrii gotowego detalu**, a nie dowód zakupu
  niestandardowego pręta lub wyboru piły zamiast frezowania.
- **Earthpress bryła 132:** przekroje prostopadłe do Y pozostają kołowe R5,
  ale końce są stożkowe (trzy powierzchnie stożkowe) i całkowita objętość nie
  odpowiada prostemu walcowi. Nie naprawiać przez zwiększenie tolerancji.
- **Earthpress bryła 20:** 80×28×95 mm, 13 powierzchni cylindrycznych,
  8 sferycznych i 2 toroidalne; w środku również B-spline. Nie jest
  rzetelnie rozpoznawalna z pojedynczego regularnego przekroju.
- **Portal Frame bryły 2–9:** przekrój jest poprawnie prostopadły do Z.
  W 2–3% długości wynosi **100×200 mm (A=20 000 mm²)**, w 10–90%
  **100×10 mm (A=1000 mm²)**, w 97–99% znowu **100×200**;
  objętość = 11 600 000 mm³. Posiada masywniejsze końce — to naprawdę
  **geometria o zmiennym przekroju**, nie przekrój wybrany pod kątem.
- **Portal Frame bryła 1 / StepGen bryła 1:** złożone bryły/scalone
  konstrukcje, nie wnioskować z pojedynczego przekroju ani bbox.

**NOWY priorytet godzinny:** zanim wdrożysz kolejną rodzinę kształtów, napraw
dobór **lokalnej osi technologicznej i prostopadłej płaszczyzny** (cylinder axis,
dominant planar normals, długość krawędzi jako poszlaka, wiele przekrojów).
Oddziel dowód *geometrii gotowej bryły* od dowodu *kształtu przygotówki*;
jeśli istnieją przyspawane/dodatkowe końce, rozpoznawaj rdzeń jako cechę
`tube-like core`, ale zostaw pełną masę i czas niewyceniony, dopóki nie da się
wywnioskować rozdziału procesów. Nie przydzielaj automatycznej piły
`polygon-bar` bez dowodu, że półfabrykat jest takim kupowanym przekrojem.


## Kontrola HEAD 83cb453 — 7.11.2026, 19:18 CET

- HEAD PR #7: `83cb45385fe8df7a34e64e40f333918f365f947b` (weryfikacja bezpośrednio z GitHub).
- Publiczny benchmark [42398795393](https://github.com/damianink-png/DS-Estimate/actions/runs/42398795393): **PASS**. Wszystkie 21 etapów joba `benchmark` przeszły, w tym kompilowany silnik OCCT, trzy publiczne modele i osobna bramka oryginalnego Earthpress `public_stock_axis_regression.py`. Artefakt [13585405319](https://github.com/damianink-png/DS-Estimate/actions/runs/42398795393/artifacts/13585405319) został opublikowany; szczegółowe liczniki nowego raportu wymagają odczytu jego JSON przed podaniem porównania przed/po.
- Windows [42398795310](https://github.com/damianink-png/DS-Estimate/actions/runs/42398795310): **IN PROGRESS** w chwili kontroli. `workspace-ui` PASS, `build-windows` dotarł do niezależnego benchmarku masy prasy, wcześniejsze 18 kroków PASS. Nie deklarować PASS całego Windows/instalatora i nie publikować EXE.
- Ostatni potwierdzony bazowy pomiar desktop (starszy artefakt): Earthpress 121/251 rozpoznanych czasów, 130 nieustalonych; Portal 6/15 i 9; StepGen 0/1 i 1. **Przed/po dla bieżącego HEAD: nieustalone**, dopóki nie zostanie odczytany aktualny `cutting_occurrence_audit.json` z artefaktu. Nie przedstawiać starszych wartości jako bieżących.
- Następna bramka: potwierdzić Windows PASS, odczytać liczby z bieżącego artefaktu, następnie dodać bezpośredni test zmiennego przekroju Portal Frame 2–9 (100×200 na końcach i 100×10 w środku) oraz nierozpoznanego surowca przy stożkowych końcach Earthpress 132. Nie zmieniać tolerancji ani nie wnioskować technologii z rdzenia geometrycznego.

## Pełny niezależny przegląd 75 nierozpoznanych brył — 7.11.2026

Przeanalizowano sam ORYGINALNY `earthpress/A-assembly.step` przez lokalny OCCT/OCP:
`STEPControl_Reader` → 251 `TopoDS_Solid` → niezależne objętości,
`BRepAdaptor_Surface` (planes/cylinders/cones/spheres/tori/BSplines),
osie cylindrów i bbox. Dane skonfrontowano z najnowszym skompilowanym
raportem `42400690874` (sha `ab944e89`), nie z heurystyką nazwy COMPOUND.

**75 nierozpoznanych** jest w zaledwie **37 grupach zweryfikowanych geometrii**:
- **44 wystąpienia, 11 grup:** wielokrotnie powtarzane powierzchnie
  cylindryczne/stożkowe + płaskie (np. bryły 88–93, 99, 106, 109, 122,
  125, 131, 135, 141); geometria charakterystyczna dla łączników i detali
  obrotowych, zgodnych z rodzinami BOM. Nie wymaga klasyfikatora profili
  wydłużonych. Materiał/zakup technologiczny nadal niepewne.
- **13 wystąpień, 11 grup:** płaszczyzny + cylindry (np. 25–30,
  49–51, 53–55, 95), otwory i elementy złożone; prawdopodobne obrabiane
  blachy/bloki, wymagają podziału na cechy.
- **5 wystąpień, 4 grupy:** cylindry + torusy/promienie,
  w tym osiowe wałki 62 i 71, obrabiane zakończenia.
- **3 wystąpienia, 3 grupy:** bardzo złożone powierzchnie z
  kulami/torusami (20, 21, 245).
- **2 wystąpienia, 2 grupy:** same powierzchnie płaskie (22, 31),
  więc bryły pryzmatyczne/schodkowe; błąd `not elongated` nie dowodzi
  skomplikowanej technologii.
- **3 wystąpienia, 3 grupy:** `unsupported section` (10, 11 i 250).
  Rdzenie Ø40/Ø34 dla 10 i 11 już są wykrywane poprawnie, lecz gotowa
  bryła ma dodatkowy materiał — surowiec nadal nieustalony; 250 ma
  11 płaszczyzn, 24 cylindry, 12 sfer, 4 torusy.
- **4 wystąpienia, 2 grupy:** rdzeń walcowy z obrobionymi końcami
  (132, 136, 174, 178), 3 stożki na bryłę.
- **1 wystąpienie, 1 grupa:** kanał UPN 80 po obróbce (15),
  `rawStockCandidate` już ma prawidłowy katalog UPN 80, 3/5 przekrojów.
- Razem 44+13+5+3+2+3+4+1 = **75**.

**Niezależny problem: 7 × `INVALID_HINT`, a nie faktycznie nieznany kształt:**
- **6 szt. SHS 60×60×3 i 50×50×3** (bryły 1–6) — przekrój B-Rep
  z promieniami naroży ma odpowiednio 660,70 mm² i 540,70 mm² zamiast
  684/564 mm² ostronarożnego wzoru kontrolnego.
  Różnica 3,41% / 4,13% przekracza obecną twardą tolerancję 2%:
  walidator raportu błędnie odrzuca poprawny pomiar. Naprawa: obliczać
  pole zgodne z promieniami narożnikowymi z B-Rep, **nie zwiększać
  tolerancji ogólnie**.
- **1 szt. (251)** — klasyfikator nadał `plate-candidate` po
  `sheet_hints`, ale bez kompletnego `lengthMm`/`widthMm`;
  naprawić spójność wymiarów zamiast oznaczać wynik jako gotowy.

**Portal Frame:** 8/9 nierozpoznanych to TA SAMA geometria
`shared-tshape-1`: 18 płaszczyzn, zmienna grubość końców na
4000 mm; dziewiąta to ogromna bryła modelu scalonego (960 płaszczyzn).
**StepGen:** 1 scalona bryła 129 płaszczyzn + 20 cylindrów.
To problem segmentacji/złożenia, nie jeden niespotykany profil.

### Następne konkretne iteracje godzinne

1. Osobny detektor osiowych części obrotowych oraz łączników, w
   pierwszej kolejności **44 wystąpienia**, zachowując nieustalone
   zakup/obróbkę kiedy brak dowodu.
2. Naprawić **6 fałszywych INVALID_HINT** rur SHS przez geometrię
   promieni i błąd kompletności blachy 251.
3. Rozpoznawanie płyt/bloków/otworów bez warunku L/W>3,5;
   profile z nacięciami i ukośne rdzenie rozdzielić od przygotówki.
4. Dla Portal Frame i StepGen odtworzyć rozkład na części z segmentów
   B-Rep/BOM, z zachowaniem sum masy, bez fikcyjnego cięcia i cen.

Wszystkie wskazania typu łącznik, wałek, frezowane są **hipotezami
geometrii/technologii**, nie pewnością zakupu, obróbki lub gatunku.


## Iteracja 7.11.2026, 20:17 CET — oryginalne B-Rep, testy osi i zmiennego przekroju

- HEAD wejściowy PR #7: `6c10b8149aa40d701a3f93ff8466400d3a52ff9e`.
- Ostatni ukończony Windows PASS: [42400691046](https://github.com/damianink-png/DS-Estimate/actions/runs/42400691046);
  public STEP PASS: [42400690874](https://github.com/damianink-png/DS-Estimate/actions/runs/42400690874).
  Runy [42405019245](https://github.com/damianink-png/DS-Estimate/actions/runs/42405019245)
  i [42405019206](https://github.com/damianink-png/DS-Estimate/actions/runs/42405019206)
  były IN PROGRESS przy kontroli, nie ogłaszać PASS.
- Odczytano bezpośrednio `ds_estimate_inventory.json` wygenerowane przez skompilowany
  silnik z oryginalnych STEP w artefakcie `13585448632`:
  Earthpress 10/11: Ø40×3, `geometric-core-only`, 191581.48 vs 128805.90 mm³;
  Earthpress 132: Ø10, 8830.84 vs 7963.94 mm³, stożkowe końce;
  Portal Frame 2–9: centralny 100×10, L4000, objętość
  11 600 000 vs 4 000 000 mm³ — nie jest to stały pręt.
- Dodano precyzyjne testy regresyjne **na oryginalnych danych publicznych STEP**
  do `tests/public_stock_axis_regression.py`:
  8× Portal Frame 2–9 (zakaz fałszywego stock i automatycznej piły)
  oraz Earthpress 132 (stożkowe końce, tylko rdzeń geometryczny).
  Commit testów: `028805140e20daf710d9ad938823fb00e6a7c13c`.
  Test jest już wywoływany przez workflow public benchmark. Status nowego
  commitu: **oczekuje na zakończenie CI**, nie deklarować PASS.
- Liczniki **przed**: Earthpress desktop 121/251 znanych czasów cięcia,
  130 nieustalonych; Portal 6/15 i 9; StepGen 0/1 i 1.
  **Po**: zmiana dotyczy wyłącznie regresji; algorytm i oczekiwane
  liczniki pozostają bez zmian. Nie udawać wzrostu skuteczności.
- Następnie: odczytać logi nowych runów; w razie FAIL naprawić;
  wdrożyć poprawki detektora osiowych łączników i walidatora SHS na
  podstawie oryginalnego B-Rep, bez zmiany tolerancji i bez nowych pól UX.


## Iteracja 7.11.2026, 21:11 CET — audyt osi i dowodów SHS

- PR #7 HEAD na początku: `beaaa0fa8a5ca970465b29fd8706da438cc25187`.
- GitHub Actions dla tego SHA: benchmark [42405496689](https://github.com/damianink-png/DS-Estimate/actions/runs/42405496689) **PASS**;
  Windows [42405496662](https://github.com/damianink-png/DS-Estimate/actions/runs/42405496662) **PASS**.
  Poprzednie runy `42405480336/337` anulowane przez nowy commit, nie FAIL.
- Bezpośrednie B-Rep wcześniejszego audytu: sześć SHS z zaokrąglonymi narożami
  mają pole inne od uproszczonego wzoru ostronarożnego; nie wolno tego
  naprawiać globalnym poluzowaniem tolerancji.
- Nowy commit `ead15dfac707f87073c2926c6621e4c5245c423f`:
  rozszerzenie testu oryginalnego Earthpress o jawny zapis dowodów
  `PUBLIC_ROUNDED_SHS_EVIDENCE` dla brył 1–6, bez zmiany klasyfikacji
  i bez zmian UI. Ten commit wymaga osobnego potwierdzenia CI.
- Liczniki przed/po bez zmiany silnika: Earthpress 121/251 znanych czasów,
  130 nieustalonych; Portal 6/15 i 9; StepGen 0/1 i 1.
  **Nie deklarować poprawy skuteczności** z samego testu diagnostycznego.
- Kolejny krok: odczytać nowy JSON diagnostyczny z logów, następnie
  poprawić walidację promieni naroży względem rzeczywistego B-Rep,
  bez zmiany 2% tolerancji. Osobno detektor osiowych łączników.

