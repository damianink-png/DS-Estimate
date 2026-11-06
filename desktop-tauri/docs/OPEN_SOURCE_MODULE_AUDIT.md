# Przegląd rozwiązań i decyzje wdrożeniowe — DS Estimate 0.4

Przegląd obejmował kod i zależności, nie tylko opisy projektów. „Publiczny kod”
nie zawsze daje prawo kopiowania. Poniżej odróżniamy dane dołączone, już działające
silniki, samodzielne implementacje oraz rozwiązania wymagające większego runtime.

## Sprawdzone źródła

1. **Steel Section Database (MIT)** — https://github.com/ulmewix/Steel_Section_Database
   commit `524172a3fff6a2c4da03f56a577402aa3a88876a`.
   Odczytano `data/**/*.csv`, metadane TOML, wygenerowane pola przekrojów i kod
   `section_properties`. Dołączono 1792 rekordy i pola przekrojów po konwersji,
   wraz z licencją. Dopasowanie wykorzystuje rodzinę, wymiary i pole, a otwarte
   przekroje także próbki wnętrza obrysu. Kilka zgodnych pozycji pozostaje wyborem.
2. **RoboWeldAR (Apache-2.0)** — https://github.com/ikh-innovation/roboweldar-weld-seam-detection
   commit `8cf0e93a6cc24a1372cdad7234eb4e0f8b563dfa`.
   Przejrzano `seam-detection/pipeline.py`, `algorithms.py`, wymagania i README.
   Pipeline używa chmury punktów, VoteNet/Open3D i CUDA. Nie dołączono go do aplikacji.
   Zamiast przenosić model GPU, napisano detektor styków dokładnego B-Rep w OCCT:
   filtr bbox, odległość, odrzucenie kolizji, przecięcia płaskich ścian i Section.
3. **FreeCAD SheetMetal (LGPL-2.1-or-later)** — https://github.com/shaise/FreeCAD_SheetMetal
   commit `d6a60a9911e612cf7ecb593b869f658baca22cdd`.
   Przejrzano `SheetMetalNewUnfolder.py`, zwłaszcza `BendAllowanceCalculator`.
   Pełny unfolder zależy od FreeCAD. Nie jest dołączony. Działa własne wykrywanie
   par cylindrycznych ścian gięcia i niezależny wzór długości łuku warstwy obojętnej
   `kąt × (promień + K × grubość)`. Nie przedstawiamy tego jako pełnego rozwinięcia.
4. **FreeCAD CAM (LGPL-2.1-or-later)** — https://github.com/FreeCAD/FreeCAD
   plik `src/Mod/CAM/Path/Post/DrillCycleExpander.py`.
   Przejrzano ekspansję G81/G82/G83 i zależności Path/MachineState.
   Wymaga narzędzia, posuwów, poziomów i strategii; sam STEP ich nie wyznacza.
   Pozostawiono istniejące kalkulatory frezowania/wiercenia i dodano szacunek objętości
   usuwanej z naddatków. Brak udawanej integracji CAM.
5. **Deepnest (MIT)** — https://github.com/deepnest-next/deepnest
   plik `main/background.js`: NFP, układanie, scalanie linii i Electron IPC.
   Przejrzany kod potrzebuje przygotowanych wielokątów i natywnych modułów; nie
   stanowi kalkulatora posuwu piły/lasera. Nie dołączono pełnego silnika nesting.
   Własny kalkulator wykorzystuje zmierzone kontury, pole cięcia, przebicia,
   normy maszyny oraz wspólne przezbrojenia partii.
6. **Kwantflow (GPL-3.0)** — https://github.com/muicci/kwantflow
   już wcześniej dołączony kod `src/lib/kwantflow/estimate-calculation.ts` i adapter
   `modular-kwantflow.ts` pozostają silnikiem sumowania kosztów. Przejrzano logikę
   kategorii/kosztów i zachowano pochodzenie oraz istniejący COPYING.
7. **Inne systemy ofertowania** — sprawdzono publiczny wrapper
   `OnkarPKher/cad-quoting-engine/src/quote_with_visualizations.py`; repozytorium
   nie deklaruje licencji, więc kod nie został skopiowany. Sprawdzono też licencję
   `GOAT-Robotics/forge`: prywatna, niekomercyjna; nie skopiowano modułów.
8. **ESAB QWPA i podobne kalkulatory** — znaleziono opis analizy produktywności,
   lecz nie potwierdzono otwartej licencji źródeł ani API do osadzenia w aplikacji.
   Zastosowano własne wzory: masa spoiny / wydajność stapiania / wykorzystanie łuku.
   Nie skopiowano zamkniętych tabel ani nie deklarujemy integracji ESAB.

## Decyzja osobno dla każdego modułu

| Moduł | Rozwiązanie ocenione | Wdrożenie |
|---|---|---|
| Materiał / masa / wymiary | OCCT + dotychczasowy przedmiar | Objętość i powierzchnia B-Rep, własna gęstość/gatunek na wystąpieniu; sześć naddatków |
| Rozpoznawanie wyrobu | MIT Steel Section Database | Biblioteka offline, dopasowanie, naroża zaokrąglone i lokalna orientacja |
| Zakup / kooperacja | Wzorzec pozycji kosztowych Kwantflow | Trasa i cena na detalu; materiał i produkcja zewnętrzna bez podwójnego naliczania |
| Cięcie | Deepnest, istniejące adaptery | Nowy kalkulator laser/plazma/palnik/piła; sortowanie i partie; bez nestingu |
| Gięcie | FreeCAD SheetMetal | Kandydaci z cylindrycznych ścian, ręczna korekta liczby, cykl i przezbrojenie; bez pełnego rozwinięcia |
| CNC | FreeCAD CAM, istniejące wzory skrawania | Kalkulator oraz objętość z naddatków; bez trajektorii CAM |
| Montaż / sczepianie | Brak zweryfikowanego uniwersalnego czasu z samej geometrii | Własne jawne normy: elementy, masa, połączenia, przygotowanie |
| Spawanie | RoboWeldAR, ESAB | Własny OCCT detektor kandydatów; przekrój, długość, stopiwo, grupy i czas z norm |
| Po spawaniu | Brak zweryfikowanego ogólnego automatu procesu | Opcjonalne szlifowanie wg długości spoin; prostowanie i obróbka korygowane ręcznie |
| Powłoki | OCCT SurfaceProperties, wzory powierzchniowe | Opcjonalne oszacowanie brutto m² × warstwy / wydajność + przygotowanie |
| Kontrola / NDT | Geometria OCCT + wymagania z dokumentacji | Normy kontroli sztuk i VT długości spoin; zakres NDT pozostaje ręczny |
| Transport | Kalkulacja odległość × stawka; brak zweryfikowanego kosztu z CAD | Edytowalne km i zł/km, pakowanie i załadunek z norm |
| Technologia | Brak wiarygodnej automatycznej normy z samego STEP | Własny czas przygotowania; jawnie włączany i edytowalny |
| Wyniki | Kwantflow | Wspólne sumowanie znanych kosztów, korekty i eksport statusu / detali |

Normy startowe są przykładami zakładowymi, nie normami wydanymi przez producenta
maszyny ani bazą czasów technologicznych. Nie traktujemy samego oznaczenia typu,
styku lub zatwierdzenia operatora jako dowodu pełnej automatyzacji wyceny.
