# DS Estimate 0.5 — automatyczna wycena po analizie

- Etapy i podsumowanie wyceny są ukryte podczas analizy części i styków. Analiza styków uruchamia się przy wczytaniu modelu, także bez odwiedzania zakładki spawania.
- W detale/materiał usunięto listę plików, tabelę operacji kosztowych, indywidualne ceny za kg i osobny panel danych geometrii. Pliki nadal można dodawać z nagłówka i przeglądać w zakładce projektu.
- Nazwa pochodzi ze struktury produktów/wystąpień XCAF STEP. Pod nią jest opis wyrobu/grubość; obok wymiary i koszt materiału na detal oraz suma. Gdy plik nie zawiera nazwy lub nie da się jej przypisać, pozostaje nazwa zastępcza.
- Ceny za kg według gatunku są w ustawieniach. Początkowe ceny to przykłady zakładowe, nie notowania rynkowe; pusty gatunek nadal oznacza założoną stal i 7850 kg/m³. Zmiana ceny lub materiału przelicza koszty bez powtórnej analizy CAD.
- Parametry detalu zawierają obracany podgląd rzeczywistych trójkątów geometrii. Jest generowany na żądanie; nie blokuje analizy wyceny. To prosty podgląd, bez zaznaczania ścian i pomiarów. Bardzo duże siatki są ograniczone do 40000 trójkątów.
- Rozpoznawanie przekrojów sprawdza kilka osi z krawędzi, płaszczyzn i cylindrów. Nadal odrzuca kształty niezgodne objętościowo z przekrojem — nie deklaruje pewnego katalogowego profilu przy istotnych wycięciach.
- Grubość blach jest dodatkowo mierzona z par ścian płaskich/cylindrycznych niezależnie od obrotu. Dla rozpoznanej blachy giętej szacuje się obwód rozwinięcia z pola i objętości powierzchni środkowej (K=0,5), domyślnie jedno przebicie. To przybliżenie kosztu, nie produkcyjne rozwinięcie ani nesting; kontur i przebicia można poprawić w parametrach.
- Sczepianie uwzględnia styki i liczbę sczepów z długości/rozstawu. Obracanie ma osobną operację zależną od liczby i masy części. Normy są edytowalne w ustawieniach.
- Typ spoiny, długość i przekrój przeliczają czas spawania natychmiast. Domyślny przekrój czołowy jest szacunkiem 0,5 t², pachwinowy a². Jawna korekta pola rowka ma pierwszeństwo. Nie jest to rozpoznanie fazy ani obliczenie wytrzymałościowe.
- Prace po spawaniu są domyślnie aktywne: przygotowanie/prostowanie według długości i szlifowanie według długości oraz typu spoiny. Czyszczenie po spawaniu też ma normę. Zakłada się brak dodatkowej obróbki po spawaniu, wiercenia CNC i NDT; wymagania dokumentacji mogą wymagać ich dopisania. CNC z naddatków liczy się automatycznie.
- Usunięto ręczne kalkulatory czasu z ekranów modułów. Pozostały wyniki automatyczne i korekty. Operacje wyłączone w normach są pomijane w wycenie, a nie prezentowane jako brakujące czasy.

## Ograniczenia i sprawdzenie

Nazw, grubości i gięć nie da się odzyskać z każdego eksportu STEP (np. powierzchnie aproksymowane zamiast analitycznych). Bez źródłowego STEP użytkownika nie potwierdzono konkretnych detali ze zdjęć. Spoiny nadal są propozycjami na podstawie styków; wymagają kontroli zamiaru spawania, dostępu i zakresu. Analiza ma limit czasu/par i jawnie pokazuje wynik częściowy.

Regresje obejmują materiał/cenę według gatunku, przeliczanie po zmianie spoiny, sczepy/obracanie, prace po spawaniu, obróconą blachę giętą z kołnierzami, podgląd rzeczywistego profilu z otworem oraz odczyt nazwy z pliku STEP zapisanego przez XCAF. Test interfejsu symuluje mostek natywny; testy Windows osobno uruchamiają spakowany silnik.
