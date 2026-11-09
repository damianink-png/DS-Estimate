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


## 8.11.2026, 13:13 CET — pomiar powierzchni oryginalnego B-Rep w ścieżce produkcyjnej

- HEAD wejściowy PR #7: `2247afc0c9f8fbcf8dab07f41c0e54cb7e99cefc`; oba workflow dla dokładnie tego SHA zakończone **PASS**: [benchmark 42474667461](https://github.com/damianink-png/DS-Estimate/actions/runs/42474667461) i [Windows 42474667460](https://github.com/damianink-png/DS-Estimate/actions/runs/42474667460). To potwierdza poprzedni HEAD, **nie** nowy kod.
- Zmieniono produkcyjny `stock_recognition.py`: dla nierozpoznanych brył odczytuje bezpośrednio z **oryginalnych zaimportowanych powierzchni B-Rep** typy walcowe i stożkowe, promienie, kierunki osi i liczbę ścian. Zapisuje tylko diagnostyczne `finishedBrepSurfaceEvidence`; nie zmienia klasyfikacji półfabrykatu, technologii ani czasu. Dodano import `GeomAbs_Cone` do obu backendów OCCT.
- Dodano regresję oryginalnych Earthpress 10 i 11: obecność promieni 20 i 17 mm oraz wektorów osi rzeczywistych powierzchni. Test wymaga skompilowanego silnika i oryginalnego STEP, a nie sztucznej bryły.
- Commity: `edc9787a42e154d454bccb263855c2935241636a`, `4fc9eb221f9056891491e63739fe21985d89f226`, `0a75d25472a29d46f66d47fadce6c005b5d082c7`. **CI nowego HEAD jeszcze niepotwierdzone.**
- Przed/po pokrycie czasów: Earthpress **121/251 → 121/251**, Portal **6/15 → 6/15**, StepGen **0/1 → 0/1**; to pomiar diagnostyczny, nie zwiększenie rozpoznania. Następny etap: odczytać rzeczywiste wartości `finishedBrepSurfaceEvidence` z artefaktów CI, grupować po `verifiedShapeKey`, zmierzyć współosiowość 11 grup/44 wystąpień i dopiero potem zaprojektować bezpieczne rozpoznanie cech. Nie zmieniono tolerancji, UX, main ani nie publikowano EXE.


## 8.11.2026, 14:17 CET — test powierzchni B-Rep elementów obrotowo-złącznych

- HEAD wejściowy PR #7: `9b1b49712bd70906407305bc65569cfc19c4388d`. Dla tego SHA [benchmark 42479251575](https://github.com/damianink-png/DS-Estimate/actions/runs/42479251575) **PASS** i [Windows 42479251679](https://github.com/damianink-png/DS-Estimate/actions/runs/42479251679) **PASS**. W logu oryginalnego STEP: Earthpress 251 brył, 96 grup, 75 UNKNOWN / 37 geometrii; potwierdzono osie i promienie 20/17 mm dla brył 10/11 oraz brak fałszywego certyfikowania cięcia.
- Dodano do `public_stock_axis_regression.py` odczyt i walidację `finishedBrepSurfaceEvidence` dla 14 wystąpień obrotowo-złącznych (88–93, 99, 106, 109, 122, 125, 131, 135, 141). Raport `PUBLIC_FASTENER_ORIGINAL_BREP_SURFACE_CENSUS` podaje rzeczywiste promienie, osie, stożki i klucze zweryfikowanych geometrii z oryginalnego STEP. Test nie zakłada, że każdy detal ma powierzchnie analityczne; nie przypisuje zakupionych normaliów ani obróbki. Commit testu: `c2a676a98ef05831f4180084ab9bbe6909187f5c`.
- Pokrycie przed/po **121/251 → 121/251** Earthpress, **6/15 → 6/15** Portal, **0/1 → 0/1** StepGen. Brak zmian tolerancji, klasyfikacji, UI i wyceny. **CI nowego testu jeszcze niepotwierdzone**; następny etap: odczyt raportu po uruchomieniu workflow i analiza współosiowości, grupowanie po `verifiedShapeKey` bez utożsamiania równej objętości z identyczną geometrią. Nie scalać do main ani nie publikować EXE.


## 8.11.2026, 15:09 CET — pomiar płaskich powierzchni B-Rep dla płyt z fazami

- HEAD wejściowy PR #7: `42d005e501b9ac0c740bdff64289eb063252e26e`. Benchmark [42484272977](https://github.com/damianink-png/DS-Estimate/actions/runs/42484272977) **PASS**, Windows [42484273103](https://github.com/damianink-png/DS-Estimate/actions/runs/42484273103) **PASS**. Nie wykryto FAIL na wejściu.
- Produkcyjny `stock_recognition.py`: dla nierozpoznanych brył odczytuje teraz **normalne płaskich ścian bezpośrednio z oryginalnego STEP B-Rep** obok walców i stożków; raportuje `planes` i `planeFaceCount`. To dane konieczne do przyszłego rozróżnienia dominujących powierzchni płyty od fazowania, nie klasyfikacja materiału wejściowego.
- Dodano test regresyjny `PUBLIC_ORIGINAL_BREP_PLANE_CENSUS_PASS`: kontroluje obecność i jednostkowość normalnych na oryginalnych 75 UNKNOWN Earthpress, bez przypisywania fazowaniu technologii frezowania, cięcia lub kosztu. Commity: `d7b5644425bcd6782fe5d48957e213999d13f218`, `88d768597acfac1e1c5d735ebab24c0c3cf0ce48`, `cf6d0baa685584296fb67aa19a09abdc9152e590`.
- Pokrycie przed/po (bez zmiany klasyfikacji): Earthpress **121/251 → 121/251**, Portal Frame **6/15 → 6/15**, StepGen **0/1 → 0/1**. CI nowych commitów **jeszcze niepotwierdzone**. Kolejny krok: zmierzyć pola i wzajemne orientacje płaszczyzn oraz odróżnić fazy od bazowych powierzchni płyty na rzeczywistych STEP; nie zgadywać półfabrykatu. Bez zmian tolerancji, UX, main i bez publikacji EXE.


## 8.11.2026, 16:15 CET — pola i odsunięcia płaszczyzn oryginalnego B-Rep

- HEAD wejściowy PR #7: `2ff745e1444b65709fb4ae3a8b64637a76db3865`. Benchmark [42488471878](https://github.com/damianink-png/DS-Estimate/actions/runs/42488471878) **PASS**, Windows [42488471863](https://github.com/damianink-png/DS-Estimate/actions/runs/42488471863) **PASS** dla wejściowego SHA.
- Produkcyjny `stock_recognition.py`: obok normalnej każdej płaskiej powierzchni nierozpoznanej bryły oryginalnego STEP zapisuje zmierzone pole `areaMm2` i odsunięcie `signedOffsetMm` w układzie tej płaszczyzny. To umożliwia dalszą analizę par dużych równoległych ścian płyty i odróżnienie mniejszych ścian faz. **Nie stanowi jeszcze rozpoznania fazowanej płyty ani technologii obróbki.** Commit `56657b085e41f662e3ccce4f518ee01fcf64744a`.
- Regresja `public_stock_axis_regression.py` na oryginalnym Earthpress wymaga dodatnich skończonych pól i skończonych odsunięć każdej raportowanej płaszczyzny. Commit `1e56a570b69c5533bb93c6155cb3b37c0a4799d2`.
- Pokrycie czasu cięcia przed/po **121/251 → 121/251** Earthpress, **6/15 → 6/15** Portal, **0/1 → 0/1** StepGen. Nowy HEAD wymaga CI; nie deklarować PASS bez workflow. Nie zmieniono tolerancji, UX, klasyfikacji półfabrykatu, technologii, main ani EXE.


## 8.11.2026 — poprawa płyt z fazami i rozszerzenie bibliotek przekrojów (PR #7)

- Wejściowy HEAD PR #7: `c19279dab8b6082a631998949d85f9aa5469553d`; benchmark istniejącej wersji [42493928819](https://github.com/damianink-png/DS-Estimate/actions/runs/42493928819) PASS; Windows przed zmianą jeszcze w toku przy pierwszej kontroli. Bez zmian `main`.
- `cad_measure.plate_hint` dobiera teraz **parę dominujących równoległych ścian B-Rep**, z udokumentowaną asymetrią ich pól na skutek sfazowania; nadal wymaga osi normalnej zgodnej z rzeczywistą cienką osią lokalnego układu, odległości między płaszczyznami równej grubości, odpowiedniej powierzchni i rzeczywistych obrysów/wires. To nie jest poluzowanie tolerancji globalnej, ponieważ zastąpiono wadliwe porównanie pól odrębnymi warunkami topologii. Wynik nadal `plate-candidate` (bez certyfikacji zakupu/technologii).
- `stock_patterns.py`: rozszerzono **geometric-section library** o ścisłe wzorce `zee` (Z) i `hat` (kapelusz/omega) oraz detektor **prostokątnego przekroju z małymi fazami w narożach**. Wzorce wymagają rzeczywistej topologii i powtarzalnych przekrojów B-Rep; brak fikcyjnego przypisania norm i dostawców. Nominalna, przypięta baza EN ma nadal 1792 wpisy — NIE dopisano wymyślonych wymiarów.
- `stock_recognition.py`: przy pięciu zgodnych przekrojach sfazowanego prostokąta i zgodnej niezależnie zmierzonej objętości zachowuje `kind=unknown` (aby nie uruchamiać nieuzasadnionej wyceny technologii), ale dodaje `finishedSectionEvidence` i kandydata prostokątnego półfabrykatu `rawStockCandidate` (`geometric-blank-candidate`). Duże/wklęsłe/nie-narożne skosy i przekroje o zmiennej geometrii nie są automatycznie „ignorowane”.
- Dodano źródłowe testy obracanych/lustrzanych przekrojów Z/hat, fazowanego naroża i negatywnych przypadków skosów, oraz testy CAD na rzeczywistych B-Rep skonstruowanych metodą wyciągania z fazowaną krawędzią (płyta 100×50×10, faza 5 mm; pręt 40×40 z fazowanym narożem).
- Commity: `7b8ed9e4`, `fe54550a`, `f761f9bb`, `3f6fff87`, `be8ccbb4`, `f95e6a37`, `bedabde6`, `b13354d4`. Weryfikacja kodu: [benchmark 42495816742](https://github.com/damianink-png/DS-Estimate/actions/runs/42495816742) **w toku** i [Windows 42495816752](https://github.com/damianink-png/DS-Estimate/actions/runs/42495816752) **w toku** (moduł `workspace-ui` PASS). Nie przypisywać PASS całości przed zakończeniem.
- Ostatnia zweryfikowana baza przed zmianą: Earthpress **121/251**, Portal Frame **6/15**, StepGen **0/1** (liczby pokrycia cięcia, nie importu B-Rep). Wynik po zmianie wymaga testu oryginalnych publicznych STEP i artefaktów CI; NIE deklarować wzrostu bez dowodów. Nie zmieniono stawek, harmonogramów technologii, interfejsu, `main` ani nie opublikowano EXE.


### Kontrola niezależnych artefaktów i poprawa regresji płyt 12/13

- Pełny [benchmark 42496043012](https://github.com/damianink-png/DS-Estimate/actions/runs/42496043012) dla `7bc43db32`: **PASS** (oryginalne STEP, natywne testy B-Rep, masy, grupowanie, częściowe czasy cięcia). Testy rzeczywistej fazowanej płyty i pręta w `manufacturing_geometry_test.py`: **PASS**. Windows tego samego SHA początkowo w toku.
- **Nie pomylono PASS benchmarku ze wzrostem pokrycia.** Porównano bezpośrednio archiwa artefaktów `13622408820` (przed zmianą, run 42493928819) i `13623965746` (po zmianie, run 42496043012). Earthpress: kandydaci płyt **85→83**, `INVALID_HINT` **1→3**, reszta czasu cięcia nadal **121/251**. Pogorszenie dotyczy dokładnie *oryginalnych brył 12 i 13*: dawniej geometrycznie wykryta płyta, później `kind=plate-candidate` dołożony przez moduł arkusza, ale bez pełnych wymiarów / `confidence`, ponieważ silnik przekroju zinterpretował zmniejszoną objętość gotowego detalu jako niepełny płaskownik.
- Z oryginalnych STEP odzyskano rzeczywisty lokalny układ: szerokość około **60 mm**, grubość **10 mm**, długość **565.0857866 mm**, duże równoległe płaskie powierzchnie o polu **30962.677013 mm²**. Dawny światowy/skośny bbox `420.67×420.67×10` nie był prawidłowym wymiarem do zakupu. Dalsza obróbka i zakup nadal nieustalone.
- Poprawiono `_recognize_axis_stock`: jeśli pięć przekrojów płaskich jest zgodnych, realnie zmierzona objętość jest **mniejsza** od pełnego pryzmatu, a niezależne dominujące powierzchnie B-Rep potwierdzają cienką płytę i jej grubość, to wynik jest **`plate-candidate` z kompletnymi wymiarami i `confidence=candidate`**, z zachowaniem `rawStockCandidate`. Dodatkowa geometria/większa objętość w Portal Frame nadal NIE przechodzi tego warunku. Nie dodano technologii ani nie zmieniono tolerancji.
- Dodano test jednostkowy długiej płyty z wybraniem materiału (również bez dowodów negatywnych) i regresję oryginalnego STEP Earthpress 12/13 z kontrolą statusu audytu i wymiarów.
- Commity poprawy: `e0ac02f7`, `5103fe92`, `a8bcb35b`. **Wynik finalnego HEAD — oczekuje na CI.** Cel: odzyskać Earthpress CANDIDATE **85**, INVALID_HINT **1** bez zmiany 121/251, 6/15, 0/1 i bez zmiany reszty zgodnych brył.


## 8.11.2026 — współosiowość rzeczywistych powierzchni B-Rep (następna iteracja)

- HEAD wejściowy PR #7: `cba8090ca526ad4a14ec25335e6e7b331d18d543`, benchmark [42497098727](https://github.com/damianink-png/DS-Estimate/actions/runs/42497098727) **PASS** i Windows [42497098774](https://github.com/damianink-png/DS-Estimate/actions/runs/42497098774) **PASS**. W oryginalnym Earthpress: 85 kandydatów płyt, 84 `GEOMETRY_ONLY`, 75 `UNKNOWN` (37 zweryfikowanych grup), 6 `UNVERIFIED`, 1 `INVALID_HINT`; regresja płyt 12/13 naprawiona. Pokrycie czasu cięcia Earthpress **121/251**, Portal Frame **6/15**, StepGen **0/1**.
- Główny problem wśród 75 `UNKNOWN`: zapisywano promienie i kierunki osi walców i stożków, ale **bez ich punktów położenia**. Równoległe, przesunięte otwory można było pomylić ze współosiowymi. Dodano `cad_backend/rotational_features.py`, który łączy oryginalne powierzchnie walcowe i stożkowe w grupy dopiero po weryfikacji **kierunku i rzeczywistej linii osi w 3-D**, tolerancja przesunięcia **0.02 mm** i iloczynu osi **0.99999999**; nie zmieniono tolerancji rozpoznawania przekrojów ani globalnych tolerancji B-Rep.
- `stock_recognition.py` zapisuje `axisPointMm` z `Cylinder.Axis().Location()` i `Cone.Axis().Location()` oraz diagnostyczne `coaxialSurfaceGroups` dla nierozpoznanych detali. Wynik geometrii pozostaje `unknown`, nie przypisuje półfabrykatu, normy, technologii ani cięcia.
- Dodano ścisły test źródłowy: równoległe osie odsunięte o 1 mm muszą pozostać rozdzielone; osie o odwróconych wektorach i punktach przesuniętych wzdłuż osi pozostają współosiowe. Dodano regresję **oryginalnego STEP** Earthpress 10/11 (Ø40×3, oś skośna) i detali 88–93 (trzy powierzchnie walcowe Ø6 / Ø4.4 i dwa stożki 45°, współosiowość rzeczywista, nadal `UNKNOWN` stock).
- Commity implementacji/testów: `f26f62a1`, `48af62ba`, `fca35275`, `36460017`. **Nowy CI: oczekuje na pełny PASS/FAIL**, nie deklarować przed wynikami. Kontrola wyników ma wykazać stabilność 121/251, 6/15 i 0/1 oraz niezmienione 75 nieustalonych Earthpress. Następny etap: analiza rzeczywistych zmierzonych grup dla 11 geometrii/44 wystąpień obrotowo-złącznych, bez automatycznego utożsamiania z normalium.


## 8.11.2026, 18:13 CET — zabezpieczenie przed łańcuchowym łączeniem osi

- HEAD wejściowy PR #7: `bfbbe47db3928d8ab2b4ca4771da0e6bbc5ae932`. Benchmark [42501875158](https://github.com/damianink-png/DS-Estimate/actions/runs/42501875158) **PASS**, Windows [42501875065](https://github.com/damianink-png/DS-Estimate/actions/runs/42501875065) **PASS** (kontrola przed zmianą). Artefakt benchmarku: `DS-Estimate-REAL-PUBLIC-FRAMES-STEP-PDF-BOM` (13626655095). Earthpress: 251 brył, 75 UNKNOWN / 37 różnych zweryfikowanych geometrii; 85 kandydatów płyt, 84 GEOMETRY_ONLY, 6 UNVERIFIED, 1 INVALID_HINT. Pokrycie czasów cięcia: **121/251**, Portal **6/15**, StepGen **0/1**.
- W `rotational_features.coaxial_face_groups` znaleziono ryzyko **nietranzytywnego dopasowania osi**: porównanie wyłącznie do pierwszej osi grupy pozwalało łączyć kilka osi odsuniętych stopniowo w łańcuch, mimo że skrajne osie przekraczały dopuszczalną odległość. Teraz każda nowa powierzchnia musi być zgodna z **każdą** osią już przyjętą do grupy. Zachowano istniejące progi 0,02 mm i 0,99999999, bez luzowania tolerancji.
- Dodano test regresyjny: trzy równoległe osie przesunięte o 0 / 0,015 / 0,030 mm muszą utworzyć **2 grupy**, a odwrócony wektor i punkt przesunięty wzdłuż tej samej osi muszą utworzyć **1 grupę**. Commity: `051596a4ae87ee3349270ee229594660d2ef2273`, `593d04fabbd85868d4e893d3bc7db9f28c5c36b3`.
- Po zmianie **nie ma jeszcze potwierdzonego CI ani nowych liczb pokrycia**; nie deklarować PASS lub poprawy klasyfikacji. Zmiana dotyczy wyłącznie dowodu współosiowości powierzchni oryginalnego B-Rep, nie technologii, półfabrykatu, kosztu ani UX. Kolejny krok: odczytać nowy benchmark i test Windows, zbadać oryginalne grupy osi Earthpress oraz dopiero potem rozważyć identyfikację normaliów bez zgadywania.


## 8.11.2026 — semantyczne nazwy oryginalnych części STEP jako dodatkowy, NIE rozstrzygający dowód

- Kontrola HEAD wejściowego PR #7: `3e61ee6dae274d510460133c7812c3679f16ac63`. Publiczny [benchmark 42517497359](https://github.com/damianink-png/DS-Estimate/actions/runs/42517497359) **PASS**; [Windows 42517497266](https://github.com/damianink-png/DS-Estimate/actions/runs/42517497266) **PASS**. Bez merge do `main`.
- Obejrzano **faktyczne `ds_estimate_inventory.json` oraz `assemblyPath` z archiwum oryginalnych STEP (artefakt 13632411265)**: Earthpress **251/251 nazw `COMPOUND`**, StepGen **1/1 `COMPOUND`**, Portal Frame **15/15 nazw `Open CASCADE STEP translator 7.8 ...`**. Wszystkie mają pozorne `nameSource=XCAF occurrence/product`, ale semantycznie są **nieinformacyjne**. Nie wolno ich traktować jako nazw części. Odrębnego BOM nie powiązano z bryłami po ich kolejności, podobnej objętości ani nazwie złożenia.
- Dodano `part_name_evidence.py`: parser oryginalnej nazwy *wystąpienia/produktu XCAF*, rozpoznający polskie, angielskie i niemieckie nazwy normaliów (śruby, nakrętki, podkładki, kołki, łożyska, seger, smarowniczki) i półfabrykatów (profil, płyta/blacha, rura, pręt, konstrukcja spawana), numery ISO/DIN, rozmiary metryczne, geometrię nominalną. Filtruje `COMPOUND`, techniczne nazwy eksportera, numery wystąpień oraz nazwy cech, np. „otwór pod śrubę” / „Bohrung für Schraube”. Sprzeczny opis normy i typu jest raportowany jako konflikt, a nie arbitralnie rozstrzygany. Bez normy/gwintu/średnicy nie tworzy pozornie dokładnego wymiaru katalogowego.
- Nazwa to osobny `nameEvidence` ze statusem `name-only-unverified`. Jest porównywana z `normaliaHint` po niezależnym rozpoznaniu **ORYGINALNEGO B-Rep**, z `nameCorroboration` (corroborated / family-compatible / conflict). Nie zmienia `stockHint`, `cuttingHint`, masy, grupowania, wyliczonych czasów, stawek ani geometrii.
- Każde **wystąpienie** dostaje własne `nameEvidence` **po** zapisaniu geometrii do wspólnego cache. Nawet identyczne bryły o różnych nazwach zachowują osobne informacje i konflikty. Usunięto w Pythonie skrót, który dla nazwy zawierającej DIN/ISO/bolt omijał całkowicie analizę B-Rep, tworząc `purchased-component`. W dotychczasowym modelu aplikacji **pozostaje wcześniejsza sugestia realizacji jako zakup** dla jawnych nazw normaliów, którą użytkownik może zmienić; sama sugestia nie potwierdza ceny ani zgodności katalogowej.
- UI nadal „wrzuć STEP → wyniki”: wskazówka nazwy i niezgodność z geometrią wyświetlane są **w istniejącym opisie elementu** bez formularzy, pól i zakładek. Potwierdzona geometria ma pierwszeństwo nad nazwą.
- Testy: `test_part_name_evidence.py` (PL/EN/DE, nominalne ISO/DIN, negative cases, placeholdery, nazwy otworów, niezgodność z B-Rep); `manufacturing_geometry_test.py` (ten sam zweryfikowany B-Rep trzech wystąpień o rozbieżnych nazwach i oddzielnym `nameCorroboration`); `coverage-and-products.test.mjs` (istniejący routing i jawna nadpisana decyzja użytkownika). `public_stock_axis_regression.py` wymaga **0 fałszywych odczytów nazwy** na trzech oryginalnych modelach (267 brył), zachowania niezależnych 48 kandydatów normaliów na geometrii Earthpress oraz dotychczasowego częściowego czasu cięcia **121/251 + 6/15 + 0/1**.
- Dotychczasowe poprawki tej iteracji zawierają commity `d403311b`, `72425ebd`, `837f3e78` (ostatecznie przywrócono wcześniejszy routing `2c2ac1b`), `c683a55b`, `af1cc979`, `a76c7eeb`, `a3150b3e`, `e687282e`, `36a88be5`, `8ce88160`, `77543145`, `925ac2dd`, `cf9a1fa5`. W pierwszej serii testów znaleziono i poprawiono brakujący niemiecki negatywny przypadek „Bohrung für Schraube M12”; wcześniejsza próba usunięcia propozycji zakupowych w JS powodowała FAIL względem obowiązującego zachowania — przywrócono ją bez zmiany zasilania B-Rep.
- **Końcowy CI nowego HEAD:** oczekuje na kontrolę i porównanie artefaktów; nie podawać PASS ani większego rozpoznania na Earthpress bez osobnych dowodów. Nie publikować EXE przed końcowymi testami.



## 8.11.2026, 23:00 CET — fizyczny STEP XCAF, rzeczywisty import produkcyjny

- HEAD wejściowy `d11547d65bd3519fe19e00a09333a5b6f368d44f`. GitHub Actions: publiczny benchmark [42523880543](https://github.com/damianink-png/DS-Estimate/actions/runs/42523880543) **PASS**, Windows [42523880512](https://github.com/damianink-png/DS-Estimate/actions/runs/42523880512) **PASS**. Krok 18 benchmarku `Round-trip real STEP XCAF with meaningful part names through compiled engine` przeszedł; artefakt `13634353430` zawiera dowody.
- `tests/named_step_roundtrip.py` rzeczywiście zapisuje fizyczny plik `named_real_xcaf_assembly.step` przez STEPCAFControl_Writer z hierarchią XCAF, ponownie otwiera go przez `read_occurrences`, a następnie uruchamia skompilowany silnik na pliku. Bazowo 8 wystąpień, w tym ta sama geometria kołka o dwóch różnych nazwach, zgodność i konflikt normalium oraz nazwy pozorne.
- Dodano do fizycznego STEP dwa negatywne przypadki nazw otworów w językach niemieckim (`Bohrung für Schraube M12`) i polskim (`Otwór pod śrubę M8`), bez zmiany geometrii, technologii i tolerancji. Commit `b197c9a64350075b1bbb3860b1e79b72483177e0`; oczekiwane 10 wystąpień, **0 fałszywych nazw normaliów z obu nowych przypadków**. CI tego commitu musi jeszcze potwierdzić wynik, nie przypisywać mu PASS z poprzedniego HEAD.
- Zachowane bazowe wartości publicznych projektów: Earthpress normalia 48, czas cięcia 121/251; Portal Frame 6/15; StepGen 0/1. Ponieważ zmieniono wyłącznie test, nie deklaruje się poprawy pokrycia ani nowego pomiaru po zmianie. Brak zmian UX, `main`, stawek i EXE.


## 9.11.2026, 00:00 CET — kontrola CI i regresja nazwy złożenia XCAF

- Poprzedni commit rejestru `5b4285889b34543bbdb6f45895e9daf0a448753c`: benchmark [42527632140](https://github.com/damianink-png/DS-Estimate/actions/runs/42527632140) **PASS**, Windows [42527632033](https://github.com/damianink-png/DS-Estimate/actions/runs/42527632033) **PASS**. Oba runy poprzedniego commitu testowego `b197c9a6` zostały **CANCELLED** (zastąpione kolejnym commitem), nie traktować ich jako FAIL kodu.
- Benchmark opublikował artefakt `13636541303`; Windows opublikował dowody `13637440989`, `13636921489`, `13635099582`. Sam status PASS nie stanowi jeszcze odczytu liczników z JSON artefaktu.
- Nowy test rzeczywistego pliku XCAF: nadrzędne złożenie ma celowo mylącą nazwę `Bolt ISO 4017 M20 assembly`, podczas gdy 10 wystąpień zachowuje własne nazwy produktów PL/EN/DE. Po zapisaniu STEP i ponownym imporcie przez produkcyjny silnik nazwa nadrzędnego złożenia nie może pojawić się jako osobny detal ani jako `nameEvidence` detalu. Commit `468034dd51f629652a2f11410f1c757719a00315`.
- Nowa bramka CI: **oczekuje na uruchomienie/ukończenie**; brak potwierdzonego PASS nowego commitu. Poprzedni test 10 wystąpień jest potwierdzony przez dwa zakończone runy, ale nowy negatywny test wymaga osobnej walidacji.
- Referencja bez nowego niezależnego odczytu raportu: Earthpress 48 kandydatów normaliów; czasy cięcia 121/251, Portal 6/15, StepGen 0/1. **Po:** niezweryfikowane na nowym HEAD; nie twierdzić poprawy. Nie zmieniono tolerancji, wyceny, UI ani `main`.


## 9.11.2026, 01:00 CET — kontrola rzeczywistego XCAF i regresja fałszywych normaliów

- HEAD wejściowy z poprzedniej iteracji: `1654ad3bbe70e61c8d7ced768c100067f688b582`. GitHub Actions dla tego SHA: publiczny benchmark [42533150143](https://github.com/damianink-png/DS-Estimate/actions/runs/42533150143) **PASS**, Windows [42533150179](https://github.com/damianink-png/DS-Estimate/actions/runs/42533150179) **PASS**. Log benchmarku zawiera `NAMED_XCAF_STEP_ROUNDTRIP_PASS`: **10/10** nazw z fizycznego STEP, **4** normalia według B-Rep, **1** konflikt nazwy z geometrią, **0** fałszywych normaliów w trzech nazwach otworów; nazwa nadrzędnego złożenia nie została użyta jako nazwa detalu. Artefakt benchmarku: `13638701413`.
- Ten sam log potwierdza `PUBLIC_GENERIC_XCAF_NAMES_IGNORED_PASS`: **267** oryginalnych brył publicznych STEP (251+15+1), **0** klasyfikacji wyłącznie po nazwie eksportera. Oryginalne B-Rep: Earthpress **85 CANDIDATE / 84 GEOMETRY_ONLY / 75 UNKNOWN / 6 UNVERIFIED / 1 INVALID_HINT**; Portal Frame 2–9 nadal nieuznane za stały profil, Earthpress 132 pozostaje z nieustalonym surowcem.
- Potwierdzone czasy cięcia desktop: Earthpress **121/251**, Portal Frame **6/15**, StepGen **0/1**. Referencja normaliów Earthpress **48** pozostaje wymagana przez test publiczny; nie twierdzić o wzroście. Rozdzielać historyczne 89/251 z QuickEstimate od desktop 121/251.
- Dodano do testu fizycznego XCAF niezależne od samego parsera nazw asercje **dokładnie 4** normaliów geometrycznych, **dokładnie 1** konfliktu i **0** normaliów z nazw otworów/placeholderów, oraz brak potwierdzonej metody produkcji wynikającej z nazwy. Commit: `51b342f40df2c3eaf1b63120bb7c46a56d2c3726`. **Nowy HEAD: CI niepotwierdzone** — nie ogłaszać PASS przed zakończeniem workflow.
- Bez zmiany tolerancji, automatycznego czasu, interfejsu, `main` i bez publikacji EXE. Kolejna iteracja: pobrać i zweryfikować wynik nowego HEAD; rozszerzyć fizyczny STEP o niezależną referencyjną BOM i sprzeczne rozmiary, nie mylić semantycznego opisu z potwierdzeniem technologii.


## 9.11.2026, 02:00 CET — niezależna BOM i fizyczny STEP XCAF

- HEAD wejściowy PR #7: `f8efa68ce1a920d6604d6295027b4fac332a88bf` (PR otwarty, bez merge). Benchmark [42537631946](https://github.com/damianink-png/DS-Estimate/actions/runs/42537631946) **PASS**, Windows [42537631878](https://github.com/damianink-png/DS-Estimate/actions/runs/42537631878) **PASS**; oba przypisane dokładnie do wejściowego SHA. Benchmark wykonał fizyczny XCAF roundtrip i publiczne STEP; artefakt `13639783641`, Windows dowody `13641515487`.
- Dodano **niezależny, wersjonowany BOM JSON** `tests/fixtures/named_xcaf_reference_bom.json` (10 wystąpień), z nazwami PL/EN/DE, rodziną geometrii, oczekiwaną rodziną normalium oraz statusem zgodności nazwy i B-Rep. Commit `91dbdf233ce5626b60cde0ab22c79b65dfc749e5`.
- Test `named_step_roundtrip.py` czyta ten BOM z osobnego fizycznego pliku i po rzeczywistym zapisie STEP XCAF oraz imporcie przez skompilowany silnik porównuje każdą pozycję z niezależną referencją, zamiast tylko z tablicą generatora. Commit `072125dfad17a2b27c20d7428a48f6915c084a95`. Oczekiwane 10/10 nazw, 4 normalia B-Rep, 1 konflikt, 0 fałszywych normaliów z nazw otworów/placeholderów, 0 rozstrzygniętych technologii z samej nazwy. Test nie przypisuje ceny zakupu ani czasu obróbki.
- **Nowy HEAD wymaga osobnego CI:** brak deklaracji PASS nowej asercji przed ukończeniem GitHub Actions. Algorytm produkcyjny, tolerancje i UX niezmienione. Referencje przed: Earthpress 48 normaliów i 121/251 czasów cięcia, Portal Frame 6/15, StepGen 0/1. Po: do weryfikacji w nowym artefakcie; nie deklarować poprawy pokrycia z testów.
- Następny krok: odczytać log nowego XCAF testu i audyt publicznych STEP; rozszerzyć fizyczny przypadek o sprzeczne rozmiary przy zachowaniu nieustalonej technologii.


## 9.11.2026, 03:00 CET — fizyczny XCAF, fałszywy kod ISO przy otworze

- HEAD wejściowy PR #7 `806dc2f2f103a6274d108c816806995e4692ce46`; benchmark [42543017005](https://github.com/damianink-png/DS-Estimate/actions/runs/42543017005) **PASS**, Windows [42543017022](https://github.com/damianink-png/DS-Estimate/actions/runs/42543017022) **PASS**, oba na tym SHA. Log skompilowanego silnika: `NAMED_XCAF_STEP_ROUNDTRIP_PASS` 10/10 nazw, 4 normalia geometryczne, 1 konflikt, 0 błędnych normaliów w nazwach otworów. `PUBLIC_GENERIC_XCAF_NAMES_IGNORED_PASS` 267/267, 0 nazw eksportera uznanych za normalia. Artefakt benchmarku `13642563536` i Windows `13642579360` (nie publikować EXE).
- Nowa regresja w **fizycznym** pliku STEP XCAF: `ISO 4017 M10 mounting hole` — nazwa zawiera poprawny numer normy śruby, ale opisuje otwór, nie śrubę. Dodano jedenastą pozycję i niezależny wpis BOM; wymagane **11/11** nazw, nadal **4** normalia B-Rep, **1** konflikt, **0** fałszywych normaliów z czterech nazw otworów, brak technologii wynikającej z nazwy. Commity `9405d1152f70c911f4f90ebca9ead17c563ea576` i `f00e3076e0982c2facacd9fa7bcf4a5a04cf572c`.
- W produkcyjnym parserze negatywne słowo `hole` jest sprawdzane przed `ISO 4017`, więc nowy test ma podstawę w istniejącej logice, ale **nowy HEAD musi przejść własne CI**. Nie deklarować PASS przed zakończeniem. Nie zmieniano algorytmu geometrii, tolerancji, UI, `main` ani wyceny.
- Ostatnie potwierdzone referencje regresji: Earthpress 48 normaliów, czasy cięcia 121/251; Portal Frame 6/15; StepGen 0/1. Po nowym commicie: do potwierdzenia w logach; brak deklaracji wzrostu.
