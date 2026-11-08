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


## Kontrola bieżącego HEAD — 7.11.2026, 22:11 CET

- PR #7 HEAD: `3ee49dd11c1fdb852e97c04d2763c8db0e6e8b47`.
- Publiczny benchmark [42409886979](https://github.com/damianink-png/DS-Estimate/actions/runs/42409886979): **PASS**; Windows [42409886980](https://github.com/damianink-png/DS-Estimate/actions/runs/42409886980): **PASS** (`workspace-ui` i `build-windows`).
- Odczytano bezpośrednio log joba `128515548608`. Earthpress: 251 brył; `CANDIDATE=85`, `GEOMETRY_ONLY=84`, `INVALID_HINT=7`, `UNKNOWN=75`; desktop cutting `known=121, pending=130`. Portal Frame `known=6, pending=9`; StepGen `known=0, pending=1`. **Bez wzrostu liczników względem poprzedniego PASS.**
- Test osi Earthpress 10/11 PASS; Portal Frame 2–9 i Earthpress 132 PASS. Log `PUBLIC_ROUNDED_SHS_EVIDENCE` pokazuje, że **natywny silnik już oznacza bryły 1–6 jako `square-hollow`**, a więc ich `INVALID_HINT` powstaje **w diagnostycznym `tests/public_stock_audit.py`**, nie w natywnym klasyfikatorze.
- Przyczyna w audycie: `_section_area_consistent` liczy `w*h-(w-2t)*(h-2t)`, czyli przekrój ostronarożny, i odrzuca rzeczywiste pole B-Rep z promieniami przy twardym progu 2%. **Nie wolno podnosić progu ani zastępować pola zmierzonego polem uproszczonym**. Potrzebny jest niezależny dowód promieni naroży z oryginalnego B-Rep i kontrola zgodności rzeczywistego pola z ich geometrią.
- To **diagnostyczne 6× INVALID_HINT**, nie dowód, że silnik nie rozpoznał sześciu rur. Osobno bryła 251 nie ma kompletu wymiarów blachy.
- W tej kontroli **nie wdrażano zmiany klasyfikatora**: brak wystarczającego potwierdzenia niezależnej formuły pola z promieni, a sztuczny PASS naruszyłby zakaz poluzowania tolerancji. Nie publikowano EXE i nie scalano do main.

**Następny bezpieczny krok:** w testach oryginalnego Earthpress pobrać rzeczywiste promienie naroży i zweryfikować pole z B-Rep dla sześciu SHS, dopiero potem poprawić audyt. Równolegle dodać detektor osi obrotowych dla 44 wystąpień, bez przypisywania technologii zakupowej i czasów.

## Iteracja 7.11.2026, 23:10 CET — oryginalne SHS i kontrola regresji

- Przed zmianą HEAD PR #7: `75d72fc7d18eaf16558013b77804a56b7783aff6`, otwarty.
- Weryfikacja bieżącego HEAD: benchmark [42414725370](https://github.com/damianink-png/DS-Estimate/actions/runs/42414725370) **PASS**; Windows [42414725327](https://github.com/damianink-png/DS-Estimate/actions/runs/42414725327) **PASS**.
- Log oryginalnego Earthpress: `CANDIDATE=85`, `GEOMETRY_ONLY=84`, `INVALID_HINT=7`, `UNKNOWN=75`; desktop cięcie `known=121/251`, `pending=130`. Portal `6/15`, StepGen `0/1`. **Przed/po: brak zmiany silnika i liczników.**
- Dodano rygorystyczny test pól B-Rep **sześciu SHS 50×50×3 / 60×60×3**: porównanie rzeczywistego `sectionAreaMm2` z wzorem ostrokątnym, oczekiwane 3–5% różnicy, zachowanie klasy `square-hollow`, pewności wyłącznie geometrii i braku automatycznego dowodu zakupu. Commit `f84d37b2cf540632d6e8337f9904fbc41fd090b3`.
- Test ten nie jest jeszcze potwierdzony przez Actions; jeżeli FAIL, zbadać rzeczywiste pola i pola `rawStockCandidate`, zamiast osłabiać asercje. Nie zmieniono tolerancji, operacji, interfejsu ani `main`.
- Następny etap: weryfikacja nowego runu; niezależny pomiar promieni naroży oryginalnych B-Rep, potem poprawka audytu tylko przy udokumentowanym promieniu. Równolegle detektor części obrotowych bez domniemania technologii.


## Iteracja 8.11.2026, 00:15 CET — weryfikacja oryginalnych SHS i powtarzalności

- Start HEAD PR #7: `e5e77108bf96bd93728f5b1c92f22813b92235b6`.
- Benchmark [42419451287](https://github.com/damianink-png/DS-Estimate/actions/runs/42419451287) **PASS**;
  Windows [42419451297](https://github.com/damianink-png/DS-Estimate/actions/runs/42419451297) **PASS**.
  Wcześniejsze `42419439532/42419439647` były **CANCELLED** wskutek nowszego commitu.
- Odczyt logu skompilowanego silnika na oryginalnym Earthpress:
  SHS bryły 1–2: 60×60×3, pole B-Rep 660.7023539873 mm² wobec
  684 mm² wzoru ostronarożnego (−3.406%);
  bryły 3–6: 50×50×3, pole 540.7023539873 mm² wobec
  564 mm² (−4.131%). Każde z sześciu `PUBLIC_ROUNDED_SHS_AREA_PASS`.
- Dodano test ścisłej powtarzalności pól B-Rep dla 2+4 wystąpień tych samych
  przekrojów, tolerancja rozrzutu pomiarów 1e−5 mm², **bez zwiększania
  tolerancji geometrii**. Commit `700b4e08055b798f4ddf8eaaa916cd088d87b89b`.
  Ten commit **wymaga potwierdzenia w nowych Actions**.
- Ostatni potwierdzony licznik bez zmian: Earthpress `known=121/251,
  pending=130`; Portal `6/15`; StepGen `0/1`. Audyt SHS nadal
  `INVALID_HINT=6`, dodatkowa blacha `INVALID_HINT=1`.
  Nie ma podstaw, by nazywać to wzrostem rozpoznania lub wyceny.
- Kolejny krok: pomiar rzeczywistych promieni naroży bezpośrednio z B-Rep
  i ścisły model pola z zaokrągleniami, a dopiero potem korekta audytu.
  Następnie detektor osiowych łączników; nie zgadywać surowca, technologii
  ani czasu cięcia.

## 8.11.2026, 01:16 CET — korekta fałszywego INVALID_HINT dla SHS

- HEAD wejściowy PR #7: `a71dd79af4adb834aab3b67c4ffadc1af91a8068`. GitHub Actions benchmark `42424478730` **PASS**, Windows `42424478738` **PASS**. Wcześniejsze uruchomienia `42424468736` i `42424468634` anulowano przez kolejne commity, nie traktować jako PASS.
- Przejrzano `tests/public_stock_audit.py`: walidator stosował wzór ostrokątny dla `square-hollow` i `rectangular-hollow` mimo udokumentowanych promieni z oryginalnego Earthpress. Poprawiono rozróżnienie: rozbieżność pola w profilach zamkniętych **nie jest INVALID_HINT**, lecz `UNVERIFIED` z jawnym powodem; zachowane rodzaj i rzeczywiste pole B-Rep. **Nie przyznano GEOMETRY_ONLY ani nie potwierdzono surowca, piły, frezowania czy kosztu.** Pozostałe błędy pól i wymiarów nadal `INVALID_HINT`; tolerancja 2% bez zmian.
- Commit kodu `abec1c4f4917943fb0ea6c72cb71a1d10defd902`. Oczekuje na nowy benchmark Windows; do jego zakończenia brak zweryfikowanych nowych liczników. Spodziewana tylko zmiana audytu 6× `INVALID_HINT` → `UNVERIFIED`; liczba znanych czasów cięcia nadal bazowo Earthpress 121/251, Portal 6/15, StepGen 0/1.
- Następny krok: bezpośredni pomiar łuków naroży SHS z oryginalnego B-Rep i niezależna kontrola pola przekroju; dopiero wtedy certyfikować geometrię. Potem 44 powtarzalne elementy obrotowo-złączne, bez przypisywania technologii bez dowodu.


## 8.11.2026, 02:15 CET — usunięcie FAIL testu audytu SHS/RHS

- Kontrola HEAD przed zmianą: `515f9072526f8d75346bef3569c3d753ea091a35`, PR #7 otwarty.
- Benchmark rzeczywistych STEP `42429011754`: **PASS**. Windows `42429011757`: **FAIL** w `workspace-ui`, etap `Stock report fixture regression (no CAD dependencies)`; `build-windows` pominięty.
- Log: dwa nieaktualne oczekiwania testu `test_section_area_must_agree_with_measured_dimensions` dla `square-hollow` i `rectangular-hollow`: test żądał `INVALID_HINT`, a kod świadomie zwracał `UNVERIFIED`, gdy pole B-Rep odbiega od wzoru ostronarożnego. To regresja kontraktu testowego, nie dowód błędnego przekroju. 187 testów JS PASS, 0 FAIL.
- Commit `24a53f4c7bb18a272eaa41e8c8e80c2a55de6d09`: poprawiono test tak, by SHS/RHS o niezgodnym polu pozostały `UNVERIFIED` (0% certyfikacji i jawna przyczyna), a inne przekroje nadal były `INVALID_HINT`. **Nie zmieniono tolerancji, silnika B-Rep ani algorytmu wyceny**.
- Wynik po zmianie: oczekiwanie na nowe Actions; nie deklarować PASS przed zakończeniem. Ostatnie potwierdzone liczniki cięcia: Earthpress 121/251, Portal Frame 6/15, StepGen 0/1 (bez zmiany algorytmu).
- Następny etap: odczytać wynik CI dla tego commitu; potem weryfikować promienie SHS na oryginalnym B-Rep i dopiero klasyfikację łączników, zachowując nieustalone półfabrykaty.

## 8.11.2026, 03:14 CET — CI odzyskane, test audytu SHS na oryginalnym STEP

- Wejściowy HEAD PR #7 `b1a2768ba8d0179400cbe8f4d293d27d87802a8b`; otwarty, bez merge.
- GitHub Actions: benchmark [42433536765](https://github.com/damianink-png/DS-Estimate/actions/runs/42433536765) **PASS**; Windows [42433536780](https://github.com/damianink-png/DS-Estimate/actions/runs/42433536780) **PASS**, oba joby `workspace-ui` i `build-windows`. Wcześniejszy FAIL `42429011757` usunięty.
- Odczyt z logu bieżącego benchmarku oryginalnych STEP: Earthpress `GEOMETRY_ONLY=84, CANDIDATE=85, UNVERIFIED=6, INVALID_HINT=1, UNKNOWN=75`; Portal `6/15` rozpoznanych czasów, StepGen `0/1`; Earthpress cięcie `121/251`, brak `130`. W porównaniu do starszego audytu 6 SHS zmieniło status `INVALID_HINT→UNVERIFIED` bez fałszywej certyfikacji i bez zmiany czasów cięcia.
- Zmiana kodu testu `4aaf80711fb6945f42928af5bcfcf7ebef6e4e95`: na **oryginalnym Earthpress** dodatkowo wywołano audyt na wyniku skompilowanego silnika; wymuszono dla wszystkich 6 SHS status `UNVERIFIED`, zachowanie pola B-Rep, brak `GEOMETRY_ONLY`. Nie zmieniono klasyfikatora, tolerancji ani wyceny.
- Nowy test wymaga osobnego PASS po commicie; nie twierdzić, że nowy HEAD już przeszedł CI. Nie publikowano EXE i nie scalano do main.
- Dalej: niezależny pomiar promieni naroży bezpośrednio z oryginalnego B-Rep i poprawa rozpoznania 44 obrotowych wystąpień bez zakładania przygotówki, piły ani frezowania.

## 8.11.2026, 04:10 CET — kontrola powtarzalnych brył złącznych

- Wejściowa baza: benchmark [42433536765](https://github.com/damianink-png/DS-Estimate/actions/runs/42433536765) PASS; Windows [42433536780](https://github.com/damianink-png/DS-Estimate/actions/runs/42433536780) PASS (workspace-ui oraz build-windows). Należy sprawdzić Actions dla nowego HEAD, ponieważ poprzedni PASS nie certyfikuje nowych zmian.
- W oryginalnym Earthpress 75 UNKNOWN tworzy 37 grup geometrii, w tym 44 wystąpienia obrotowo-złączne w 11 grupach. Dodano próbkę regresji 14 numerowanych wystąpień (88–93, 99, 106, 109, 122, 125, 131, 135, 141): dodatnia objętość oryginalnego B-Rep, brak niepotwierdzonego rawStockCandidate, brak automatycznej klasyfikacji przygotówki, wypisanie verifiedShapeKey do diagnostyki. Commit `2edbbf97d3caaa34f3cf600416a7fb5e7372b127`.
- To **test zabezpieczający**, nie nowy detektor. Jego PASS/FAIL na nowym HEAD jest jeszcze niepotwierdzony. Przed/po dla czasu cięcia nadal ostatnio potwierdzone Earthpress 121/251, Portal 6/15, StepGen 0/1. Nie przypisywać 44 wystąpieniom czasu piły ani frezowania bez dowodu przygotówki.
- Kolejny krok: pobrać artefakty nowego runu i zbadać faktyczne krzywizny/osiowość z oryginalnych STEP, następnie rozdzielić rozpoznanie geometryczne detali obrotowych od decyzji zakup/technologia. Bez zmian tolerancji i UI, bez merge do main.


## 8.11.2026, 05:11 CET — bramka oryginalnych łączników w audycie

- Zweryfikowano poprzedni HEAD `66694fce33a695a0e1705c086a3b3506b1c5f38a` bezpośrednio w GitHub Actions: benchmark [42441567130](https://github.com/damianink-png/DS-Estimate/actions/runs/42441567130) **PASS**, wszystkie 21 kroków benchmarku; Windows [42441567296](https://github.com/damianink-png/DS-Estimate/actions/runs/42441567296) **PASS**. Artefakt benchmarku [13602171489](https://github.com/damianink-png/DS-Estimate/actions/runs/42441567130/artifacts/13602171489) jest dostępny; szczegółowe liczniki jego JSON nie zostały w tej iteracji niezależnie odczytane.
- Commit testu `104e53d43fcc0bebed4542ffd3984e6ee27b9295`: rozszerzono bramkę **oryginalnego Earthpress** dla 14 wystąpień obrotowo-złącznych o sprawdzenie, że po przejściu przez osobny `stock_audit` nadal mają `UNKNOWN`, rodzaj `unknown` i nieutracony `verifiedShapeKey`. Chroni przed sztuczną promocją cylindrycznych powierzchni do gotowego półfabrykatu. Nowy commit wymaga własnego PASS w Actions; nie uznawać PASS poprzednika za wynik nowego testu.
- Przed/po: nie zmieniano algorytmu, więc **nie wykazano poprawy pokrycia**; ostatni potwierdzony odczyt: Earthpress 121/251 znanych czasów i 130 nieustalonych, Portal 6/15 i 9, StepGen 0/1 i 1. Aktualnych liczników po commicie nie certyfikowano.
- Następny etap: przeanalizować powierzchnie cylindryczne/stożkowe i osie 11 grup (44 wystąpienia) bezpośrednio na oryginalnym B-Rep, a nie tylko na wynikach `stockHint`. Dodać niezależny test geometrii, następnie zmienić detektor **wyłącznie przy potwierdzonych dowodach**. Nie zwiększać tolerancji, nie przypisywać niepotwierdzonych czasów ani przygotówek, nie zmieniać UI, nie scalać do main.


## 8.11.2026, 06:15 CET — powtarzalne B-Rep o tej samej objętości

- HEAD wejściowy PR #7: `1d59edc8f0d228060ea4399836fb36d467c43aa1`; PR otwarty, bez merge.
- Bezpośrednio sprawdzono GitHub Actions dla tego HEAD: publiczny benchmark [42445815768](https://github.com/damianink-png/DS-Estimate/actions/runs/42445815768) **PASS** (job benchmark); Windows [42445815697](https://github.com/damianink-png/DS-Estimate/actions/runs/42445815697) **PASS** (workspace-ui i build-windows). Artefakty: publiczne STEP `13603443837`, Windows evidence `13603644610`. Odczytano log benchmarku, nie tylko status CI.
- Oryginalny Earthpress w logu skompilowanego silnika: 14/14 wybranych wystąpień obrotowo-złącznych przeszło `PUBLIC_FASTENER_GEOMETRY_GUARD_PASS`; 6 SHS ma `UNVERIFIED`, bryły 10–11, 132 i Portal 2–9 przeszły odpowiednie testy osi/rdzeni/zmiennego przekroju.
- Konkretne odkrycie z B-Rep: bryły Earthpress 88–93 mają tę samą objętość ok. **508,9263 mm³**, ale **trzy różne** `verifiedShapeKey`: 88=91 (`shared-tshape-49`), 89=92 (`shared-tshape-50`), 90=93 (`shared-tshape-51`). Nie wolno scalać geometrii na podstawie samej objętości.
- Commit testu `a92cad707b7db542c6028f9ae477b250a3f1fbb7`: ścisła regresja trzech odrębnych kluczy przy identycznej objętości, powtórzenia położenia i zakaz wnioskowania technologii. **Nowy commit nie ma jeszcze potwierdzonego PASS**; sprawdzić nowe Actions przed kolejną zmianą.
- Wynik przed/po wyceny: **bez zmian silnika**, ostatnie potwierdzone 121/251 Earthpress, 6/15 Portal, 0/1 StepGen; nie twierdzić, że nowy test zwiększył pokrycie.
- Następny krok: bezpośredni pomiar osi i typów powierzchni 11 grup elementów obrotowych z oryginalnego STEP, niezależnie od kluczy/objętości; dopiero potem bezpieczny detektor cech. Półfabrykat, piła, frezowanie i czas pozostają nieustalone bez dowodu. Nie zmieniono tolerancji, UI ani main; nie opublikowano EXE.


## 8.11.2026, 07:15 CET — kontrola HEAD i pełnego zbioru UNKNOWN

- HEAD wejściowy PR #7: `fa08ca27300e2912ca0e1921a603e287d13c20e0`; PR otwarty, bez merge.
- Dwa workflow dla **dokładnie tego SHA** zakończone sukcesem: [benchmark 42450077781](https://github.com/damianink-png/DS-Estimate/actions/runs/42450077781) **PASS** i [Windows 42450077761](https://github.com/damianink-png/DS-Estimate/actions/runs/42450077761) **PASS**. Potwierdzono obecność artefaktów: benchmark `13605472433`, Windows installer `13606310151`, UI evidence `13605720219`. Nie opublikowano EXE.
- Po odczycie bieżącego testu oryginalnych STEP dodano do `tests/public_stock_axis_regression.py` bramkę całego zbioru nierozpoznanych brył Earthpress: dokładnie **75 wystąpień UNKNOWN w 37 różnych verifiedShapeKey**, bez utraty identyfikatorów. Jest to test regresji tożsamości B-Rep i zachowania nieustalonych pozycji, nie rozpoznawanie półfabrykatu ani technologii.
- Commit kodu: `82f2e0644ab18edabb23f403b3553a632b8f361e`. **Nowy commit wymaga osobnego CI**; PASS poprzedniego HEAD nie certyfikuje tej zmiany. Nie zmieniono tolerancji, UI ani algorytmu cięcia.
- Przed/po: brak zmiany silnika; ostatnie potwierdzone liczniki czasów Earthpress **121/251**, Portal **6/15**, StepGen **0/1**. Nowe liczby po commicie nie są jeszcze potwierdzone. Nie przedstawiać regresji jako wzrostu skuteczności.
- Następny etap: pobrać i porównać pełne artefakty bieżącego benchmarku, następnie wykonać **bezpośredni pomiar osi cylindrów i stożków na oryginalnym B-Rep** w 11 grupach (44 wystąpienia) i dodać testy zmierzonych kierunków. Sam `verifiedShapeKey` i objętość nie są dowodem obrotowości ani surowca. Nie przypisywać piły/frezowania i czasu bez dowodu.


## 8.11.2026, 08:11 CET — potwierdzenie CI HEAD i analiza bezpośrednich logów B-Rep

- Kontrola PR #7: HEAD `4b66107950dafa1734abdad9748ed122b5f05d51`, otwarty, bez merge. Dwa workflow dokładnie tego SHA: [benchmark 42454055951](https://github.com/damianink-png/DS-Estimate/actions/runs/42454055951) **PASS** (job 128649209319), [Windows 42454055974](https://github.com/damianink-png/DS-Estimate/actions/runs/42454055974) **PASS** (workspace-ui i build-windows). Artefakty: benchmark 13607222881; Windows evidence 13607880551, installer 13607870610 (nie publikować). W logu benchmarku jest przejściowe `conda activate ds-cad` ERROR, lecz dalsze natywne testy OCCT zakończyły się sukcesem; nie oznaczać tego jako FAIL całego runu.
- Odczytano bezpośrednio log joba z oryginalnymi publicznymi STEP: Earthpress 251 brył, statusy `CANDIDATE=85, GEOMETRY_ONLY=84, UNVERIFIED=6, INVALID_HINT=1, UNKNOWN=75`; Portal Frame 15 brył, `GEOMETRY_ONLY=6, UNKNOWN=9`; StepGen 1 bryła, `UNKNOWN=1`. Testy `PUBLIC_STOCK_AXIS_PASS` (10/11), `PUBLIC_ROUNDED_SHS_AREA_PASS` (1–6), `PUBLIC_FASTENER_GEOMETRY_GUARD_PASS` (14 wystąpień), `PUBLIC_UNKNOWN_GEOMETRY_CENSUS_PASS` (75/37), `PUBLIC_VARIABLE_SECTION_PASS` (Portal 2–9) i `PUBLIC_CONICAL_END_PASS` (132) wszystkie PASS.
- Odczyt B-Rep SHS z natywnego silnika: 60×60×3, 2 szt., pole 660.702354 mm²; 50×50×3, 4 szt., pole 540.702354 mm². Wciąż **brak niezależnego odczytu promieni naroży**: nie uznawać pola ostrokątnego za wzorzec ani nie promować `UNVERIFIED` do `GEOMETRY_ONLY`.
- **Przed/po**: w tej iteracji nie zmieniano silnika, zatem pokrycie czasów pozostaje ostatnio potwierdzone Earthpress 121/251, Portal 6/15, StepGen 0/1; brak nowego wzrostu. Nie twierdzić, że 44 łączniki zostały geometrycznie rozpoznane — ich 11 grup wymaga odczytu osi/typów powierzchni z oryginalnych B-Rep, nie tylko `verifiedShapeKey` i objętości.
- Kolejna zmiana kodu: instrumentować w natywnym przebiegu STEP rodzaje i osie powierzchni 11 grup obrotowo-złącznych, z deduplikacją po sprawdzonym kluczu B-Rep; dodać regresję kątów osi, promieni i współosiowości, **bez** domniemania półfabrykatu, piły, frezowania, czasu lub kosztu. Bez rozluźniania tolerancji, bez zmian UX, bez merge i publikacji EXE.


## 8.11.2026, 09:14 CET — pełna bramka HEAD i odczyt natywnych logów

- HEAD wejściowy PR #7: `6b89600c4674bcfc3379072f11dc7ee3043d3e51`; benchmark [42457824587](https://github.com/damianink-png/DS-Estimate/actions/runs/42457824587) **PASS** (job 128660511050, 21 kroków); Windows [42457824527](https://github.com/damianink-png/DS-Estimate/actions/runs/42457824527) **PASS** (workspace-ui i build-windows, w tym instalacja i uruchomienie aplikacji). Artefakt oryginalnych STEP: [13608219767](https://github.com/damianink-png/DS-Estimate/actions/runs/42457824587/artifacts/13608219767).
- Bezpośredni odczyt logu skompilowanego OCCT: Earthpress `251` brył, `UNKNOWN=75`, `UNVERIFIED=6`, `INVALID_HINT=1`, `CANDIDATE=85`, `GEOMETRY_ONLY=84`. Natywne testy osi rur 10–11, pól SHS 1–6, 14 wystąpień łączników, odrębności geometrii 88–93, cenzusu 75/37, zmiennego przekroju Portal 2–9 i stożkowych końców 132: **PASS**.
- Aktualny audyt rzeczywistej ścieżki desktop: Earthpress `121/251` czasów znanych, `130` nieustalonych; Portal `6/15`, `9` nieustalonych; StepGen `0/1`, `1` nieustalone. **Przed/po: 121→121, 6→6, 0→0**. Brak poprawy skuteczności, nie wolno mylić PASS testów zabezpieczających z naprawą rozpoznawania.
- Dodatkowa uwaga: log nadal pokazuje `UNSPECIFIED=56` w przyczynach `stockFailures` Earthpress dla przekrojów wielokątnych; ich geometria nie dowodzi rodzaju zakupionej przygotówki. Pozostawić czas i technologię nieustalone.
- Następny krok wymagający **zmiany silnika**, a nie kolejnego testu statusów: na oryginalnym STEP wyznaczyć `BRepAdaptor_Surface` typy, promienie i wektory osi dla 11 unikatowych grup łączników (44 wystąpienia), następnie dopiero dodać rozpoznanie cech przy zachowaniu `unknown` surowca i czasu. Nie promować profili SHS bez niezależnego pomiaru promieni naroży. Brak zmian tolerancji, UI, main lub wydania EXE.


## 8.11.2026, 10:15 CET — kontrola HEAD, bramka CI i przegląd lokalnej osi w kodzie

- HEAD wejściowy PR #7: `a1a33fd737e5eab3c2a2ef81d0f8114725fe2182`; [benchmark 42462097375](https://github.com/damianink-png/DS-Estimate/actions/runs/42462097375) **PASS** (job 128673395067); [Windows 42462097341](https://github.com/damianink-png/DS-Estimate/actions/runs/42462097341) **PASS** (workspace-ui 128673394896, build-windows 128673558235). Brak FAIL do naprawy w tej bramce.
- Przegląd rzeczywistego `cad_backend/stock_recognition.py`: `_section_edges` przecina bryłę płaszczyzną normalną do globalnej osi `axis`, ale ścieżka lokalna próbuje `gp_Ax3` z kierunków powierzchni/krawędzi i `BRepBuilderAPI_Transform` przed ponowną klasyfikacją. Nie należy zatem twierdzić, że wszystkie przekroje są zawsze globalne; problemem pozostaje dobór i walidacja osi kandydujących dla złożonych brył.
- Ryzyko do zbadania: lokalna pętla `axes[:8]` zatrzymuje się na pierwszym nie-`unknown` wyniku, co może wymagać niezależnej weryfikacji przekroju na całej długości i sprawdzenia, czy kierunek jest osią geometryczną gotowej części, a nie tylko osiową cechą poboczną. Nie zmieniać tego heurystycznie bez pomiarów oryginalnych STEP.
- `stock_patterns.py` rozpoznaje geometrię L/U/T/I i wypukłych wielokątów, ale jawnie nie poświadcza katalogowego półfabrykatu. Nazwowe rozpoznawanie łączników w `parts.mjs` nie jest bazą normaliów ani dowodem B-Rep. W pierwszej kolejności wykonać natywne pomiary osi/promieni/współosiowości 11 grup (44 wystąpienia) Earthpress, dopiero potem weryfikować katalog DIN/ISO.
- **Przed/po (bez zmiany algorytmu)**: Earthpress 121/251 → 121/251; Portal Frame 6/15 → 6/15; StepGen 0/1 → 0/1. Nie wykonano nowego testu katalogu normaliów ani nie zwiększono pokrycia; status **NIEPRZETESTOWANE**. Nie zmieniano tolerancji, UX, main ani EXE.


## 8.11.2026, 11:09 CET — naprawa bramki środowiska CI

- HEAD wejściowy `6c5397f890ec1c3e9bd1a141f330d179e2001449`; [benchmark 42468214829](https://github.com/damianink-png/DS-Estimate/actions/runs/42468214829) **FAIL** i [Windows 42468214824](https://github.com/damianink-png/DS-Estimate/actions/runs/42468214824) **FAIL**. Oba logi wskazują `setup-miniconda@v3` -> `Miniforge3-Windows-x86_64.exe` z `releases/latest/download` -> HTTP 504 po próbach ponowienia. To awaria instalatora środowiska przed uruchomieniem natywnego B-Rep, nie potwierdzona regresja geometrii. `workspace-ui` PASS.
- W obu workflow usunięto `miniforge-version: latest`, aby `setup-miniconda` mógł skorzystać z domyślnego/bundled Miniconda runnera. Commity `f19e4e1dbcbc2cb97e938acbf524162ea31e4f41`, `d107362a0939683cae1ae8d1c2585687b2bd919a`. Zmiana wymaga potwierdzenia CI; nie twierdzić PASS przed wynikami.
- Pokrycie cięcia **przed/po: Earthpress 121/251 -> 121/251; Portal 6/15 -> 6/15; StepGen 0/1 -> 0/1** (bez zmian silnika). Oryginalne STEP nie zostały w tym przebiegu zaimportowane z powodu bramki środowiska. Następny krok: po PASS środowiska bezpośrednio zmierzyć powierzchnie walcowe, osie i promienie 11 grup obrotowo-złącznych, bez domniemania technologii lub ceny.


## 8.11.2026, 12:10 CET — HEAD CI i naprawa pobierania NSIS

- Wejściowy HEAD PR #7: `ec4b82e6ca38f2555fd7d3782c61269549d1563a`. [Benchmark 42470251457](https://github.com/damianink-png/DS-Estimate/actions/runs/42470251457) **PASS**; [Windows 42470251623](https://github.com/damianink-png/DS-Estimate/actions/runs/42470251623) **FAIL** (workspace-ui PASS, build-windows FAIL).
- Odczytano bezpośredni log Windows job 128699311002: natywne testy CAD i niezależny test masy human press **PASS** (51.767769 kg vs 51.765137 kg, błąd względny 0.005085%); błąd w końcowym bundlowaniu NSIS: Tauri 2.10.4 pobiera `https://github.com/tauri-apps/binary-releases/releases/download/nsis-3.13/nsis-3.13.zip`, HTTP **504**. To nie jest błąd Miniforge ani regresja geometrii.
- Poprawiono `.github/workflows/tauri-desktop-windows.yml`: do 3 prób kompilacji/pakowania z opóźnieniem 15/30 s; każda trwała porażka nadal kończy się FAIL. Commit kodu workflow: `4f4464bc30b264c0e68588094b53b527f5ce65df`. **Nowy CI: oczekuje na weryfikację**, nie deklarować PASS.
- Wyniki rozpoznawania przed/po: Earthpress **121/251 → 121/251**, Portal Frame **6/15 → 6/15**, StepGen **0/1 → 0/1**; brak zmian w CAD, tolerancjach i UX. Priorytet następnej iteracji: rzeczywiste osie/powierzchnie B-Rep 11 grup (44 wystąpienia) Earthpress, a nie przypisywanie normaliów ani technologii na podstawie nazw/objętości. Bez merge do main, bez publikacji EXE.
