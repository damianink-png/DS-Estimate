# DS Estimate 0.3 — jeden interfejs i stan modułów

Źródło porównawcze: DS Compare 0.6.4, `damianink-png/test`, gałąź
`build/dscompare-0.6.4-20261105`, commit `1cae4bc`.

Dwa interfejsy wynikały z App.svelte: domyślny ModuleEstimate oraz przejście
„Narzędzia” do QuickEstimate i wcześniejszych ekranów. App.svelte otwiera teraz
wyłącznie jeden workspace. Nie zmieniamy modelu danych przez przechodzenie między
osobnymi aplikacjami. Starszy komponent QuickEstimate jest zachowany w źródłach,
ale nie jest importowany ani dostępny z UI.

## Gotowe zmiany interfejsu

- Układ i kolory w stylu DS Compare; jasny i ciemny motyw.
- Natywny wybór wielu plików oraz folderu; przeciąganie do okna.
- Dodawanie plików do istniejącej listy, deduplikacja ścieżek Windows.
- Jeden wybrany STEP jest zakresem wyceny. Inne STEP nie są doliczane drugi raz.
- Analiza OCCT raz na niezmieniony model; kolejne moduły korzystają z JSON.
- Własny gatunek, gęstość, cena i naddatki długości dla grup geometrii.
- Bez danych: pusty gatunek, 7850 kg/m³. Grupowanie obejmuje wszystkie wystąpienia.
- Wartość automatyczna i przyjęta osobno, zachowanie korekt, przywracanie automatu.
- Natywny eksport stanu 12 modułów do JSON i CSV.
- Okno dostosowane do obszaru roboczego monitora. CAD uruchamiany bez konsoli.

## Stan funkcjonalny

| Moduł | Działa | Ograniczenie |
|---|---|---|
| Pliki / STEP | Natywny wybór, folder, drop, cache, OCCT B-Rep, grupy i wystąpienia | Nie sumuje wielu modeli naraz; wybór zakresu jest jawny |
| Materiał | Objętość, masa z gęstości, popularne materiały, ceny, naddatki długości, znana masa półfabrykatu | Przypisanie do grup geometrii; brak pełnego drzewa nazw z XCAF i odczytu gatunku STEP |
| Rozpoznawanie wyrobów | Istniejące hipotezy przekrojów z analizy B-Rep, widoczne pewność i wymiary | Kandydat wymaga weryfikacji; brak kompletnego katalogu normowych profili |
| Zakupy / kooperacja | Ręczne kwoty i dodatkowe pozycje | Brak importu ofert dostawców |
| Cięcie | Mierzone kontury płaskich ścian, propozycja maszyny, wspólne przezbrojenie partii, korekta | Brak pełnej automatyzacji piły i nestingu; parametry maszyn przykładowe |
| Gięcie | Kalkulator liczby gięć, cyklu i przezbrojenia; edycja czasu | Brak automatycznego rozwinięcia i liczby gięć |
| CNC | Kalkulator usuwanej objętości i przezbrojenia, ręczne wiercenie | Brak CAM, automatycznego przypisania narzędzi i trajektorii |
| Montaż / sczepianie | Kalkulator liczby brył i połączeń, normy operatora | Liczba złączy i normy wymagają danych operatora |
| Spawanie | Kalkulator pachwin a², masa stopiwa, wydajność, wykorzystanie łuku, przygotowanie | Brak automatycznych styków, faz i integracji ESAB |
| Po spawaniu | Ręczne czasy prostowania, szlifowania i obróbki | Brak automatycznego zakresu |
| Powłoki | Ręczne czasy i operacje | Brak automatycznej powierzchni do malowania / cynkowania |
| Kontrola / NDT | Ręczne czasy i stawki | Brak automatycznej interpretacji wymagań badań |
| Transport | Ręczne czasy i stawki | Brak automatycznej wyceny trasy |
| Technologia | Ręczne czasy i stawki | Brak automatycznego projektowania przyrządów |
| Dokumentacja | PDF: tekst, oznaczenia i uwagi; pozostałe formaty na liście | OCR, DWG, DXF i Excel nie są analizowane automatycznie |
| Wyniki | Koszty przez adapter Kwantflow, czas, statusy, JSON/CSV | Niepełne pozycje pozostają oznaczone; brakujący czas nie jest zerem |

## Weryfikacja

Testy Node obejmują istniejące obliczenia oraz nowy przepływ plików, materiały,
naddatki, puste gatunki i eksport. W istniejącym teście przepełnienia kosztu cięcia
uzupełniono brakujący materiał S355: bez niego żaden dostępny profil maszyny nie
miał stawki, więc test nie wykonywał operacji mnożenia, którą miał weryfikować.

Test Playwright sprawdza interfejs z atrapą natywnych komend; NIE zastępuje testu
Windows/WebView2 ani prawdziwej analizy STEP. Windows CI osobno buduje rzeczywisty
silnik OCCT, uruchamia testy na STEP i kompiluje instalator. Artefakt jest gotowy
dopiero po pomyślnym zakończeniu tego workflow.
