# DS Estimate — przegląd metod CAD feature recognition (2026-11-11)

Status: analiza techniczna; **bez zmiany silnika i bez deklaracji PASS**.

## Źródła
- Analysis Situs: https://www.analysissitus.org/features.html — AAG, krawędzie wklęsłe/wypukłe, otwory, zaokrąglenia.
- Analysis Situs: https://analysissitus.org/ — część modułów produkcyjnych (m.in. pełne CNC, sheet metal) jest komercyjna.
- FreeCAD SheetMetal: https://github.com/shaise/FreeCAD_SheetMetal — stała grubość, cylindryczne zagięcia, unfold, tryb bez niejawnych parametrów technologicznych.

## Kandydat do wdrożenia (bez nowych opcji UI)
1. Utworzyć AAG dla unikalnej geometrii, nie dla każdego wystąpienia; zachować identyfikatory ścian i typy powierzchni.
2. Grupować łańcuchy otworów walcowych, faz i zaokrągleń jako cechy wtórne; nie usuwać ich z bryły źródłowej.
3. Generować hipotezy osi z osi powierzchni analitycznych i głównych kierunków bryły. Przekroje 10/25/50/75/90% porównywać po sprowadzeniu do lokalnych współrzędnych.
4. Wyznaczyć bazowy przekrój wyłącznie z co najmniej trzech zgodnych, niezakłóconych sekcji. Sprawdzać, czy proponowana przygotówka geometrycznie zawiera bryłę gotową, a jej objętość nie jest mniejsza od gotowej części.
5. Dla blach giętych wymagać spójnej grubości i cylindrycznych połączeń ścian; nie utożsamiać każdego promienia z gięciem.
6. Wynik klasyfikacji oddzielić od decyzji technologicznej: rozpoznany przekrój != potwierdzony czas cięcia. Przy konflikcie dowodów pozostawić null i kod przyczyny.
7. Cache według zweryfikowanej sygnatury geometrii; zachować oddzielnie wystąpienia, masy i materiały.

## Bramka akceptacji
- Earthpress: punkt odniesienia 75 nierozpoznanych wystąpień / 37 geometrii; mierzyć liczbę poprawnie rozpoznanych i false positives, nie tylko recall.
- Testy negatywne: płyta z fazą, profil z otworami, walec z rowkiem, nieregularna bryła o podobnym bbox, samodotykający obrys, krótkie RHS/SHS, blacha z promieniem niebędącym gięciem.
- Nie pogarszać masy, grupowania, liczby wystąpień ani bazowych benchmarków.
- Sprawdzić skompilowany Windows CAD, OneEXE i rzeczywisty GUI przed oznaczeniem PASS.
- Porównać czas całkowity, czas na unikalną geometrię, pamięć i liczbę B-Rep calls przed/po.

## Decyzja
Najpierw niewielki, niezależny klasyfikator AAG/feature evidence uruchamiany jako fallback dla nierozpoznanych geometrii; nie podmieniać stabilnej klasyfikacji i nie wprowadzać nowych kontrolek. Integracja produkcyjna dopiero po regresji na oryginalnych STEP.
