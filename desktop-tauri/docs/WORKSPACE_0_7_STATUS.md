# DS Estimate 0.7 — półfabrykat i plan operacji

## Zmiany

- Masa gotowej części jest oddzielona od materiału. Rozpoznany profil: pole przekroju × długość. Płyta: prostokątny półfabrykat w lokalnych osiach. Naddatki powiększają materiał; ręczna masa nadal ma pierwszeństwo. Nie obejmuje to rzazu, resztek handlowych ani nestingu. Przy nierozpoznanym przekroju pozostaje opisany szacunek z objętości, a blacha gięta nie ma pełnego rozwinięcia.
- Ubytek w profilu z rozpoznanym półfabrykatem dolicza obróbkę objętościową także bez ręcznego naddatku. Dla rozpoznanych faz doliczane są przygotowanie i usuwanie objętości rowka bez szczeliny montażowej. To edytowalne normy obróbki, nie wybór ostatecznej technologii ani CAM. Otwory wycinane w konturze blachy nie są dodatkowo automatycznie frezowane.
- Montaż/sczepianie oparto na grafie aktywnych połączeń detali, także zakupowych i kooperowanych. Części bez połączenia nie zwiększają czasu montażu spawanego. Każdy podzespół ma przygotowanie; wspólny detal liczony jest raz. Typ części wpływa na dopasowanie. Manipulacja zależy od masy podzespołu, gabarytu i grup normalnych kontaktu; nie jest zoptymalizowaną kolejnością obrotów.
- Gięcie uwzględnia długość linii, grubość i masę. Przygotowanie liczone jest na grupę materiał / gęstość / grubość / promień. Brak promienia przy ręcznym dodaniu gięcia jest jawny. Rzeczywisty dobór narzędzi i kolejność wymagają sprawdzenia.
- Prostowanie jest rezerwą po przekroczeniu edytowalnych progów długości i ilości stopiwa na metr. Nie jest symulacją odkształceń. Szlifowanie pachwin domyślnie wyłączono; spoiny czołowe nadal mają normę szlifowania.
- Nazwane standardowe śruby, podkładki, nakrętki oraz bottle jack i electrical enclosure są proponowane jako zakup. Ręczny wybór realizacji ma pierwszeństwo. Nazwane standardowe elementy są pomijane w automatycznej analizie spoin. Sam zakup lub kooperacja zwykłej blachy nie wyklucza jej z montażu i spawania; zmienia koszty wykonania detalu. Nie rozpoznaje to wszystkich połączeń skręcanych i elementów kupowanych.
- Generyczne nazwy NAUO i referencje etykiet XCAF ustępują opisowej nazwie produktu. Pomiary i rozpoznanie geometrii są współdzielone wyłącznie w grupach, których zgodność została sprawdzona.
- Pythonocc i OCP korzystają ze wspólnego adaptera wywołań przedmiaru. Lokalny test używa teraz rzeczywistego kodu aplikacji, bez modyfikowania kopii algorytmu.

Całkowanie powierzchni B-Rep korzysta z adaptacyjnej tolerancji względnej 10⁻⁷. Usuwa to bardzo długie obliczenia objętości niektórych powierzchni splajnowych modeli dostawców; nie zastępuje pomiaru siatką podglądu.

## Modele zaprojektowane przez ludzi

1. Prasa: Morgan C. Woods, Cameron K. Brooks, Joshua M. Pearce, HardwareX 19 (2024), e00566, https://doi.org/10.1016/j.ohx.2024.e00566. STEP z https://osf.io/nbxzq/download, SHA-256 334286309490685981929f69e71b4bdf99d23bc5f7ccd65fd4db48e1f823cb51. Pełne złożenie ma 220 brył (bryła nie jest równoznaczna z pozycją BOM).
2. Stół Mekanika WKT-S V2.0: https://github.com/mekanika-dev/wkt/tree/8839152eeb607fa1cf63de468c80e3b1398ed8ed. STEP ma 487 brył. Jest to konstrukcja skręcana, przydatna również jako test fałszywych propozycji spoin. BOM w repozytorium dotyczy V1.0, więc nie stanowi dokładnej referencji liczby części V2.0. Dokumentacja i pliki mają licencje opisane w REUSE.toml autorów; nie włączono CAD do kodu programu.

Test `tests/human_assembly_benchmark.py` pobiera plik prasy i sprawdza SHA-256, 220 brył i masę względem niezależnego importu STEPControl oraz całki z pełnej siatki (nie siatki podglądu). Tolerancja 0,1%. W Windows CI uruchamia spakowany silnik EXE; raport jest osobnym artefaktem. Samo dodanie testu nie oznacza jego zaliczenia. Szczegółowe wyniki są w raporcie z danego przebiegu.

## Wyniki przeprowadzonych prób

- Prasa: 220 brył, 36 grup, pełny odczyt nazw bez błędu importu. Masa przy 7850 kg/m³: 51,76776944 kg; niezależna całka 3 663 342 trójkątów: 51,76513722 kg. Różnica 0,005085%. Także spakowany Windows EXE uzyskał ten wynik w przebiegu 42288310933; kolejne poprawki krótkich profili są sprawdzane przez ten sam test.
- Analitycznie: podstawa 412,75 × 336,55 × 6,35 mm daje 6,92436670 kg; dystans 76,2 × 76,2 × 4,7625 mm daje 0,21707739 kg; każda z dwóch prowadnic 12,7 × 76,2 × 4,7625 mm daje 0,03617956 kg. Wszystkie wyniki zgodne z programem. Wymiary po przeliczeniu z dokumentacji autorów; formuła V = L × W × T, m = V × 7850 / 10⁹.
- Analiza styków prasy: 50 propozycji z 83 sprawdzonych par, sześć zgłoszonych przenikań i osiągnięty limit ok. 90 s. Wynik częściowy. Z tego powodu całkowite czasy montażu i spawania pozostają nieustalone — nie są przedstawiane jako kompletna wycena.
- Stół Mekanika: lokalnie odczytano 487 brył, 23 grupy bez błędu importu. Niezależny import STEPControl i całka 23 515 034 trójkątów dały 234,02216346 kg przy tej samej umownej gęstości, wobec 234,01947773 kg programu: różnica 0,001148%. Masa przy jednej, umownie stalowej gęstości 234,01948 kg nie jest masą rzeczywistego stołu aluminiowego z MDF. Analiza trwała ok. 573 s, z czego 486 s przypadło na konserwatywne sprawdzanie podobnej geometrii. Wydajność tej części nadal wymaga dalszej pracy; limit między operacjami nie przerywa pojedynczej długiej operacji jądra CAD.
- Większe modele ujawniły błędne naliczanie naroży nierozpoznanych profili jako gięć. Automatyczne gięcie wymaga teraz rozpoznania blachy giętej. Krótkie zamknięte przekroje calowe są rozpoznawane na podstawie pięciu przekrojów i objętości także bez pozycji katalogowej; cztery wsporniki z rury 25,4 mm nie powinny trafiać do gięcia prasy.
- Kontrolne złożenie sześciu części: materiał 19,734943 kg zamiast wcześniejszych 19,657415 kg masy gotowych detali; montaż dotyczy dwóch połączonych blach zamiast wszystkich sześciu detali (27,366667 min zamiast 40,366667 min przy normach domyślnych). Dodano 20 min przygotowania i 0,14 min obróbki wycięcia SHS oraz 10 min przygotowania i 1,066667 min wykonania faz. Są to normy obróbki, nie zmierzone czasy produkcji.

## Granice

Styki pozostają kandydatami spoin. STEP nie potwierdza zamiaru spawania, wszystkich materiałów, gwintów, wymagań obróbki, jakości powierzchni i WPS. Analiza z limitem czasu daje jawny wynik częściowy; brak pełnej analizy nie jest zerowym czasem spawania, montażu ani fazowania. Nie uzyskano referencyjnych czasów produkcji autorów modeli. Zgodność wzorów nie jest potwierdzeniem norm warsztatowych. Masa przy jednej gęstości jest porównaniem geometrycznym, nie zmierzoną masą całej maszyny z wyposażeniem.
