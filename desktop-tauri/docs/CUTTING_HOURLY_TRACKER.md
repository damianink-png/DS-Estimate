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
