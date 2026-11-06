# DS Estimate 0.7 — półfabrykat i plan operacji

## Zmiany

- Masa gotowej części jest oddzielona od materiału. Rozpoznany profil: pole przekroju × długość. Płyta: prostokątny półfabrykat w lokalnych osiach. Naddatki powiększają materiał; ręczna masa nadal ma pierwszeństwo. Nie obejmuje to rzazu, resztek handlowych ani nestingu. Przy nierozpoznanym przekroju pozostaje opisany szacunek z objętości, a blacha gięta nie ma pełnego rozwinięcia.
- Ubytek w profilu z rozpoznanym półfabrykatem dolicza obróbkę objętościową także bez ręcznego naddatku. Dla rozpoznanych faz doliczane są przygotowanie i usuwanie objętości rowka bez szczeliny montażowej. To edytowalne normy obróbki, nie wybór ostatecznej technologii ani CAM. Otwory wycinane w konturze blachy nie są dodatkowo automatycznie frezowane.
- Montaż/sczepianie oparto na grafie aktywnych połączeń części produkowanych. Części bez połączenia nie zwiększają czasu montażu spawanego. Każdy podzespół ma przygotowanie; wspólny detal liczony jest raz. Typ części wpływa na dopasowanie. Manipulacja zależy od masy podzespołu, gabarytu i grup normalnych kontaktu; nie jest zoptymalizowaną kolejnością obrotów.
- Gięcie uwzględnia długość linii, grubość i masę. Przygotowanie liczone jest na grupę materiał / gęstość / grubość / promień. Brak promienia przy ręcznym dodaniu gięcia jest jawny. Rzeczywisty dobór narzędzi i kolejność wymagają sprawdzenia.
- Prostowanie jest rezerwą po przekroczeniu edytowalnych progów długości i ilości stopiwa na metr. Nie jest symulacją odkształceń. Szlifowanie pachwin domyślnie wyłączono; spoiny czołowe nadal mają normę szlifowania.
- Nazwane standardowe śruby, podkładki, nakrętki oraz bottle jack są proponowane jako zakup. Ręczny wybór realizacji ma pierwszeństwo. Pomijane są w automatycznej analizie spoin. Nie rozpoznaje to wszystkich połączeń skręcanych i elementów kupowanych.
- Generyczne nazwy NAUO i referencje etykiet XCAF ustępują opisowej nazwie produktu. Pomiary i rozpoznanie geometrii są współdzielone wyłącznie w grupach, których zgodność została sprawdzona.
- Pythonocc i OCP korzystają ze wspólnego adaptera wywołań przedmiaru. Lokalny test używa teraz rzeczywistego kodu aplikacji, bez modyfikowania kopii algorytmu.

## Modele zaprojektowane przez ludzi

1. Prasa: Morgan C. Woods, Cameron K. Brooks, Joshua M. Pearce, HardwareX 19 (2024), e00566, https://doi.org/10.1016/j.ohx.2024.e00566. STEP z https://osf.io/nbxzq/download, SHA-256 334286309490685981929f69e71b4bdf99d23bc5f7ccd65fd4db48e1f823cb51. Pełne złożenie ma 220 brył (bryła nie jest równoznaczna z pozycją BOM).
2. Stół Mekanika WKT-S V2.0: https://github.com/mekanika-dev/wkt/tree/8839152eeb607fa1cf63de468c80e3b1398ed8ed. STEP ma 487 brył. Jest to konstrukcja skręcana, przydatna również jako test fałszywych propozycji spoin. BOM w repozytorium dotyczy V1.0, więc nie stanowi dokładnej referencji liczby części V2.0. Dokumentacja i pliki mają licencje opisane w REUSE.toml autorów; nie włączono CAD do kodu programu.

Test `tests/human_assembly_benchmark.py` pobiera plik prasy i sprawdza SHA-256, 220 brył i masę względem niezależnego importu STEPControl oraz całki z pełnej siatki (nie siatki podglądu). Tolerancja 0,1%. W Windows CI uruchamia spakowany silnik EXE; raport jest osobnym artefaktem. Samo dodanie testu nie oznacza jego zaliczenia. Szczegółowe wyniki są w raporcie z danego przebiegu.

## Granice

Styki pozostają kandydatami spoin. STEP nie potwierdza zamiaru spawania, wszystkich materiałów, gwintów, wymagań obróbki, jakości powierzchni i WPS. Analiza z limitem czasu daje jawny wynik częściowy; brak pełnej analizy nie jest zerowym czasem spawania, montażu ani fazowania. Nie uzyskano referencyjnych czasów produkcji autorów modeli. Zgodność wzorów nie jest potwierdzeniem norm warsztatowych. Masa przy jednej gęstości jest porównaniem geometrycznym, nie zmierzoną masą całej maszyny z wyposażeniem.
